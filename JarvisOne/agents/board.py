from dotenv import load_dotenv
load_dotenv(override=True)
import asyncio
import os
import json
import uuid
from datetime import datetime
import sqlite3
from typing import Optional, Tuple

import httpx

from groq import Groq

from .prompts import AGENT_PROMPTS, TURN_ORDER
from ..database.database import get_connection
from . import board_agent
from ..config import GROQ_API_KEY, DEEPSEEK_API_KEY, PLANNER_PROVIDER, PLANNER_MODEL

# Custom Leader AI system prompt (can be overridden via env LEADER_AI_PROMPT)
LEADER_AI_SYSTEM_PROMPT = (
    (os.environ.get("LEADER_AI_PROMPT") or "")
    or "You are LeadAgent, a pragmatic planner. Synthesize prior agents into a JSON-only, actionable plan."
)



class _PlannerLLM:
    def __init__(self):
        self._groq: Optional[Groq] = None
        self._deepseek = None
        # mock content to allow offline runs
        self._mock_responses = {
            "MarketScout": "For busy students who procrastinate, the pain point is the anxiety of starting. Single-feature: a 25-minute auto-start timer with one big 'Go' button.",
            "SalesOptimizer": "Charm pricing at $0.99 for lifetime access framed as 'One coffee for a calmer day'.",
            "Designer": "Single-screen with one giant Go button, then a progress ring. Notifications only at start and end.",
            "Hephaestus": "Stack: React + Vite. Files: src/main.jsx, src/App.jsx. State: { running:boolean, remaining:number }.",
            "CPO": "Cut any accounts/payments for MVP; ship a static price banner and focus on the timer experience.",
            "LeadAgent": "<<JSON_START>>{\n  \"strategy_title\": \"One-Button Focus Timer\",\n  \"tldr\": \"A single-button 25-minute focus timer that lowers anxiety and starts instantly.\",\n  \"summary\": \"For busy students and professionals who procrastinate, this app reduces anxiety by starting a Pomodoro-length timer instantly.\",\n  \"missions\": [\n    {\n      \"mission_id\": \"M1\",\n      \"title\": \"Scaffold app\",\n      \"description\": \"Create minimal React app with Vite and a single App.jsx.\",\n      \"owner\": \"Hephaestus\",\n      \"dependencies\": [],\n      \"steps\": [\n        {\n          \"step_id\": 1,\n          \"description\": \"Create workspace folders\",\n          \"tool\": \"workspace\",\n          \"params\": {\n            \"app_name\": \"one-button-focus-timer\"\n          }\n        },\n        {\n          \"step_id\": 2,\n          \"description\": \"Generate App.jsx\",\n          \"tool\": \"code_generator\",\n          \"params\": {\n            \"app_name\": \"one-button-focus-timer\",\n            \"file_path\": \"src/App.jsx\",\n            \"language\": \"javascript\",\n            \"prompt\": \"Write a React component App that renders a big Go button and when clicked starts a 25-minute countdown, showing minutes:seconds.\"\n          }\n        }\n      ],\n      \"acceptance_criteria\": [\"App builds and countdown works\"]\n    }\n  ]\n}<<JSON_END>>"
        }

    def _ensure(self, provider: str):
        if provider == "groq":
            if not GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY is not set")
            if not self._groq:
                try:
                    http_client = httpx.Client(trust_env=False)
                    self._groq = Groq(api_key=GROQ_API_KEY, http_client=http_client)
                except TypeError:
                    self._groq = Groq(api_key=GROQ_API_KEY)
        elif provider == "deepseek":
            if not DEEPSEEK_API_KEY:
                raise RuntimeError("DEEPSEEK_API_KEY is not set")
            if not self._deepseek:
                from openai import OpenAI
                self._deepseek = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
        else:
            raise RuntimeError(f"Unsupported provider: {provider}")

    def pick_provider_and_model(self, default_model: str, agent_name: Optional[str] = None) -> Tuple[str, str]:
        # Provider precedence: explicit env -> auto
        if PLANNER_PROVIDER in {"groq", "deepseek"}:
            provider = PLANNER_PROVIDER
        else:
            # auto: prefer Groq (free-tier), then DeepSeek
            provider = "groq" if GROQ_API_KEY else ("deepseek" if DEEPSEEK_API_KEY else "mock")

        # Model: env override > agent default > provider default
        if PLANNER_MODEL:
            model = PLANNER_MODEL
        else:
            if provider == "groq":
                model = default_model or "llama-3.1-8b-instant"
            elif provider == "deepseek":
                model = default_model if default_model.lower().startswith("deepseek") else "deepseek-coder"
            else:
                model = default_model or "llama-3.1-8b-instant"

        return provider, model

    def chat(self, provider: str, model: str, messages: list, temperature: float = 0.2, max_tokens: int = 4096, agent_name: Optional[str] = None) -> str:
        self._ensure(provider)
        if provider == "groq":
            resp = self._groq.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        elif provider == "deepseek":
            resp = self._deepseek.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        else:  # mock
            # pick a deterministic response based on agent_name if provided
            name = agent_name or "LeadAgent"
            return self._mock_responses.get(name, "Mock response")

