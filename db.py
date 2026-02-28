import sqlite3
from datetime import datetime

DB_FILE = "complaints.db"


def get_conn():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = get_conn()
    cur = con.cursor()

    # users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        verified INTEGER DEFAULT 0
    )
    """)

    # complaints table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        address TEXT,
        phone TEXT,
        complaint TEXT,
        category TEXT,
        priority TEXT,
        photo1_path TEXT,
        photo2_path TEXT,
        assigned_department TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    # Ensure status column exists even if older DB
    cols = [r["name"] for r in cur.execute("PRAGMA table_info(complaints)").fetchall()]
    if "status" not in cols:
        cur.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")

    con.commit()
    con.close()


# ---------------- USERS ----------------

def create_user(name, address, phone, password):
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO users (name, address, phone, password, verified) VALUES (?, ?, ?, ?, COALESCE((SELECT verified FROM users WHERE phone=?), 0))",
        (name, address, phone, password, phone)
    )
    con.commit()
    con.close()


def get_user_by_phone(phone):
    con = get_conn()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    con.close()
    return row


def verify_user(phone):
    con = get_conn()
    cur = con.cursor()
    cur.execute("UPDATE users SET verified=1 WHERE phone=?", (phone,))
    con.commit()
    con.close()


# ---------------- COMPLAINTS ----------------

def insert_complaint(data: dict):
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO complaints
        (user_id, name, address, phone, complaint, category, priority,
         photo1_path, photo2_path, assigned_department, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("user_id"),
        data.get("name"),
        data.get("address"),
        data.get("phone"),
        data.get("complaint"),
        data.get("category"),
        data.get("priority"),
        data.get("photo1_path"),
        data.get("photo2_path"),
        data.get("assigned_department"),
        data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        data.get("status", "Pending")
    ))
    con.commit()
    con.close()


def get_complaints_by_department(dept: str):
    con = get_conn()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT * FROM complaints
        WHERE assigned_department=?
        ORDER BY id DESC
    """, (dept,)).fetchall()
    con.close()
    return rows


def get_all_complaints():
    con = get_conn()
    cur = con.cursor()
    rows = cur.execute("""
        SELECT * FROM complaints
        ORDER BY id DESC
    """).fetchall()
    con.close()
    return rows


def update_complaint_status(complaint_id: int, status: str):
    con = get_conn()
    cur = con.cursor()
    cur.execute("UPDATE complaints SET status=? WHERE id=?", (status, complaint_id))
    con.commit()
    con.close()