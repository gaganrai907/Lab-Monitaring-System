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

    # ============================================================
    # PCs
    # ============================================================

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

    # ============================================================
    # USERS
    # ============================================================

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

    # ============================================================
    # ALERTS
    # ============================================================

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

    # ============================================================
    # SETTINGS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # AI restriction default = ENABLED
    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('ai_restriction', '1')
    """)

    connection.commit()
    connection.close()


# ============================================================
# SETTINGS
# ============================================================

def get_setting(key: str, default=None):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT value
        FROM settings
        WHERE key = ?
    """, (key,))

    row = cursor.fetchone()

    connection.close()

    if not row:
        return default

    return row["value"]


def set_setting(key: str, value: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (key, value))

    connection.commit()
    connection.close()


def is_ai_restriction_enabled():

    value = get_setting("ai_restriction", "1")

    return value == "1"


# ============================================================
# DELETE ALERT HISTORY
# ============================================================

def delete_all_alerts():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM alerts")

    deleted_count = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted_count


def delete_alerts_for_lab(lab_name: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM alerts
        WHERE device_id IN (
            SELECT device_id
            FROM pcs
            WHERE lab_name = ?
        )
    """, (lab_name,))

    deleted_count = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted_count