planner_llm = _PlannerLLM()

class Board:
    """
    The Board manages the agent discussion process, from initialization to completion.
    It orchestrates the conversation turn by turn, logs all messages, and saves
    the final strategy to the database.
    """
    def __init__(self, topic: str, user_id: int):
        self.strategy_id = str(uuid.uuid4())
        self.topic = topic
        self.user_id = user_id
        self.turn_number = 0
        self.discussion_log = []
        self.current_agent_name = TURN_ORDER[0]

    def get_conversation_history(self) -> str:
        """Returns a formatted string of the conversation history."""
        return "\n\n".join([f"**{msg['agent']}**: {msg['message']}" for msg in self.discussion_log])

    def _log_message(self, actor: str, message: str, msg_type: str = "text"):
        """Logs a message to the internal messages list and the database."""
        msg = {
            "agent": actor,
            "message": message,
            "type": msg_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.discussion_log.append(msg)
        
        # Also save to DB
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO board_messages (strategy_id, actor, message, type, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.strategy_id, msg["agent"], msg["message"], msg["type"], msg["timestamp"])
            )
            conn.commit()
            # Notify connected clients that a new message is available
            try:
                asyncio.create_task(board_agent.notify_clients())
            except Exception:
                pass
        except sqlite3.Error as e:
            print(f"Database error in _log_message: {e}")
        finally:
            if conn:
                conn.close()

    async def _call_agent(self, agent_name: str) -> str:
        """Calls the specified agent using the selected provider and returns the response."""
        system_prompt = AGENT_PROMPTS[agent_name]["system_prompt"]
        default_model = AGENT_PROMPTS[agent_name]["model"]
        provider, model = planner_llm.pick_provider_and_model(default_model, agent_name)

        history = self.get_conversation_history()
        user_prompt = f"The discussion topic is: {self.topic}"
        if history:
            user_prompt = history

        # Inject custom system prompt for LeadAgent if provided
        if agent_name == "LeadAgent" and LEADER_AI_SYSTEM_PROMPT:
            system_content = f"{LEADER_AI_SYSTEM_PROMPT}\n\n{system_prompt}"
        else:
            system_content = system_prompt

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response_text = await asyncio.to_thread(
                planner_llm.chat,
                provider,
                model,
                messages,
                0.2,
                4096,
                agent_name,
            )
            label = "Groq" if provider == "groq" else ("DeepSeek" if provider == "deepseek" else "OpenAI")
            if provider == "mock":
                label = "Mock"
            print(f"[{label} Board:{model}] {agent_name} responded.")
            return response_text
        except Exception as e:
            print(f"Primary provider '{provider}' failed for {agent_name}: {e}")
            fallback_order = []
            if provider == "groq":
                if DEEPSEEK_API_KEY:
                    fallback_order.append("deepseek")
            elif provider == "deepseek":
                if GROQ_API_KEY:
                    fallback_order.append("groq")

            for fb in fallback_order:
                try:
                    fb_model = model
                    if fb == "deepseek" and not model.lower().startswith("deepseek"):
                        fb_model = "deepseek-coder"
                    if fb == "groq" and model.lower().startswith("deepseek"):
                        fb_model = "llama-3.1-8b-instant"
                    response_text = await asyncio.to_thread(
                        planner_llm.chat,
                        fb,
                        fb_model,
                        messages,
                        0.2,
                        4096,
                        agent_name,
                    )
                    label = "Groq" if fb == "groq" else ("DeepSeek" if fb == "deepseek" else "OpenAI")
                    if fb == "mock":
                        label = "Mock"
                    print(f"[{label} Board:{fb_model}] {agent_name} responded (fallback).")
                    return response_text
                except Exception as fe:
                    print(f"Fallback provider '{fb}' also failed for {agent_name}: {fe}")

            return f"Error: Could not get a response from {agent_name}."

    def _parse_final_plan(self, text: str) -> dict:
        """
        Parses the final JSON plan from the LeadAgent's output.
        Handles cases where the JSON is embedded within other text.
        """
        try:
            # Find the start and end of the JSON block
            json_start = text.find("<<JSON_START>>") + len("<<JSON_START>>")
            json_end = text.find("<<JSON_END>>")
            
            if json_start == -1 or json_end == -1:
                # Fallback for plain JSON
                return json.loads(text)

            json_str = text[json_start:json_end].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing final plan JSON: {e}")
            print(f"Raw text received:\n{text}")
            return {
                "strategy_title": "Plan Parsing Failed",
                "tldr": "The AI's final plan was not in the expected format.",
                "summary": text,
                "missions": []
            }

    def _save_strategy(self, plan: dict):
        """Saves the final strategy and its missions to the database."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            # Save the main strategy
            cursor.execute(
                """
                INSERT INTO strategies (strategy_id, user_id, topic, tldr, summary, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.strategy_id,
                    self.user_id,
                    self.topic, # Use the original topic
                    plan.get("tldr", ""),
                    plan.get("summary", ""),
                    "pending"
                )
            )

            # Save the missions
            missions = plan.get("missions", [])
            for mission in missions:
                cursor.execute(
                    """
                    INSERT INTO missions (
                        mission_id, strategy_id, title, description, owner, 
                        dependencies, steps, acceptance_criteria, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mission.get("mission_id"),
                        self.strategy_id,
                        mission.get("title"),
                        mission.get("description"),
                        mission.get("owner"),
                        json.dumps(mission.get("dependencies", [])),
                        json.dumps(mission.get("steps", [])),
                        json.dumps(mission.get("acceptance_criteria", [])),
                        "pending"
                    )
                )
            
            conn.commit()
            print(f"Strategy {self.strategy_id} and its missions have been saved to the database.")

        except sqlite3.Error as e:
            print(f"Database error in _save_strategy: {e}")
            conn.rollback()
        finally:
            if conn:
                conn.close()

    async def run_discussion(self):
        """
        Runs the entire agent discussion from start to finish.
        """
        print("\nStarting discussion...")
        self._log_message("CEO", self.topic, msg_type="topic")

        for agent_name in TURN_ORDER:
            self.current_agent_name = agent_name
            response = await self._call_agent(agent_name)
            
            msg_type = "text"
            if agent_name == "LeadAgent":
                msg_type = "plan_summary"

            self._log_message(agent_name, response, msg_type=msg_type)

        # After the loop, the last message is from the LeadAgent
        final_plan_text = self.discussion_log[-1]["message"]
        final_plan = self._parse_final_plan(final_plan_text)

        # Save strategy even if missions are absent; missions saved only when present
        if isinstance(final_plan, dict):
            self._save_strategy(final_plan)
            self._log_message("System", f"Strategy {self.strategy_id} has been finalized and saved.", msg_type="system")
        else:
            self._log_message("System", f"Strategy {self.strategy_id} could not be finalized due to invalid plan format.", msg_type="system")
        
        print("Board discussion finished.")
        return final_plan