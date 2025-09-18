import sqlite3
import os

DATABASE_FILE = "jarvisone.db"

# Determine the absolute path to the database file within the JarvisOne package
# This ensures that no matter where the script is run from, it finds the correct DB.
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', DATABASE_FILE))


def get_connection():
    """
    Establishes a connection to the SQLite database and returns rows as dict-like objects.
    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
