import sqlite3
import os
import uuid

# This script adds a sample strategy to the database.

# Construct the absolute path to the database file
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(script_dir, '../jarvisone.db')

def add_sample_strategy():
    """Adds a sample 'pending' strategy to the database and assigns it to the CEO."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 1. Get the user_id for the 'ceo'
        cursor.execute("SELECT user_id FROM users WHERE username = 'ceo'")
        ceo = cursor.fetchone()
        if not ceo:
            print("Default user 'ceo' not found. Please run create_tables.py first.")
            return
        ceo_id = ceo[0]

        # 2. Check if the strategy already exists
        cursor.execute("SELECT 1 FROM strategies WHERE topic = ? AND user_id = ?", ('Initial Market Analysis', ceo_id))
        if cursor.fetchone():
            print("Sample strategy 'Initial Market Analysis' already exists for the CEO.")
            return

        # 3. Insert the new strategy
        strategy_id = str(uuid.uuid4())
        topic = 'Initial Market Analysis'
        ceo_notes = 'Analyze the current market trends for AI-powered assistants.'
        status = 'pending_approval'

        cursor.execute(
            "INSERT INTO strategies (strategy_id, user_id, topic, ceo_notes, status) VALUES (?, ?, ?, ?, ?)",
            (strategy_id, ceo_id, topic, ceo_notes, status)
        )
        conn.commit()
        print("Successfully added sample strategy and assigned it to the CEO.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    add_sample_strategy()
