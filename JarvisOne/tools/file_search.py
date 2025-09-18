import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Determine project root as the parent of this file's package directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

router = APIRouter(prefix="/tools", tags=["Tools: File Search"])


class SearchRequest(BaseModel):
    query: str


class ReadRequest(BaseModel):
    path: str  # relative path from project root


def _is_allowed(path: Path) -> bool:
    """Allow only files inside project root and not hidden/system files."""
    try:
        # Must be within project root
        path.relative_to(PROJECT_ROOT)
    except ValueError:
        return False

    # Disallow hidden components (names starting with '.')
    parts = path.relative_to(PROJECT_ROOT).parts
    if any(p.startswith(".") for p in parts):
        return False

    # Basic system folders to avoid
    blocked = {".git", "node_modules", "__pycache__", ".venv"}
    if any(p in blocked for p in parts):
        return False

    # Only regular files
    return path.is_file()


@router.post("/search", response_model=List[str])
def search_files(body: SearchRequest) -> List[str]:
    q = (body.query or "").strip()
    if not q:
        return []

    q_lower = q.lower()
    results: List[str] = []

    # Walk the project root
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Prune blocked/hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {".git", "node_modules", "__pycache__", ".venv"}]

        for fname in files:
            if fname.startswith('.'):
                continue
            fpath = Path(root) / fname
            rel = fpath.relative_to(PROJECT_ROOT)
            rel_str = str(rel).replace("\\", "/")

            matched = q_lower in fname.lower()
            if not matched:
                # Try a quick content scan (best-effort, short-circuit after a chunk)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                        chunk = fh.read(200000)  # read first ~200KB
                        if q_lower in chunk.lower():
                            matched = True
                except Exception:
                    matched = False

            if matched and _is_allowed(fpath):
                results.append(rel_str)

            # Keep it simple; no dedupe/prioritization beyond this
            if len(results) >= 500:
                return results

    return results


@router.post("/read")
def read_file(body: ReadRequest) -> str:
    rel = body.path.strip().lstrip("/\\")
    if not rel:
        raise HTTPException(status_code=400, detail="path is required")

    target = (PROJECT_ROOT / rel).resolve()

    # Security checks
    if not _is_allowed(target):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read file: {e}")

    # For large files, return first 1000 characters
    return content[:1000]
