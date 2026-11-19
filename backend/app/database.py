
import sqlite3
from datetime import datetime
from .config import DATABASE_PATH


def conn():
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with conn() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                filename TEXT,
                created_at TEXT,
                status TEXT
            )
        """)

        columns = [
            row["name"]
            for row in db.execute("PRAGMA table_info(projects)").fetchall()
        ]

        if "user_id" not in columns:
            db.execute("ALTER TABLE projects ADD COLUMN user_id TEXT")

        db.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                result_json TEXT,
                created_at TEXT
            )
        """)

        # AI Chat Assistant message history
        db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        db.commit()


def create_user(user_id, email, password_hash):
    with conn() as db:
        db.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email, password_hash, datetime.utcnow().isoformat())
        )
        db.commit()


def get_user_by_email(email):
    with conn() as db:
        row = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id):
    with conn() as db:
        row = db.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None


def add_project(pid, name, filename, user_id):
    with conn() as db:
        db.execute(
            "INSERT INTO projects (id, name, filename, created_at, status, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, name, filename, datetime.utcnow().isoformat(), "Uploaded", user_id)
        )
        db.commit()


def list_projects(user_id):
    with conn() as db:
        return [
            dict(x) for x in db.execute(
                "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
        ]


def get_project(pid, user_id):
    with conn() as db:
        row = db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (pid, user_id)
        ).fetchone()
        return dict(row) if row else None


def save_analysis(pid, result):
    with conn() as db:
        db.execute(
            "INSERT INTO analyses(project_id, result_json, created_at) VALUES(?,?,?)",
            (pid, result, datetime.utcnow().isoformat())
        )
        db.execute(
            "UPDATE projects SET status='Analyzed' WHERE id=?",
            (pid,)
        )
        db.commit()


def latest_analysis(pid):
    with conn() as db:
        row = db.execute(
            "SELECT result_json FROM analyses WHERE project_id=? ORDER BY id DESC LIMIT 1",
            (pid,)
        ).fetchone()
        return row["result_json"] if row else None


def save_chat_message(user_id, project_id, role, message):
    with conn() as db:
        db.execute(
            """
            INSERT INTO chat_messages
            (user_id, project_id, role, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                project_id,
                role,
                message,
                datetime.utcnow().isoformat()
            )
        )
        db.commit()


def get_chat_history(user_id, project_id, limit=50):
    with conn() as db:
        rows = db.execute(
            """
            SELECT role, message, created_at
            FROM chat_messages
            WHERE user_id = ? AND project_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, project_id, limit)
        ).fetchall()

        return [dict(row) for row in reversed(rows)]
