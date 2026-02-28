import sqlite3


DB_NAME = "complaints.db"


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # ✅ so templates can use dict-style keys
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ---------- USERS TABLE ----------
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

    # ---------- COMPLAINTS TABLE ----------
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
        photo1_path TEXT,
        photo2_path TEXT,
        assigned_department TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT DEFAULT 'Pending'
    )
    """)

    # ✅ Safe migration: add status column if DB was created earlier without it
    cols = [r["name"] for r in cur.execute("PRAGMA table_info(complaints)").fetchall()]
    if "status" not in cols:
        cur.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")

    conn.commit()
    conn.close()


# ---------------- USER FUNCTIONS ----------------

def create_user(name, address, phone, password):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (name, address, phone, password, verified)
            VALUES (?, ?, ?, ?, 0)
        """, (name, address, phone, password))
        conn.commit()
    except sqlite3.IntegrityError:
        # phone already exists
        pass
    finally:
        conn.close()


def get_user_by_phone(phone):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cur.fetchone()
    conn.close()
    return user


def verify_user(phone):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET verified = 1 WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()


# ---------------- COMPLAINT FUNCTIONS ----------------

def insert_complaint(data: dict):
    conn = get_conn()
    cur = conn.cursor()

    # Default status for new complaints
    status = data.get("status", "Pending")

    cur.execute("""
        INSERT INTO complaints
        (user_id, name, address, phone, complaint, category, priority,
         photo1_path, photo2_path, assigned_department, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["name"],
        data["address"],
        data["phone"],
        data["complaint"],
        data["category"],
        data["priority"],
        data.get("photo1_path"),
        data.get("photo2_path"),
        data["assigned_department"],
        data["created_at"],
        status
    ))

    conn.commit()
    conn.close()


def get_complaints_by_department(dept: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM complaints
        WHERE assigned_department = ?
        ORDER BY id DESC
    """, (dept,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ✅ For "My Complaints" feature
def get_complaints_by_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM complaints
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_complaint_by_id(complaint_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_complaint_status(complaint_id: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
    conn.commit()
    conn.close()