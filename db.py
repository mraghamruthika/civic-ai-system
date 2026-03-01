import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("complaints.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        # Users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            verified INTEGER DEFAULT 1
        )
        """)

        # Complaints table
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
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

        # If old DB exists without status column, add it safely
        cur.execute("PRAGMA table_info(complaints)")
        cols = [row["name"] for row in cur.fetchall()]
        if "status" not in cols:
            cur.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")

        conn.commit()


def create_user(name, address, phone, password):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO users (name, address, phone, password, verified)
            VALUES (?, ?, ?, ?, 1)
        """, (name, address, phone, password))
        conn.commit()


def get_user_by_phone(phone):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        row = cur.fetchone()
        return tuple(row) if row else None


def verify_user(phone):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET verified = 1 WHERE phone = ?", (phone,))
        conn.commit()


def insert_complaint(data: dict):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO complaints (
                user_id, name, address, phone, complaint,
                category, priority, photo1_path, photo2_path,
                assigned_department, status, created_at
            )
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
            data.get("status", "Pending"),
            data.get("created_at"),
        ))
        conn.commit()


def get_complaints_by_department(dept: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM complaints
            WHERE assigned_department = ?
            ORDER BY id DESC
        """, (dept,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_complaints_by_user(user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM complaints
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]