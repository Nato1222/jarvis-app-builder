import sqlite3

DB_FILE = "jarvisone.db"

def inspect_users():
    """Connects to the database and prints all users."""
    print(f"--- Inspecting users in {DB_FILE} ---")
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users ORDER BY user_id ASC;")
        users = cursor.fetchall()

        if not users:
            print("No users found in the database.")
        else:
            print(f"Found {len(users)} user(s):")
            for user in users:
                print(dict(user))

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    print("--- Inspection complete ---")

if __name__ == "__main__":
    inspect_users()
