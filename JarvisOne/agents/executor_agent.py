"""
Executor Agent

Executes missions and provides tools, including a real Groq-backed
code generator that writes files to disk.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from groq import Groq
import httpx
from openai import OpenAI

from ..config import GROQ_API_KEY, DEEPSEEK_API_KEY, APPS_ROOT
from ..database.database import get_connection


class ExecutorAgent:
    """Executes the missions defined in a strategy plan."""

    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.plan: Optional[Dict[str, Any]] = None
        self.db_conn = get_connection()
        try:
            self.db_conn.row_factory = sqlite3.Row
        except Exception:
            pass
        self._groq_client: Optional[Groq] = None
        self._deepseek_client: Optional[OpenAI] = None

    # ---------------- Plan loading (minimal/no-op) ----------------
    def _load_plan(self):
        print(f"[Executor] Loading plan for strategy_id: {self.strategy_id}")
        plan: Dict[str, Any] = {"strategy_id": self.strategy_id, "missions": []}
        cur = self.db_conn.cursor()

        # Strategy (basic fields from table)
        try:
            cur.execute("PRAGMA table_info(strategies)")
            strat_cols = {row[1] for row in cur.fetchall()}
            cur.execute(
                "SELECT * FROM strategies WHERE strategy_id = ?",
                (self.strategy_id,),
            )
            srow = cur.fetchone()
            if srow:
                # Use DB topic as a fallback title; we'll override with final plan JSON if available
                if "topic" in strat_cols and srow["topic"]:
                    plan["strategy_title"] = srow["topic"]
                if "summary" in strat_cols:
                    plan["summary"] = srow["summary"]
                if "tldr" in strat_cols:
                    plan["tldr"] = srow["tldr"]
                if "app_name" in strat_cols:
                    plan["app_name"] = srow["app_name"]
        except sqlite3.Error:
            pass

        # Enhance with metadata from the LeadAgent's final plan JSON stored in board_messages
        meta = self._load_final_plan_meta()
        if meta:
            title = meta.get("strategy_title") or meta.get("title")
            if title:
                plan["strategy_title"] = title
            if "summary" not in plan and meta.get("summary"):
                plan["summary"] = meta.get("summary")
            if "tldr" not in plan and meta.get("tldr"):
                plan["tldr"] = meta.get("tldr")
            if meta.get("app_name"):
                plan["app_name"] = self._slugify_name(str(meta.get("app_name")))

        # Missions
        try:
            cur.execute("PRAGMA table_info(missions)")
            mcols = [tuple(r) for r in cur.fetchall()]
            mcol_names = {r[1] for r in mcols}

            base_query = "SELECT * FROM missions"
            params = []
            if "strategy_id" in mcol_names:
                base_query += " WHERE strategy_id = ?"
                params.append(self.strategy_id)
            base_query += " ORDER BY rowid ASC"

            cur.execute(base_query, tuple(params))
            rows = cur.fetchall() or []
            missions = []
            for r in rows:
                mission: Dict[str, Any] = {
                    "mission_id": r["mission_id"] if "mission_id" in mcol_names else None,
                    "title": r["title"] if "title" in mcol_names else (r["name"] if "name" in mcol_names else "Untitled Mission"),
                    "owner": r["owner"] if "owner" in mcol_names else r["assigned_agent"] if "assigned_agent" in mcol_names else None,
                    "status": r["status"] if "status" in mcol_names else None,
                }
                if "app_name" in mcol_names and r["app_name"] is not None:
                    mission["app_name"] = r["app_name"]
                # Steps JSON extraction
                steps_json = None
                for cand in ("steps", "actions", "tasks"):
                    if cand in mcol_names and r[cand] is not None:
                        steps_json = r[cand]
                        break
                steps: list = []
                if isinstance(steps_json, (str, bytes)):
                    try:
                        steps = json.loads(steps_json)
                    except Exception:
                        steps = []
                elif isinstance(steps_json, list):
                    steps = steps_json
                # Normalize steps
                norm_steps = []
                for idx, st in enumerate(steps, start=1):
                    if not isinstance(st, dict):
                        continue
                    tool = st.get("tool") or st.get("type")
                    params = st.get("params") or {}
                    desc = st.get("description") or st.get("desc") or f"Step {idx}"
                    norm_steps.append({
                        "step_id": idx,
                        "tool": tool,
                        "params": params,
                        "description": desc,
                    })
                mission["steps"] = norm_steps
                missions.append(mission)

            plan["missions"] = missions
        except sqlite3.Error:
            plan["missions"] = []

        # Derive a default app_name if not present
        if "app_name" not in plan:
            title = meta.get("strategy_title") if meta else None
            title = title or plan.get("strategy_title") or self.strategy_id
            plan["app_name"] = self._slugify_name(str(title))
        self.plan = plan

    def _load_final_plan_meta(self) -> Optional[Dict[str, Any]]:
        """Fetch and parse the LeadAgent's final plan JSON from board_messages for this strategy."""
        try:
            cur = self.db_conn.cursor()
            cur.execute(
                """
                SELECT message FROM board_messages
                WHERE strategy_id = ? AND actor = 'LeadAgent'
                ORDER BY msg_id DESC LIMIT 1
                """,
                (self.strategy_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            text = row[0] if isinstance(row, (tuple, list)) else row["message"]
            if not isinstance(text, str):
                return None
            # Extract JSON between sentinels if present
            start = text.find("<<JSON_START>>")
            end = text.find("<<JSON_END>>")
            if start != -1 and end != -1 and end > start:
                json_str = text[start + len("<<JSON_START>>"):end].strip()
            else:
                json_str = text.strip()
            try:
                meta = json.loads(json_str)
                if isinstance(meta, dict):
                    return meta
            except Exception:
                return None
        except sqlite3.Error:
            return None
        return None

    # ---------------- Public execute entry ----------------
    async def execute(self):
        self._load_plan()
        missions = (self.plan or {}).get("missions", [])
        # Ensure a workspace exists for this plan
        plan_app = (self.plan or {}).get("app_name")
        if plan_app:
            await self._execute_workspace({
                "app_name": plan_app,
                "create_vscode": True,
                "folders": ["src", "tests", "docs"]
            })
        if not missions:
            print("[Executor] No missions found for this strategy.")
            return
        # Show summary as the strategy name if available per request
        title = (self.plan or {}).get("summary") or (self.plan or {}).get("strategy_title") or self.strategy_id
        print(f"--- Executing Strategy: {title} ---")
        for m in missions:
            print(f"\n[Mission] {m.get('title','Untitled')} - owner: {m.get('owner')}")
            mission_app = m.get("app_name") or (self.plan or {}).get("app_name")
            for st in m.get("steps", []):
                print(f"  - Step {st.get('step_id')}: {st.get('description')}")
                # Propagate app_name down to params if provided at mission/plan level
                if mission_app:
                    st.setdefault("params", {})
                    st["params"].setdefault("app_name", mission_app)
                res = await self._execute_step(st)
                if isinstance(res, dict):
                    if st.get("tool") == "terminal":
                        code = res.get("code")
                        ok = res.get("ok")
                        stdout = (res.get("stdout") or "").strip()
                        stderr = (res.get("stderr") or "").strip()
                        print(f"    [Terminal {'OK' if ok else 'FAIL'}] exit={code}")
                        if stdout:
                            lines = stdout.splitlines()
                            head = "\n".join(lines[-10:]) if len(lines) > 10 else stdout
                            print("    stdout:\n" + "\n".join(["      " + l for l in head.splitlines()]))
                        if stderr:
                            lines = stderr.splitlines()
                            head = "\n".join(lines[-10:]) if len(lines) > 10 else stderr
                            print("    stderr:\n" + "\n".join(["      " + l for l in head.splitlines()]))
                    if not res.get("ok", True):
                        print(f"    [ERROR] {res.get('error')}")
        print("\n--- Execution Complete ---")

    # ---------------- Step router ----------------
    async def _execute_step(self, step: Dict[str, Any]):
        tool = step.get("tool")
        params = step.get("params", {})
        if tool == "terminal":
            return await self._execute_terminal(params)
        if tool == "code_generator":
            return await self._execute_code_generator(params)
        if tool == "file_editor":
            return await self._execute_file_editor(params)
        return {"ok": False, "error": f"Unknown tool: {tool}"}

    # ---------------- Terminal tool ----------------
    async def _execute_terminal(self, params: Dict[str, Any]):
        cmd = params.get("command")
        cwd = params.get("cwd")
        # If no cwd is provided, but app_name is, run from the app root
        if not cwd:
            app_name = params.get("app_name")
            if app_name:
                cwd = str(Path(APPS_ROOT) / app_name)
        timeout = params.get("timeout", 600)
        if not cmd:
            return {"ok": False, "error": "Missing 'command' in params"}

        print(f"[Terminal] $ {cmd}")
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return {"ok": False, "error": f"Command timed out after {timeout}s"}

            code = proc.returncode
            return {
                "ok": code == 0,
                "code": code,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------- Code generator (Groq/DeepSeek) ----------------
    async def _execute_code_generator(self, params: Dict[str, Any]):
        prompt: Optional[str] = params.get("prompt")
        file_path: Optional[str] = params.get("file_path")
        language: Optional[str] = params.get("language")
        overwrite: bool = bool(params.get("overwrite", True))
        app_name: Optional[str] = params.get("app_name")
        model = params.get("model") or "llama-3.1-8b-instant"

        if not prompt or not file_path:
            return {"ok": False, "error": "'prompt' and 'file_path' are required"}

        dest_path = self._resolve_target_path(file_path, app_name)
        parent = dest_path.parent
        # If the parent exists but is a file, we cannot create into it
        if parent.exists() and parent.is_file():
            return {"ok": False, "error": f"Destination parent is a file: {parent}"}
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            # Handle race/edge cases where a file with the same name as a directory exists
            if parent.exists() and parent.is_file():
                return {"ok": False, "error": f"Cannot create directory, a file exists at {parent}"}
            # Otherwise ignore: directory already exists
        if dest_path.exists() and not overwrite:
            return {"ok": False, "error": f"File exists and overwrite=False: {file_path}"}

        backend = "groq"
        if isinstance(model, str) and model.lower().startswith("deepseek"):
            backend = "deepseek"

        if backend == "groq":
            if not self._groq_client:
                if not GROQ_API_KEY:
                    return {"ok": False, "error": "GROQ_API_KEY is not set"}
                try:
                    http_client = httpx.Client(trust_env=False)
                    self._groq_client = Groq(api_key=GROQ_API_KEY, http_client=http_client)
                except TypeError:
                    try:
                        self._groq_client = Groq(api_key=GROQ_API_KEY)
                    except Exception as e:
                        return {"ok": False, "error": f"Failed to init Groq client: {e}"}
                except Exception as e:
                    return {"ok": False, "error": f"Failed to init Groq client: {e}"}
        else:
            if not self._deepseek_client:
                if not DEEPSEEK_API_KEY:
                    return {"ok": False, "error": "DEEPSEEK_API_KEY is not set"}
                try:
                    self._deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
                except Exception as e:
                    return {"ok": False, "error": f"Failed to init DeepSeek client: {e}"}

        system_prompt = (
            "You are a senior code generator. Return ONLY raw code for the requested file. "
            "Do not include markdown, code fences, or explanations. If the prompt mentions "
            "multiple files, output only the single target file's content."
        )
        if language:
            system_prompt += f" Language hint: {language}."

        try:
            if backend == "groq":
                resp = self._groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=float(params.get("temperature", 0.2)),
                    max_tokens=int(params.get("max_tokens", 4096)),
                )
                content = resp.choices[0].message.content or ""
            else:
                resp = self._deepseek_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=float(params.get("temperature", 0.2)),
                    max_tokens=int(params.get("max_tokens", 4096)),
                )
                content = resp.choices[0].message.content or ""
        except Exception as e:
            msg = str(e)
            if backend == "groq" and DEEPSEEK_API_KEY and ("invalid api key" in msg.lower() or "401" in msg):
                # Fallback to DeepSeek automatically
                if not self._deepseek_client:
                    try:
                        self._deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
                    except Exception as ie:
                        return {"ok": False, "error": f"DeepSeek init failed during fallback: {ie}"}
                ds_model = model if model.lower().startswith("deepseek") else "deepseek-coder"
                try:
                    resp = self._deepseek_client.chat.completions.create(
                        model=ds_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=float(params.get("temperature", 0.2)),
                        max_tokens=int(params.get("max_tokens", 4096)),
                    )
                    content = resp.choices[0].message.content or ""
                except Exception as de:
                    return {"ok": False, "error": f"DeepSeek API error after fallback: {de}"}
            else:
                return {"ok": False, "error": f"{backend.capitalize()} API error: {e}"}

        if not content:
            return {"ok": False, "error": "Empty response from model"}

        code = self._strip_code_fences(content)
        try:
            dest_path.write_text(code, encoding="utf-8", newline="\n")
        except Exception as e:
            return {"ok": False, "error": f"Failed to write file: {e}"}

        size = dest_path.stat().st_size
        label = "Groq" if backend == "groq" else "DeepSeek"
        print(f"[{label} CodeGen:{model}] Wrote {size} bytes to {dest_path}")
        return {"ok": True, "file_path": str(dest_path), "bytes": size, "backend": backend, "model": model}

    # ---------------- File editor (Groq/DeepSeek) ----------------
    async def _execute_file_editor(self, params: Dict[str, Any]):
        """Edit an existing file using an LLM to produce the full revised file."""
        file_path: Optional[str] = params.get("file_path")
        instruction: Optional[str] = params.get("instruction") or params.get("prompt")
        language: Optional[str] = params.get("language")
        app_name: Optional[str] = params.get("app_name")
        model = params.get("model") or "llama-3.1-8b-instant"

        if not file_path or not instruction:
            return {"ok": False, "error": "'file_path' and 'instruction' are required"}

        p = self._resolve_target_path(file_path, app_name)
        # If the target path looks like a directory (trailing slash or no suffix), treat as folder creation
        looks_like_dir = (
            isinstance(file_path, str)
            and (file_path.endswith("/") or file_path.endswith("\\") or Path(file_path).suffix == "")
        )
        if looks_like_dir:
            try:
                p.mkdir(parents=True, exist_ok=True)
                return {"ok": True, "dir_path": str(p)}
            except Exception as e:
                return {"ok": False, "error": f"Failed to create directory {p}: {e}"}
        if not p.exists():
            if params.get("create_if_missing", True):
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return {"ok": False, "error": f"Failed to create parent dirs for {p}: {e}"}
                if params.get("use_codegen_on_create", True):
                    cg_prompt = (
                        f"Create an initial version of the file {p.name}. "
                        f"Apply this intent: {instruction}. Return only the file contents."
                    )
                    cg_res = await self._execute_code_generator({
                        "prompt": cg_prompt,
                        "file_path": str(p),
                        "language": language,
                        "overwrite": True,
                        "app_name": app_name,
                        "max_tokens": params.get("max_tokens", 1024),
                        "model": model,
                    })
                    if not isinstance(cg_res, dict) or not cg_res.get("ok"):
                        return {"ok": False, "error": f"Failed to create file via codegen at {p}: {cg_res}"}
                else:
                    try:
                        p.write_text("", encoding="utf-8")
                    except Exception as e:
                        return {"ok": False, "error": f"Failed to create file {p}: {e}"}
            else:
                return {"ok": False, "error": f"File not found: {p}"}

        try:
            original = p.read_text(encoding="utf-8")
        except Exception as e:
            return {"ok": False, "error": f"Failed to read file: {e}"}

        backend = "groq"
        if isinstance(model, str) and model.lower().startswith("deepseek"):
            backend = "deepseek"
        if backend == "groq":
            if not self._groq_client:
                if not GROQ_API_KEY:
                    return {"ok": False, "error": "GROQ_API_KEY is not set"}
                try:
                    http_client = httpx.Client(trust_env=False)
                    self._groq_client = Groq(api_key=GROQ_API_KEY, http_client=http_client)
                except TypeError:
                    try:
                        self._groq_client = Groq(api_key=GROQ_API_KEY)
                    except Exception as e:
                        return {"ok": False, "error": f"Failed to init Groq client: {e}"}
                except Exception as e:
                    return {"ok": False, "error": f"Failed to init Groq client: {e}"}
        else:
            if not self._deepseek_client:
                if not DEEPSEEK_API_KEY:
                    return {"ok": False, "error": "DEEPSEEK_API_KEY is not set"}
                try:
                    self._deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
                except Exception as e:
                    return {"ok": False, "error": f"Failed to init DeepSeek client: {e}"}

        system_prompt = (
            "You are a senior code editor. You will be given an existing file and a requested change. "
            "Return ONLY the full updated file contents. Do not include markdown, code fences, or explanations. "
            "Preserve existing style and imports unless changes require otherwise."
        )
        if language:
            system_prompt += f" Language hint: {language}."

        user_content = (
            "Apply the following change to the file.\n\n"
            f"Change request:\n{instruction}\n\n"
            "Current file contents:\n" + "```\n" + original + "\n```"
        )

        try:
            if backend == "groq":
                resp = self._groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=float(params.get("temperature", 0.2)),
                    max_tokens=int(params.get("max_tokens", 8192)),
                )
                content = resp.choices[0].message.content or ""
            else:
                resp = self._deepseek_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=float(params.get("temperature", 0.2)),
                    max_tokens=int(params.get("max_tokens", 8192)),
                )
                content = resp.choices[0].message.content or ""
        except Exception as e:
            msg = str(e)
            if backend == "groq" and DEEPSEEK_API_KEY and ("invalid api key" in msg.lower() or "401" in msg):
                if not self._deepseek_client:
                    try:
                        self._deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
                    except Exception as ie:
                        return {"ok": False, "error": f"DeepSeek init failed during fallback: {ie}"}
                ds_model = model if model.lower().startswith("deepseek") else "deepseek-coder"
                try:
                    resp = self._deepseek_client.chat.completions.create(
                        model=ds_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        temperature=float(params.get("temperature", 0.2)),
                        max_tokens=int(params.get("max_tokens", 8192)),
                    )
                    content = resp.choices[0].message.content or ""
                except Exception as de:
                    return {"ok": False, "error": f"DeepSeek API error after fallback: {de}"}
            else:
                return {"ok": False, "error": f"{backend.capitalize()} API error: {e}"}

        if not content:
            return {"ok": False, "error": "Empty response from model"}

        new_code = self._strip_code_fences(content)
        if not new_code.strip():
            return {"ok": False, "error": "Model returned empty content after stripping fences"}

        tmp_path = p.with_suffix(p.suffix + ".tmp")
        bak_path = p.with_suffix(p.suffix + ".bak")
        try:
            tmp_path.write_text(new_code, encoding="utf-8", newline="\n")
            if not bak_path.exists():
                bak_path.write_text(original, encoding="utf-8", newline="\n")
            tmp_path.replace(p)
        except Exception as e:
            return {"ok": False, "error": f"Failed to write updated file: {e}"}
        label = "Groq" if backend == "groq" else "DeepSeek"
        print(f"[{label} Edit:{model}] Wrote {len(new_code)} bytes to {p}")
        return {"ok": True, "file_path": str(p), "bytes": len(new_code), "backend": backend, "model": model}

    # ---------------- Workspace management ----------------
    async def _execute_workspace(self, params: Dict[str, Any]):
        """Create a per-app workspace folder and optional VS Code workspace file.

        Params:
        - app_name (str): Name of the app/workspace.
        - create_vscode (bool): If true, creates a .code-workspace file.
        - folders (list[str], optional): Subfolders to create under the app.
        """
        app_name = params.get("app_name")
        if not app_name:
            return {"ok": False, "error": "'app_name' is required"}
        app_root = Path(APPS_ROOT) / app_name
        folders = params.get("folders") or ["src", "tests"]
        try:
            app_root.mkdir(parents=True, exist_ok=True)
            for folder in folders:
                (app_root / folder).mkdir(parents=True, exist_ok=True)
            created = [str(app_root)] + [str(app_root / f) for f in folders]
            if params.get("create_vscode"):
                ws = {
                    "folders": [{"path": "."}],
                    "settings": {},
                }
                ws_path = app_root / f"{app_name}.code-workspace"
                ws_path.write_text(json.dumps(ws, indent=2), encoding="utf-8")
                created.append(str(ws_path))
            return {"ok": True, "created": created}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------- Path resolution ----------------
    def _resolve_target_path(self, file_path: str, app_name: Optional[str]) -> Path:
        p = Path(file_path)
        if p.is_absolute():
            return p
        if app_name:
            return Path(APPS_ROOT) / app_name / p
        return Path(file_path)

    # ---------------- Utils ----------------
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        t = text.strip()
        m = re.match(r"^```[a-zA-Z0-9+\-_.]*\n([\s\S]*?)\n```$", t, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
        m2 = re.match(r"^```\n([\s\S]*?)\n```$", t, flags=re.MULTILINE)
        if m2:
            return m2.group(1).strip()
        if t.startswith("```") and t.endswith("```"):
            return t.strip("`").strip()
        return t

    @staticmethod
    def _slugify_name(name: str) -> str:
        s = name.strip().lower()
        # Replace non-alphanumeric with hyphens
        s = re.sub(r"[^a-z0-9]+", "-", s)
        s = re.sub(r"-+", "-", s).strip("-")
        return s or "app"

    def __del__(self):
        try:
            if getattr(self, "db_conn", None):
                self.db_conn.close()
        except Exception:
            pass
