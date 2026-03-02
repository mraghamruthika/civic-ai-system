import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "complaints.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    cols = [row["name"] for row in cur.fetchall()]
    return column_name in cols


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        verified INTEGER DEFAULT 0
    )
    """)

    # ADMINS (with department)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        department TEXT DEFAULT 'general',
        verified INTEGER DEFAULT 0
    )
    """)

    # COMPLAINTS
    cursor.execute("""
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
        status TEXT DEFAULT 'Pending',
        admin_proof_path TEXT DEFAULT ''
    )
    """)

    # ---- Safe migrations (for older DBs) ----
    # Add admins.department if missing
    if not _column_exists(conn, "admins", "department"):
        conn.execute("ALTER TABLE admins ADD COLUMN department TEXT DEFAULT 'general'")

    # Add complaints.admin_proof_path if missing
    if not _column_exists(conn, "complaints", "admin_proof_path"):
        conn.execute("ALTER TABLE complaints ADD COLUMN admin_proof_path TEXT DEFAULT ''")

    conn.commit()
    conn.close()


# ---------------- USERS ----------------

def create_user(name, address, phone, password):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE phone=?", (phone,))
    if cursor.fetchone():
        conn.close()
        return False, "Phone already registered"

    cursor.execute(
        "INSERT INTO users (name,address,phone,password,verified) VALUES (?,?,?,?,0)",
        (name, address, phone, password)
    )

    conn.commit()
    conn.close()
    return True, None


def get_user_by_phone(phone):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone=?", (phone,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user(phone):
    conn = get_db()
    conn.execute("UPDATE users SET verified=1 WHERE phone=?", (phone,))
    conn.commit()
    conn.close()


# ---------------- ADMINS ----------------

def create_admin(name, email, password, department="general"):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM admins WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        return False, "Email already registered"

    cursor.execute(
        "INSERT INTO admins (name,email,password,department,verified) VALUES (?,?,?,?,0)",
        (name, email, password, department)
    )

    conn.commit()
    conn.close()
    return True, None


def get_admin_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_admin(email):
    conn = get_db()
    conn.execute("UPDATE admins SET verified=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()


# ---------------- COMPLAINTS ----------------

def insert_complaint(data):
    conn = get_db()
    conn.execute("""
        INSERT INTO complaints
        (user_id,name,address,phone,complaint,category,priority,
         photo1_path,photo2_path,assigned_department,created_at,
         status,admin_proof_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["user_id"],
        data["name"],
        data["address"],
        data["phone"],
        data["complaint"],
        data["category"],
        data["priority"],
        data["photo1_path"],
        data["photo2_path"],
        data["assigned_department"],
        data["created_at"],
        data.get("status", "Pending"),
        data.get("admin_proof_path", "")
    ))
    conn.commit()
    conn.close()


def get_complaints_by_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_complaints_by_department(dept):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM complaints WHERE assigned_department=? ORDER BY id DESC",
        (dept,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_complaint_by_id(complaint_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_complaint_status(complaint_id, status, admin_proof_path=""):
    conn = get_db()
    conn.execute(
        "UPDATE complaints SET status=?, admin_proof_path=? WHERE id=?",
        (status, admin_proof_path, complaint_id)
    )
    conn.commit()
    conn.close()