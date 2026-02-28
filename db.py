import sqlite3
from datetime import datetime

DB_NAME = "complaints.db"


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

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

    cols = [r["name"] for r in cur.execute("PRAGMA table_info(complaints)").fetchall()]
    if "status" not in cols:
        cur.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")

    conn.commit()
    conn.close()



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
    user = cur.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return user



def create_admin(name, email, phone, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO admins (name, email, phone, password, verified, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
    """, (name, email, phone, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_admin_by_email(email):
    conn = get_conn()
    cur = conn.cursor()
    admin = cur.execute("SELECT * FROM admins WHERE email=?", (email,)).fetchone()
    conn.close()
    return admin


def verify_admin(email):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE admins SET verified=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()



def insert_complaint(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO complaints
        (user_id, name, address, phone, complaint, category, priority, status,
         photo1_path, photo2_path, assigned_department, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["name"],
        data["address"],
        data["phone"],
        data["complaint"],
        data["category"],
        data["priority"],
        data.get("status", "Pending"),
        data.get("photo1_path"),
        data.get("photo2_path"),
        data["assigned_department"],
        data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ))
    conn.commit()
    conn.close()


def get_complaints_by_department(dept):
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT * FROM complaints
        WHERE assigned_department=?
        ORDER BY
            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                ELSE 3
            END,
            id DESC
    """, (dept,)).fetchall()
    conn.close()
    return rows


def get_all_complaints():
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def update_complaint_status(complaint_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status=? WHERE id=?", (status, complaint_id))
    conn.commit()
    conn.close()


def get_complaints_by_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT * FROM complaints
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows


def get_complaint_by_id(complaint_id):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    conn.close()
    return row