import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("complaints.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        verified INTEGER DEFAULT 0
    )
    """)

    # Admins table (email-based)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        verified INTEGER DEFAULT 0
    )
    """)

    # Complaints table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        phone TEXT NOT NULL,
        complaint TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        assigned_department TEXT NOT NULL,
        photo1_path TEXT,
        photo2_path TEXT,
        status TEXT DEFAULT 'Pending',
        admin_proof TEXT DEFAULT '',
        status_updated_at TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


# ---------------- USER FUNCTIONS ----------------

def create_user(name, address, phone, password):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO users (name, address, phone, password, verified)
        VALUES (?, ?, ?, ?, COALESCE((SELECT verified FROM users WHERE phone=?), 0))
    """, (name, address, phone, password, phone))
    conn.commit()
    conn.close()


def get_user_by_phone(phone):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE phone=?", (phone,))
    row = cur.fetchone()
    conn.close()
    return row


def verify_user(phone):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET verified=1 WHERE phone=?", (phone,))
    conn.commit()
    conn.close()


# ---------------- ADMIN FUNCTIONS ----------------

def create_admin(name, email, password):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO admins (name, email, password, verified)
        VALUES (?, ?, ?, COALESCE((SELECT verified FROM admins WHERE email=?), 0))
    """, (name, email, password, email))
    conn.commit()
    conn.close()


def get_admin_by_email(email):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins WHERE email=?", (email,))
    row = cur.fetchone()
    conn.close()
    return row


def verify_admin(email):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE admins SET verified=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()


# ---------------- COMPLAINT FUNCTIONS ----------------

def insert_complaint(data: dict):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO complaints (
            user_id, name, address, phone, complaint,
            category, priority, assigned_department,
            photo1_path, photo2_path,
            status, admin_proof, status_updated_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["name"],
        data["address"],
        data["phone"],
        data["complaint"],
        data["category"],
        data["priority"],
        data["assigned_department"],
        data.get("photo1_path", ""),
        data.get("photo2_path", ""),
        data.get("status", "Pending"),
        data.get("admin_proof", ""),
        data.get("status_updated_at", ""),
        data["created_at"]
    ))
    conn.commit()
    conn.close()


def get_complaints_by_department(dept):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM complaints
        WHERE assigned_department=?
        ORDER BY id DESC
    """, (dept,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_complaints_by_user(user_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM complaints
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_complaint_status(complaint_id, new_status, admin_proof):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE complaints
        SET status=?,
            admin_proof=?,
            status_updated_at=?
        WHERE id=?
    """, (
        new_status,
        admin_proof,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        complaint_id
    ))
    conn.commit()
    conn.close()