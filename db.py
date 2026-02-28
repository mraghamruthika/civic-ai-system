import sqlite3

DB_NAME = "complaints.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users table
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
        status TEXT DEFAULT 'Pending',
        photo1_path TEXT,
        photo2_path TEXT,
        assigned_department TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------- USER ----------
def create_user(name, address, phone, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO users (name, address, phone, password, verified)
        VALUES (?, ?, ?, ?, COALESCE((SELECT verified FROM users WHERE phone=?), 0))
    """, (name, address, phone, password, phone))
    conn.commit()
    conn.close()


def get_user_by_phone(phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE phone=?", (phone,))
    row = cur.fetchone()
    conn.close()
    return row


def verify_user(phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET verified=1 WHERE phone=?", (phone,))
    conn.commit()
    conn.close()


# ---------- COMPLAINTS ----------
def insert_complaint(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO complaints (
            user_id, name, address, phone, complaint,
            category, priority, status,
            photo1_path, photo2_path,
            assigned_department, created_at
        )
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
        data["photo1_path"],
        data["photo2_path"],
        data["assigned_department"],
        data["created_at"]
    ))
    conn.commit()
    conn.close()


def get_complaints_by_department(dept):
    conn = get_connection()
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM complaints
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows