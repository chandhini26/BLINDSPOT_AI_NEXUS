import sqlite3
from datetime import datetime
from .config import DATABASE_PATH

def conn():
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with conn() as db:
        db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT, filename TEXT, created_at TEXT, status TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS analyses (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, result_json TEXT, created_at TEXT)")
        db.commit()

def add_project(pid, name, filename):
    with conn() as db:
        db.execute("INSERT INTO projects VALUES(?,?,?,?,?)", (pid,name,filename,datetime.utcnow().isoformat(),"Uploaded"))
        db.commit()

def list_projects():
    with conn() as db:
        return [dict(x) for x in db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()]

def get_project(pid):
    with conn() as db:
        row = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None

def save_analysis(pid, result):
    with conn() as db:
        db.execute("INSERT INTO analyses(project_id,result_json,created_at) VALUES(?,?,?)", (pid,result,datetime.utcnow().isoformat()))
        db.execute("UPDATE projects SET status='Analyzed' WHERE id=?", (pid,))
        db.commit()

def latest_analysis(pid):
    with conn() as db:
        row = db.execute("SELECT result_json FROM analyses WHERE project_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        return row["result_json"] if row else None
