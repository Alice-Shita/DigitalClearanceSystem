import sqlite3

DB_NAME = "clearance.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # ---------------- STUDENTS ----------------
    conn.execute("""
    CREATE TABLE IF NOT EXISTS students (
        sid TEXT PRIMARY KEY,
        data TEXT NOT NULL
    )
    """)

    # ---------------- USERS ----------------
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        data TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()