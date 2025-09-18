import asyncio
import sqlite3
import os
import sys
import re

# Add project root to path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from JarvisOne.agents.board import Board

def get_ceo_id():
    """Fetches the user_id for the 'ceo' user."""
    # Construct the absolute path to the database file from the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '..', 'jarvisone.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = 'ceo'")
        user = cursor.fetchone()
        return user[0] if user else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

async def run_terminal_board():
    print("--- JarvisOne Board Room ---")

    ceo_id = get_ceo_id()
    if not ceo_id:
        print("Critical: 'ceo' user not found in the database. Please run `database/create_tables.py` first.")
        return

    custom = input("Enter a topic for a new strategy, or press Enter to use default: ").strip()
    topic = custom or "Find a common pain point in a consumer market and propose a single-feature mobile app to solve it."
    print(f"Topic: {topic}")
    print("Initializing board and agents...")
    board = Board(topic=topic, user_id=ceo_id)

    # Run the discussion and get the final plan
    plan = await board.run_discussion()

    print("\n--- Discussion Complete ---")
    if plan:
        print(f"Final strategy ({board.strategy_id}) has been generated and saved.")
    else:
        print("An error occurred and the plan could not be generated.")

    # Print the full discussion log
    print("\n--- Full Discussion Log ---")
    for entry in board.discussion_log:
        print(f"[{entry['timestamp']}] {entry['agent']} ({entry['type']}):\n{entry['message']}\n")

    # Print the final summary in the requested format
    if plan:
        print("\n--- Plan Summary ---")
        print(f"New Idea: \"{plan.get('strategy_title', 'N/A')}\"")
        
        summary_text = plan.get('summary', '')
        
        persona = "Not specified"
        pain_point = "Not specified"
        solution = f"A single-feature app, {plan.get('strategy_title', 'N/A')}, that {plan.get('tldr', 'solves an issue')}."

        # A robust regex to find the persona and the description of their pain point.
        # It looks for "For [persona], [description of pain point]."
        match = re.search(r"For (.*?),\s*(.*)", summary_text, re.DOTALL | re.IGNORECASE)

        if match:
            persona = match.group(1).strip().capitalize()
            pain_point = match.group(2).strip().capitalize()


        print(f"Persona: {persona}")
        print(f"Pain Point: {pain_point}")
        print(f"Solution: {solution}")

if __name__ == "__main__":
    asyncio.run(run_terminal_board())