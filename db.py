import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "complaints.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _col_exists(conn, table, col):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in rows)


def init_db():
    conn = get_db()

    # users
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        verified INTEGER DEFAULT 0
    )
    """)

    # admins
    conn.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        verified INTEGER DEFAULT 0
    )
    """)

    # complaints
    conn.execute("""
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
        created_at TEXT
    )
    """)

    # ---- MIGRATIONS (add missing columns safely) ----
    if not _col_exists(conn, "complaints", "status"):
        conn.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")
    if not _col_exists(conn, "complaints", "admin_proof_path"):
        conn.execute("ALTER TABLE complaints ADD COLUMN admin_proof_path TEXT DEFAULT ''")

    conn.commit()
    conn.close()


# ---------------- USERS ----------------
def create_user(name, address, phone, password):
    conn = get_db()
    ex = conn.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
    if ex:
        conn.close()
        return False, "Phone already registered"
    conn.execute(
        "INSERT INTO users (name,address,phone,password,verified) VALUES (?,?,?,?,0)",
        (name, address, phone, password)
    )
    conn.commit()
    conn.close()
    return True, None


def get_user_by_phone(phone):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user(phone):
    conn = get_db()
    conn.execute("UPDATE users SET verified=1 WHERE phone=?", (phone,))
    conn.commit()
    conn.close()


# ---------------- ADMINS ----------------
def create_admin(name, email, password):
    conn = get_db()
    ex = conn.execute("SELECT id FROM admins WHERE email=?", (email,)).fetchone()
    if ex:
        conn.close()
        return False, "Email already registered"
    conn.execute(
        "INSERT INTO admins (name,email,password,verified) VALUES (?,?,?,0)",
        (name, email, password)
    )
    conn.commit()
    conn.close()
    return True, None


def get_admin_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM admins WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_admin(email):
    conn = get_db()
    conn.execute("UPDATE admins SET verified=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()


# ---------------- COMPLAINTS ----------------
def insert_complaint(data: dict):
    conn = get_db()
    conn.execute("""
        INSERT INTO complaints
        (user_id,name,address,phone,complaint,category,priority,photo1_path,photo2_path,
         assigned_department,status,admin_proof_path,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
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
        data.get("admin_proof_path", ""),
        data.get("created_at")
    ))
    conn.commit()
    conn.close()


def get_complaints_by_user(user_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_complaints_by_department(dept: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM complaints WHERE assigned_department=? ORDER BY id DESC",
        (dept,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_complaint_status(complaint_id: int, status: str, admin_proof_path: str = ""):
    conn = get_db()
    if admin_proof_path:
        conn.execute(
            "UPDATE complaints SET status=?, admin_proof_path=? WHERE id=?",
            (status, admin_proof_path, complaint_id)
        )
    else:
        conn.execute(
            "UPDATE complaints SET status=? WHERE id=?",
            (status, complaint_id)
        )
    conn.commit()
    conn.close()