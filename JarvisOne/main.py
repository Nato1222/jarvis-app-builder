from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState
from typing import List, Optional
import sqlite3
import uuid
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

from JarvisOne.database.database import get_connection
from .agents.executor_agent import ExecutorAgent
from .config import APPS_ROOT
from .auth import router as auth_router, User, get_current_user, get_current_user_ws
try:
    from .agents import board_agent, start_background_board_loop, stop_background_board_loop
except Exception:
    class _BoardStub:
        def user_joined(self, websocket):
            pass
        def user_left(self, websocket):
            pass
        async def start_cycle(self):
            pass
        async def notify_clients(self):
            pass
    board_agent = _BoardStub()
    def start_background_board_loop():
        pass
    def stop_background_board_loop():
        pass

from . import create_tables
from pydantic import BaseModel
from starlette.responses import FileResponse
import sys
import subprocess
from contextlib import closing
try:
    from .jarvis_agent import jarvis_agent
except Exception:
    class _JarvisStub:
        def execute_mission(self, description: str):
            return f"Executed (stub): {description}"
    jarvis_agent = _JarvisStub()
# Optional tools router (file_search). Include only if importable.
file_search_router = None
try:
    from .tools.file_search import router as file_search_router
except Exception:
    try:
        from JarvisOne.tools.file_search import router as file_search_router
    except Exception:
        file_search_router = None
try:
    from .agents.board import Board
except Exception:
    Board = None  # type: ignore

app = FastAPI(
    title="JarvisOne Backend",
    description="Minimalist backend for the JarvisOne project.",
    version="0.1.0"
)

api_router = APIRouter()

