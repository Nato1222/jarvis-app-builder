"""Run the Executor Agent on a chosen strategy, with quick-modify support."""
import asyncio
import sys
import os
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from JarvisOne.agents.executor_agent import ExecutorAgent
from JarvisOne.database.database import get_connection


def get_latest_strategy_id():
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT strategy_id FROM strategies ORDER BY rowid DESC LIMIT 1")
        row = cur.fetchone()
        return row["strategy_id"] if row else None
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def list_strategies(limit: int = 10):
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT strategy_id, topic, summary, created_at FROM strategies ORDER BY rowid DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall() or []
    except sqlite3.Error:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

async def quick_modify(strategy_id: str):
    print("\n--- Quick Modify ---")
    file_path = input("File to edit (relative to app root, e.g., src/App.js): ").strip()
    instruction = input("Change request (what to modify): ").strip()
    if not file_path or not instruction:
        print("Missing file or instruction.")
        return
    agent = ExecutorAgent(strategy_id=strategy_id)
    agent._load_plan()
    app_name = (agent.plan or {}).get("app_name")
    res = await agent._execute_file_editor({
        "file_path": file_path,
        "instruction": instruction,
        "app_name": app_name,
        "model": "llama-3.1-8b-instant",
    })
    print("Modify result:", res)

async def main():
    print("--- Executor Agent Runner ---")
    rows = list_strategies()
    if not rows:
        print("No strategy found in DB.")
        return
    print("Select a strategy to execute:")
    for idx, r in enumerate(rows, start=1):
        title = r["summary"] or r["topic"] or r["strategy_id"]
        print(f"  {idx}. {title[:100]}…")
    choice = input(f"Enter number (1-{len(rows)}) or press Enter for latest: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(rows):
        row = rows[int(choice)-1]
    else:
        row = rows[0]
    strategy_id = row["strategy_id"]
    print(f"Executing strategy: {strategy_id}")

    executor = ExecutorAgent(strategy_id=strategy_id)
    await executor.execute()

    # Offer to open the generated app folder and quick-modify
    open_app = input("Open the app folder in Explorer? (y/N): ").strip().lower() == 'y'
    if open_app:
        try:
            executor._load_plan()
            from JarvisOne.config import APPS_ROOT
            app = (executor.plan or {}).get("app_name")
            if app:
                path = os.path.join(APPS_ROOT, app)
                os.startfile(path)
        except Exception:
            pass

    if input("Quick modify a file now? (y/N): ").strip().lower() == 'y':
        await quick_modify(strategy_id)


if __name__ == "__main__":
    asyncio.run(main())
