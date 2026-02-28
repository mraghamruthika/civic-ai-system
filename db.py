import sqlite3

DB_NAME = "complaints.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        is_verified INTEGER DEFAULT 0
    )
    """)

    # COMPLAINTS TABLE
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
        photo1_path TEXT NOT NULL,
        photo2_path TEXT NOT NULL,
        assigned_department TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


def create_user(name, address, phone, password):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, address, phone, password, is_verified) VALUES (?, ?, ?, ?, 0)",
        (name, address, phone, password)
    )
    conn.commit()
    conn.close()


def get_user_by_phone(phone):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, address, phone, password, is_verified FROM users WHERE phone=?", (phone,))
    row = cur.fetchone()
    conn.close()
    return row


def verify_user(phone):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_verified=1 WHERE phone=?", (phone,))
    conn.commit()
    conn.close()


def insert_complaint(data):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO complaints (
            user_id, name, address, phone, complaint, category, priority,
            photo1_path, photo2_path, assigned_department, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"], data["name"], data["address"], data["phone"],
        data["complaint"], data["category"], data["priority"],
        data["photo1_path"], data["photo2_path"],
        data["assigned_department"], data["created_at"]
    ))
    conn.commit()
    conn.close()


def get_complaints_by_department(dept):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
    SELECT id, name, address, phone, complaint, category, priority, photo1_path, photo2_path, created_at
    FROM complaints
    WHERE assigned_department = ?
    ORDER BY 
      CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
      id DESC
    """, (dept,))
    rows = cur.fetchall()
    conn.close()
    return rows