# --- CORS Configuration ---
# Allow the local JarvisUI dev server to call the FastAPI backend
# In dev, allow all origins. We don't rely on cookies; tokens are in headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the authentication router
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(api_router, prefix="/api")
if file_search_router is not None:
    app.include_router(file_search_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    """
    Actions to perform on application startup.
    - Create database tables if they don't exist.
    - Start the background agent loop.
    """
    print("Starting up JarvisOne backend...")
    create_tables.create_tables()
    start_background_board_loop()
    print("Startup complete.")

@app.on_event("shutdown")
def on_shutdown():
    """
    Actions to perform on application shutdown.
    - Stop the background agent loop.
    """
    print("Shutting down JarvisOne backend...")
    stop_background_board_loop()
    print("Shutdown complete.")


# --- WebSocket Endpoint ---

class CEO_Message(BaseModel):
    message: str
    type: str

@api_router.websocket("/ws/board")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    # Dev-friendly: accept all WS connections; token is optional and not enforced here
    await websocket.accept()
    uname = 'guest'
    print(f"WebSocket connection established for user: {uname}")
    board_agent.user_joined(websocket) # Pass websocket to agent
    try:
        while True:
            # Keep the connection alive. The agent will push messages.
            await asyncio.sleep(3600) # Sleep for a long time
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user {uname}")
    except Exception as e:
        print(f"WebSocket Error for user {uname}: {e}")
    finally:
        print(f"WebSocket connection closed for user: {uname}")
        board_agent.user_left(websocket)
        if not websocket.client_state == WebSocketState.DISCONNECTED:
            await websocket.close()


# Compatibility WebSocket route without the /api prefix
@app.websocket("/ws/board")
async def websocket_endpoint_direct(websocket: WebSocket, token: Optional[str] = Query(None)):
    # Forward to the main handler
    await websocket_endpoint(websocket, token)

# Additional alias to ensure /api/ws/board works even if router order changes
@app.websocket("/api/ws/board")
async def websocket_endpoint_api_alias(websocket: WebSocket, token: Optional[str] = Query(None)):
    await websocket_endpoint(websocket, token)


# --- Board Endpoints ---

@api_router.post("/board/start", status_code=status.HTTP_202_ACCEPTED, tags=["Board"])
async def start_board_scan():
    """
    Manually trigger an immediate scan by the Board agent.
    """
    asyncio.create_task(board_agent.start_cycle())
    return {"message": "Board scan initiated."}

@api_router.get("/board/feed", tags=["Board"])
def get_board_feed(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """
    Returns the most recent messages from the board.
    """
    conn = get_connection()
    # This fetches messages across all strategies for a general feed
    messages = conn.execute(
        'SELECT * FROM board_messages ORDER BY timestamp DESC LIMIT ?',
        (limit,)
    ).fetchall()
    conn.close()
    # The frontend expects 'id' but the schema has 'msg_id'
    results = []
    for row in messages:
        row_dict = dict(row)
        row_dict['id'] = row_dict['msg_id']
        results.append(row_dict)
    return results

@api_router.post("/board/message", status_code=status.HTTP_201_CREATED, tags=["Board"])
def post_board_message(message: CEO_Message, current_user: dict = Depends(get_current_user)):
    """
    Allows the CEO (user) to send a message or correction to the board.
    """
    conn = get_connection()
    try:
        # Find the most recent strategy to associate the message with
        latest_strategy = conn.execute(
            "SELECT strategy_id FROM strategies WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (current_user['user_id'],)
        ).fetchone()

        if not latest_strategy:
            raise HTTPException(status_code=400, detail="No active strategy to post a message to.")

        strategy_id = latest_strategy['strategy_id']

        conn.execute(
            """
            INSERT INTO board_messages (strategy_id, actor, type, message, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (strategy_id, 'CEO', message.type, message.message)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()
    
    # Notify the board agent that a new message has been posted
    asyncio.create_task(board_agent.notify_clients())
    
    return {"message": "Message posted successfully."}

# --- Lightweight Status Endpoints expected by UI ---

@api_router.get("/status", tags=["Status"])
def api_status(current_user: dict = Depends(get_current_user)):
    """Return minimal system stats for the Dashboard."""
    conn = get_connection()
    try:
        # Pending strategies = not approved
        pending = conn.execute(
            "SELECT COUNT(*) AS c FROM strategies WHERE COALESCE(status,'') != 'approved' AND user_id = ?",
            (current_user['user_id'],)
        ).fetchone()['c']

        # Active missions = pending missions in user's strategies
        active = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM missions m
            JOIN strategies s ON m.strategy_id = s.strategy_id
            WHERE m.status = 'pending' AND s.user_id = ?
            """,
            (current_user['user_id'],)
        ).fetchone()['c']

        # Board messages total (all)
        board_total = conn.execute(
            "SELECT COUNT(*) AS c FROM board_messages"
        ).fetchone()['c']

        # Provide both snake_case and camelCase keys to satisfy different frontends
        return {
            # snake_case
            "pending_strategies": pending,
            "active_missions": active,
            # camelCase expected by current React UI
            "pendingStrategies": pending,
            "activeMissions": active,
            "boardMessages": board_total,
            "ok": True,
        }
    finally:
        conn.close()


@api_router.get("/board/status", tags=["Status"]) 
def api_board_status(current_user: dict = Depends(get_current_user)):
    """Return recent board messages and totals for the Dashboard widgets."""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM board_messages").fetchone()['c']
        rows = conn.execute(
            "SELECT msg_id, actor, type, message, timestamp FROM board_messages ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        recent = []
        for r in rows:
            d = dict(r)
            # Provide a friendlier display name if needed
            d['actor_display'] = d.get('actor')
            # Also include 'text' alias for UI fallbacks
            d['text'] = d.get('message')
            recent.append(d)
        return {
            "total_messages": total,
            "recent_messages": recent,
        }
    finally:
        conn.close()


# --- Compatibility Endpoints expected by UI service (legacy names) ---

@api_router.get("/stats", tags=["Status"])
def api_stats(current_user: dict = Depends(get_current_user)):
    """Alias of /api/status for older UI calls."""
    return api_status(current_user)  # type: ignore[arg-type]


@api_router.get("/messages", tags=["Messages"])
def api_messages(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Return recent board messages in a generic shape (id, text, actor, timestamp)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT msg_id, actor, type, message, timestamp FROM board_messages ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            out.append({
                "id": d.get("msg_id"),
                "text": d.get("message"),
                "message": d.get("message"),
                "actor": d.get("actor"),
                "type": d.get("type"),
                "timestamp": d.get("timestamp"),
            })
        return out
    finally:
        conn.close()


@api_router.get("/messages/{msg_id}", tags=["Messages"])
def api_message_detail(msg_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        r = conn.execute(
            "SELECT msg_id, actor, type, message, timestamp FROM board_messages WHERE msg_id = ?",
            (msg_id,)
        ).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Message not found")
        d = dict(r)
        return {
            "id": d.get("msg_id"),
            "text": d.get("message"),
            "message": d.get("message"),
            "actor": d.get("actor"),
            "type": d.get("type"),
            "timestamp": d.get("timestamp"),
        }
    finally:
        conn.close()


class ShiftRequest(BaseModel):
    corrected_text: Optional[str] = None
    reason: Optional[str] = None
    tags: Optional[List[str]] = []


@api_router.post("/messages/{msg_id}/propose_shift", tags=["Messages"])
def api_message_propose_shift(msg_id: str, body: ShiftRequest, current_user: dict = Depends(get_current_user)):
    """Compatibility route that stores a correction proposal linked to a message."""
    conn = get_connection()
    try:
        msg = conn.execute("SELECT msg_id FROM board_messages WHERE msg_id=?", (msg_id,)).fetchone()
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")

        correction_id = f"corr_{uuid.uuid4()}"
        conn.execute(
            "INSERT INTO corrections (correction_id, msg_id, corrected_text, reason, tags, approved) VALUES (?, ?, ?, ?, ?, ?)",
            (
                correction_id,
                msg_id,
                body.corrected_text or "",
                body.reason or "",
                ",".join(body.tags or []),
                0,
            ),
        )
        conn.commit()
        return {"status": "success", "correction_id": correction_id}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

# Also register status endpoints at the app level to avoid include order issues
@app.get("/api/status", tags=["Status"])  # duplicate path for robustness
def app_api_status(current_user: dict = Depends(get_current_user)):
    return api_status(current_user)  # type: ignore[arg-type]


@app.get("/api/board/status", tags=["Status"])  # duplicate path for robustness
def app_api_board_status(current_user: dict = Depends(get_current_user)):
    return api_board_status(current_user)  # type: ignore[arg-type]

# Alias for clients calling /api/stats
@app.get("/api/stats", tags=["Status"])  # alias
def app_api_stats_alias(current_user: dict = Depends(get_current_user)):
    return api_status(current_user)  # type: ignore[arg-type]

# --- Strategy Endpoints ---

@api_router.get("/strategies", tags=["Strategy"])
def get_strategies(current_user: dict = Depends(get_current_user)):
    """
    Returns all strategies for the current user, mapped to UI-friendly shape.
    """
    conn = get_connection()
    try:
        import re

        def _format_title(topic: str | None, tldr: str | None, summary: str | None) -> str:
            text = (tldr or summary or topic or "").strip()
            if not text:
                return (topic or "Strategy").strip()[:60]
            first = text.split("\n", 1)[0]

            app_name = None
            desc = None
            # Patterns like "SyncKids is a ..."
            if " is " in first:
                app_name = first.split(" is ", 1)[0].strip().strip(':')
                desc = first.split(" is ", 1)[1]
            elif " solves " in first:
                app_name = first.split(" solves ", 1)[0].strip().strip(':')
                desc = "solves it"
            else:
                # Fallback: first word or CamelCase token as name
                m = re.match(r"([A-Z][A-Za-z0-9]+)", first)
                app_name = m.group(1) if m else (topic or "App").split()[0]
                desc = first

            # Short descriptor = first clause or first 5 words
            desc = (desc or "").split('.')[0].split(',')[0].strip()
            words = [w for w in re.split(r"\s+", desc) if w]
            short = " ".join(words[:5]) if words else "single-feature app"
            return f"{app_name} - {short}"[:80]

        rows = conn.execute(
            'SELECT strategy_id, topic, tldr, summary, status, created_at FROM strategies WHERE user_id = ? ORDER BY created_at DESC',
            (current_user['user_id'],)
        ).fetchall()
        # Dev fallback: if user has no strategies yet, surface a few latest public ones for visibility
        if not rows:
            rows = conn.execute(
                'SELECT strategy_id, topic, tldr, summary, status, created_at FROM strategies ORDER BY created_at DESC LIMIT 10'
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            out.append({
                "id": d["strategy_id"],
                "title": _format_title(d.get("topic"), d.get("tldr"), d.get("summary")),
                "summary": d.get("summary") or d.get("tldr") or d.get("topic"),
                "status": "pending" if d.get("status") in (None, "", "pending", "pending_approval") else d.get("status"),
                "createdAt": d.get("created_at"),
                # optional fields UI may show if present
                "investment": None,
                "timeline": None,
                "roi": None,
                "successRate": None,
                "evidence": None,
                "approvedAt": None,
            })
        return out
    finally:
        conn.close()

@api_router.get("/strategies/{strategy_id}", tags=["Strategies"])
def get_strategy(strategy_id: int, current_user: dict = Depends(get_current_user)):
    """
    Get details of a specific strategy.
    """
    conn = get_connection()
    strategy = conn.execute(
        'SELECT * FROM strategies WHERE strategy_id = ? AND user_id = ?',
        (strategy_id, current_user['user_id'])
    ).fetchone()
    conn.close()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return dict(strategy)

@api_router.get("/board/messages/{strategy_id}", tags=["Board"])
def get_strategy_messages(strategy_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    # Optional: Add a check to ensure the user owns the strategy
    messages = conn.execute(
        "SELECT msg_id, actor, type, message, timestamp FROM board_messages WHERE strategy_id=? ORDER BY timestamp ASC",
        (strategy_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in messages]

@api_router.get("/board/missions/{strategy_id}", tags=["Board"])
def get_strategy_missions(strategy_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    # Optional: Add a check to ensure the user owns the strategy
    missions = conn.execute(
        "SELECT mission_id, title, assigned_agent, tool, action, evidence FROM missions WHERE strategy_id=?",
        (strategy_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in missions]

class ProposeCorrectionRequest(BaseModel):
    corrected_text: str
    reason: str
    tags: Optional[List[str]] = []

@api_router.post("/board/message/{msg_id}/propose_correction", tags=["Board"])
def propose_correction(msg_id: str, request: ProposeCorrectionRequest, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        # Check if the message exists
        msg = conn.execute("SELECT msg_id FROM board_messages WHERE msg_id=?", (msg_id,)).fetchone()
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")

        correction_id = f"corr_{uuid.uuid4()}"
        conn.execute(
            "INSERT INTO corrections (correction_id, msg_id, corrected_text, reason, tags, approved) VALUES (?, ?, ?, ?, ?, ?)",
            (correction_id, msg_id, request.corrected_text, request.reason, ",".join(request.tags), 0)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()
    
    return {"status": "success", "correction_id": correction_id}

@api_router.post("/strategies/{strategy_id}/approve", status_code=status.HTTP_200_OK, tags=["Strategy"])
def approve_strategy(strategy_id: str, current_user: dict = Depends(get_current_user)):
    """
    Approve a strategy, changing its status and creating initial missions.
    """
    conn = get_connection()
    try:
        # 1. Find the strategy owned by the user
        strategy_row = conn.execute(
            'SELECT * FROM strategies WHERE strategy_id = ? AND user_id = ?',
            (strategy_id, current_user['user_id'])
        ).fetchone()

        # Dev fallback: allow approving if the strategy exists but is not owned by this user
        if not strategy_row:
            any_strategy_row = conn.execute(
                'SELECT * FROM strategies WHERE strategy_id = ?',
                (strategy_id,)
            ).fetchone()
            if not any_strategy_row:
                raise HTTPException(status_code=404, detail="Strategy not found")
            strategy_row = any_strategy_row
            # Optionally claim ownership for current user if unassigned
            try:
                dtmp = dict(strategy_row)
                if not dtmp.get('user_id'):
                    conn.execute('UPDATE strategies SET user_id = ? WHERE strategy_id = ?', (current_user['user_id'], strategy_id))
            except Exception:
                pass

        strategy = dict(strategy_row)

        # Allow approving anything not already approved
        if strategy.get('status') == 'approved':
            return {"message": "Already approved"}

        # 2. Update strategy status
        conn.execute(
            'UPDATE strategies SET status = ? WHERE strategy_id = ?',
            ('approved', strategy_id)
        )

        # Also create an initial mission similar to the public endpoint
        summary_val = strategy.get('summary') or ''
        title = strategy.get('topic') or ((summary_val[:60] + '...') if summary_val else 'Implement approved strategy')
        conn.execute(
            """
            INSERT INTO missions (mission_id, strategy_id, title, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (str(uuid.uuid4()), strategy_id, title)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

    return {"message": f"Strategy {strategy_id} approved."}


@api_router.post("/strategies/{strategy_id}/reject", status_code=status.HTTP_200_OK, tags=["Strategy"])
def reject_strategy(strategy_id: str, current_user: dict = Depends(get_current_user)):
    """
    Reject a strategy, changing its status to 'rejected'.
    """
    conn = get_connection()
    try:
        strategy_row = conn.execute(
            'SELECT * FROM strategies WHERE strategy_id = ? AND user_id = ?',
            (strategy_id, current_user['user_id'])
        ).fetchone()

        # Dev fallback: allow rejecting if the strategy exists but is not owned by this user
        if not strategy_row:
            any_strategy_row = conn.execute(
                'SELECT * FROM strategies WHERE strategy_id = ?',
                (strategy_id,)
            ).fetchone()
            if not any_strategy_row:
                raise HTTPException(status_code=404, detail="Strategy not found")
            strategy_row = any_strategy_row

        strategy = dict(strategy_row)

        if strategy.get('status') == 'rejected':
            return {"message": "Already rejected"}

        conn.execute(
            'UPDATE strategies SET status = ? WHERE strategy_id = ?',
            ('rejected', strategy_id)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

    return {"message": f"Strategy {strategy_id} rejected."}


# --- Mission Endpoints ---

@api_router.get("/missions")
async def get_active_missions(user: dict = Depends(get_current_user)):
    """
    Get all missions from approved strategies that are pending.
    The frontend expects a status of 'active' for these.
    """
    conn = get_connection()
    approved_strategies = conn.execute(
        "SELECT strategy_id FROM strategies WHERE status = 'approved' AND user_id = ?",
    (user['user_id'],)
    ).fetchall()
    
    if not approved_strategies:
        conn.close()
        return []

    strategy_ids = [row['strategy_id'] for row in approved_strategies]
    placeholders = ','.join('?' for _ in strategy_ids)
    query = (
        "SELECT m.*, s.topic AS strategy_topic, COALESCE(s.tldr, s.summary) AS strategy_summary "
        "FROM missions m JOIN strategies s ON m.strategy_id = s.strategy_id "
        f"WHERE m.strategy_id IN ({placeholders}) AND m.status = 'pending'"
    )
    missions_cursor = conn.execute(query, strategy_ids)
    db_rows = [dict(row) for row in missions_cursor.fetchall()]
    conn.close()

    # Map to UI shape: id, title, description, status, createdAt
    missions: list[dict] = []
    for r in db_rows:
        status_val = r.get('status')
        missions.append({
            "id": r.get('mission_id'),
            "title": r.get('title'),
            "description": r.get('description'),
            # Frontend treats 'pending' as 'active'
            "status": 'active' if status_val == 'pending' else status_val,
            "createdAt": r.get('created_at') if 'created_at' in r else None,
            "planName": r.get('strategy_topic') or (r.get('strategy_summary')[:60] + '...') if r.get('strategy_summary') else None,
        })

    return missions

@api_router.post("/jarvis/execute/{mission_id}")
async def execute_mission(mission_id: str, user: User = Depends(get_current_user)):
    """
    Executes a mission using the JarvisAgent, stores the result, and marks it as completed.
    """
    conn = get_connection()
    try:
        # 1. Find the mission and ensure it belongs to the user and is pending
        mission_query = """
            SELECT m.mission_id, m.title, s.user_id
            FROM missions m
            JOIN strategies s ON m.strategy_id = s.strategy_id
            WHERE m.mission_id = ? AND s.user_id = ? AND m.status = 'pending'
        """
        mission = conn.execute(mission_query, (mission_id, user['user_id'])).fetchone()

        if not mission:
            raise HTTPException(status_code=404, detail="Pending mission not found for this user.")

        mission_description = mission['title']

        # 2. Execute the mission using JarvisAgent
        # This is a synchronous call for simplicity. For long-running tasks,
        # this should be a background job.
        execution_report = jarvis_agent.execute_mission(mission_description)

        # 3. Update the mission in the database with the result and new status
        update_query = "UPDATE missions SET status = 'completed', result = ? WHERE mission_id = ?"
        conn.execute(update_query, (execution_report, mission_id))
        conn.commit()

        return {
            "status": "completed",
            "mission_id": mission_id,
            "report": execution_report
        }

    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during mission execution: {e}")
    finally:
        conn.close()


# --- Static Files and SPA Handling ---

script_dir = os.path.dirname(__file__)
# Serve a lightweight UI directly from the frontend folder
frontend_dir = os.path.join(script_dir, "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/ui", StaticFiles(directory=frontend_dir, html=True), name="ui")


# Add a root endpoint for basic health check
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to JarvisOne API"}

# ----------------- Public (local) endpoints for minimal UI -----------------

public_router = APIRouter(prefix="/api/public", tags=["Public"])


@public_router.get("/strategies")
def public_strategies(limit: int = 20):
    """List latest strategies without auth (local dev only)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT strategy_id, topic, summary, tldr, created_at FROM strategies ORDER BY rowid DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall() or []
        out = []
        for r in rows:
            d = {
                "strategy_id": r[0],
                "topic": r[1],
                "summary": r[2],
                "tldr": r[3],
                "created_at": r[4],
            }
            out.append(d)
        return out
    finally:
        conn.close()


@public_router.get("/board/feed")
def public_board_feed(limit: int = 100):
    """Public board feed for UI chat."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT msg_id, strategy_id, actor, type, message, timestamp FROM board_messages ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    finally:
        conn.close()


@public_router.post("/board/generate")
async def public_board_generate(n: int = 5):
    """Generate N board discussions in background without interactive input."""

    # Helper to get CEO user_id from DB
    def _get_ceo_id() -> Optional[str]:
        try:
            conn = get_connection()
            with closing(conn):
                row = conn.execute("SELECT user_id FROM users WHERE username = 'ceo'").fetchone()
                return row['user_id'] if row else None
        except Exception as e:
            print(f"Failed to fetch CEO user id: {e}")
            return None

    async def run_once(topic: str):
        try:
            ceo_id = _get_ceo_id()
            if not ceo_id or not Board:
                return
            board = Board(topic=topic, user_id=ceo_id)
            await board.run_discussion()
            # board.run_discussion persists messages and strategy internally
        except Exception as e:
            print(f"Board generation error: {e}")

    count = max(1, int(n or 1))
    default_topic = "Find a common market pain point and propose a single-feature app to solve it."
    for _ in range(count):
        asyncio.create_task(run_once(default_topic))
    # Best-effort immediate ping so UIs update quickly
    try:
        await board_agent.notify_clients()
    except Exception:
        pass
    return {"started": count}


class QuickEditRequest(BaseModel):
    strategy_id: str
    file_path: str
    instruction: str

class MissionMetric(BaseModel):
    mission_id: str
    key: str
    value: str

class MissionActivityIn(BaseModel):
    mission_id: str
    time: Optional[str] = None
    action: str
    status: str
    details: Optional[dict] = None


@public_router.post("/execute/{strategy_id}", status_code=202)
async def public_execute(strategy_id: str):
    """Kick off the executor for a strategy in background."""
    async def runner():
        agent = ExecutorAgent(strategy_id=strategy_id)
        await agent.execute()

    asyncio.create_task(runner())
    return {"status": "started", "strategy_id": strategy_id}


@public_router.post("/quick_edit")
async def public_quick_edit(req: QuickEditRequest):
    agent = ExecutorAgent(strategy_id=req.strategy_id)
    agent._load_plan()
    app_name = (agent.plan or {}).get("app_name")
    res = await agent._execute_file_editor({
        "file_path": req.file_path,
        "instruction": req.instruction,
        "app_name": app_name,
        "model": "llama-3.1-8b-instant",
    })
    return res


@public_router.post("/open_app/{strategy_id}")
def public_open_app(strategy_id: str):
    """Open the generated app folder in Explorer on the server host (local)."""
    try:
        # Derive app folder by reusing executor logic
        agent = ExecutorAgent(strategy_id=strategy_id)
        agent._load_plan()
        app_name = (agent.plan or {}).get("app_name")
        if not app_name:
            return {"ok": False, "error": "No app_name found for strategy"}
        path = os.path.join(APPS_ROOT, app_name)
        if os.name == "nt":
            os.startfile(path)
        else:
            return {"ok": False, "error": "Opening folders is supported on Windows only in this endpoint."}
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@public_router.post("/strategies/{strategy_id}/approve")
def public_approve_strategy(strategy_id: str):
    """Public approve: mark strategy approved and create initial mission."""
    conn = get_connection()
    try:
        strategy = conn.execute(
            'SELECT strategy_id, topic, summary, status FROM strategies WHERE strategy_id = ?',
            (strategy_id,)
        ).fetchone()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        if strategy['status'] == 'approved':
            return {"message": "Already approved"}

        conn.execute('UPDATE strategies SET status = ? WHERE strategy_id = ?', ('approved', strategy_id))

        # Create a simple initial mission
        title = strategy['topic'] or (strategy['summary'][:60] + '...') if strategy['summary'] else 'Implement approved strategy'
        conn.execute(
            """
            INSERT INTO missions (mission_id, strategy_id, title, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (str(uuid.uuid4()), strategy_id, title)
        )
        conn.commit()
        return {"message": f"Strategy {strategy_id} approved and mission created."}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

# --- Mission Details and Editing ---

@api_router.post("/missions/{mission_id}/metrics")
def upsert_mission_metric(mission_id: str, metric: MissionMetric, user: dict = Depends(get_current_user)):
    if mission_id != metric.mission_id:
        raise HTTPException(status_code=400, detail="mission_id mismatch")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO mission_metrics (mission_id, key, value) VALUES (?, ?, ?)",
            (metric.mission_id, metric.key, metric.value)
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        conn.close()

@api_router.get("/missions/{mission_id}/metrics")
def list_mission_metrics(mission_id: str, user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM mission_metrics WHERE mission_id = ?", (mission_id,)).fetchall()
        return [{"key": r[0], "value": r[1]} for r in rows]
    finally:
        conn.close()

@api_router.post("/missions/{mission_id}/activities")
def add_mission_activity(mission_id: str, activity: MissionActivityIn, user: dict = Depends(get_current_user)):
    if mission_id != activity.mission_id:
        raise HTTPException(status_code=400, detail="mission_id mismatch")
    conn = get_connection()
    try:
        activity_id = str(uuid.uuid4())
        details_json = None
        if activity.details is not None:
            try:
                import json as _json
                details_json = _json.dumps(activity.details)
            except Exception:
                details_json = None
        conn.execute(
            """
            INSERT INTO mission_activities (activity_id, mission_id, time, action, status, details)
            VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, ?, ?)
            """,
            (activity_id, mission_id, activity.time, activity.action, activity.status, details_json)
        )
        conn.commit()
        return {"activity_id": activity_id}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        conn.close()

@api_router.get("/missions/{mission_id}/activities")
def list_mission_activities(mission_id: str, user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT activity_id, time, action, status, details FROM mission_activities WHERE mission_id = ? ORDER BY time ASC",
            (mission_id,)
        ).fetchall()
        out = []
        for r in rows:
            item = {
                "activity_id": r[0],
                "time": r[1],
                "action": r[2],
                "status": r[3],
            }
            if r[4]:
                try:
                    import json as _json
                    item["details"] = _json.loads(r[4])
                except Exception:
                    item["details"] = None
            out.append(item)
        return out
    finally:
        conn.close()

class MissionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

@api_router.put("/missions/{mission_id}")
def update_mission(mission_id: str, patch: MissionUpdate, user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        fields = []
        values: list = []
        if patch.title is not None:
            fields.append("title = ?")
            values.append(patch.title)
        if patch.description is not None:
            fields.append("description = ?")
            values.append(patch.description)
        if patch.status is not None:
            fields.append("status = ?")
            values.append(patch.status)
        if not fields:
            return {"ok": True}
        values.append(mission_id)
        sql = f"UPDATE missions SET {', '.join(fields)} WHERE mission_id = ?"
        conn.execute(sql, values)
        conn.commit()
        return {"ok": True}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        conn.close()

@api_router.get("/missions/{mission_id}", tags=["Missions"])
def get_mission_detail(mission_id: str, user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        # Mission + owning user validation
        row = conn.execute(
            """
            SELECT m.*, s.user_id, s.topic AS strategy_topic, COALESCE(s.tldr, s.summary) AS strategy_summary
            FROM missions m JOIN strategies s ON m.strategy_id = s.strategy_id
            WHERE m.mission_id = ?
            """,
            (mission_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Mission not found")
        if row["user_id"] != user["user_id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        mission = dict(row)
        # Metrics
        metrics_rows = conn.execute(
            "SELECT key, value FROM mission_metrics WHERE mission_id = ?",
            (mission_id,)
        ).fetchall()
        metrics = [{"key": r[0], "value": r[1]} for r in metrics_rows]
        # Activities
        act_rows = conn.execute(
            "SELECT activity_id, time, action, status, details FROM mission_activities WHERE mission_id = ? ORDER BY time ASC",
            (mission_id,)
        ).fetchall()
        activities = []
        for r in act_rows:
            item = {
                "activity_id": r[0],
                "time": r[1],
                "action": r[2],
                "status": r[3],
            }
            if r[4]:
                try:
                    import json as _json
                    item["details"] = _json.loads(r[4])
                except Exception:
                    item["details"] = None
            activities.append(item)
        # Output
        return {
            "mission": {
                "id": mission.get("mission_id"),
                "title": mission.get("title"),
                "description": mission.get("description"),
                "status": mission.get("status"),
                "createdAt": mission.get("created_at"),
                "planName": mission.get("strategy_topic") or ((mission.get("strategy_summary") or "")[:60] + "...") if mission.get("strategy_summary") else None,
                "result": mission.get("result"),
            },
            "metrics": metrics,
            "activities": activities,
        }
    finally:
        conn.close()


@public_router.get("/missions")
def public_missions(limit: int = 50):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM missions ORDER BY rowid DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    finally:
        conn.close()


@public_router.get("/actions")
def public_actions(limit: int = 200):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM actions_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    finally:
        conn.close()


app.include_router(public_router)

# ----------------- App-level aliases for robustness -----------------

@app.get("/api/strategies", tags=["Strategy"])  # alias wrapper
def app_get_strategies(current_user: dict = Depends(get_current_user)):
    return get_strategies(current_user)


@app.post("/api/strategies/{strategy_id}/approve", tags=["Strategy"])  # alias wrapper
def app_approve_strategy(strategy_id: str, current_user: dict = Depends(get_current_user)):
    return approve_strategy(strategy_id, current_user)


@app.post("/api/strategies/{strategy_id}/reject", tags=["Strategy"])  # alias wrapper
def app_reject_strategy(strategy_id: str, current_user: dict = Depends(get_current_user)):
    return reject_strategy(strategy_id, current_user)


@app.get("/api/missions", tags=["Missions"])  # alias wrapper
async def app_get_active_missions(user: dict = Depends(get_current_user)):
    return await get_active_missions(user)
