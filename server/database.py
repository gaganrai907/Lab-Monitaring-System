import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "college_lab.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    # ==========================================
    # PC TABLE
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            lab_name TEXT NOT NULL,

            pc_number TEXT NOT NULL,

            device_id TEXT NOT NULL UNIQUE,

            hostname TEXT,

            status TEXT DEFAULT 'OFFLINE',

            last_heartbeat TEXT,

            agent_version TEXT,

            approved INTEGER DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    # ==========================================
    # USERS TABLE
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            telegram_id TEXT NOT NULL UNIQUE,

            name TEXT,

            username TEXT,

            role TEXT NOT NULL DEFAULT 'FACULTY',

            assigned_lab TEXT,

            active INTEGER DEFAULT 1,

            created_at TEXT NOT NULL
        )
    """)

        # ALERTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'WARNING',
            status TEXT DEFAULT 'NEW',
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()

    connection.close()