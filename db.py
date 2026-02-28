import sqlite3
from datetime import datetime

DB_NAME = "complaints.db"


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    # Complaints table (includes status)
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
            status TEXT NOT NULL DEFAULT 'Pending',
            photo1_path TEXT,
            photo2_path TEXT,
            assigned_department TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # If older DB exists without status column, add it safely
    cur.execute("PRAGMA table_info(complaints)")
    cols = [row[1] for row in cur.fetchall()]
    if "status" not in cols:
        cur.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")

    conn.commit()
    conn.close()


# ---------------- USERS ----------------

def create_user(name, address, phone, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, address, phone, password) VALUES (?, ?, ?, ?)",
        (name, address, phone, password)
    )
    conn.commit()
    conn.close()


def get_user_by_phone(phone):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cur.fetchone()
    conn.close()
    return user


# ---------------- COMPLAINTS ----------------

def insert_complaint(data: dict):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO complaints
        (user_id, name, address, phone, complaint, category, priority, status,
         photo1_path, photo2_path, assigned_department, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("user_id"),
        data.get("name"),
        data.get("address"),
        data.get("phone"),
        data.get("complaint"),
        data.get("category"),
        data.get("priority"),
        data.get("status", "Pending"),
        data.get("photo1_path"),
        data.get("photo2_path"),
        data.get("assigned_department"),
        data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ))

    conn.commit()
    conn.close()


def get_complaints_by_department(dept):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM complaints
        WHERE assigned_department = ?
        ORDER BY
            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                ELSE 3
            END,
            id DESC
    """, (dept,))
    complaints = cur.fetchall()
    conn.close()
    return complaints


def update_complaint_status(complaint_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
    conn.commit()
    conn.close()