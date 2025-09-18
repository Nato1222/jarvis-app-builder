import sqlite3
import os
from passlib.context import CryptContext

# Get the absolute path to the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the absolute path to the SQL file
SQL_FILE = os.path.join(script_dir, 'migrations/001_init.sql')
DB_NAME = os.path.join(script_dir, '../jarvisone.db')

def get_connection():
    """
    Creates a new database connection to the SQLite database
    specified by the DB_NAME variable.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Enable access to columns by name
    return conn

def create_tables():
    """
    Reads the SQL DDL from models_sql.sql and executes it to create
    the database schema in the SQLite database file.
    Also, ensures a default user 'ceo' exists.
    """
    db_exists = os.path.exists(DB_NAME)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    with open(SQL_FILE, 'r') as f:
        sql_script = f.read()
    
    try:
        cursor.executescript(sql_script)
        conn.commit()
        print("Database and tables created successfully.")
        
        # --- Add default user ---
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        ceo_username = "ceo"
        ceo_password = "jarvis2025"
        
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (ceo_username,))
        if cursor.fetchone() is None:
            hashed_password = pwd_context.hash(ceo_password)
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (ceo_username, hashed_password)
            )
            conn.commit()
            print(f"Default user '{ceo_username}' created.")
        else:
            print(f"Default user '{ceo_username}' already exists.")
        # -------------------------

        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables found in the database:")
        for table in tables:
            print(f"- {table[0]}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
