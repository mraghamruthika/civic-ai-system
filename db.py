import sqlite3
import os

# Render persistent disk support:
# In Render set env: DB_DIR=/var/data and attach a disk mounted to /var/data
DEFAULT_DB_DIR = os.environ.get("DB_DIR", "")
if DEFAULT_DB_DIR:
    os.makedirs(DEFAULT_DB_DIR, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = DEFAULT_DB_DIR if DEFAULT_DB_DIR else BASE_DIR
DB_PATH = os.path.join(DB_DIR, "complaints.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn, table, col):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        verified INTEGER DEFAULT 0,
        home_district TEXT DEFAULT 'Unknown',
        home_taluk TEXT DEFAULT 'Unknown'
    )
    """)

    # ADMINS (includes district head)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        verified INTEGER DEFAULT 0,
        role TEXT DEFAULT 'admin',              -- 'admin' or 'head'
        department TEXT DEFAULT 'general',
        district TEXT DEFAULT 'Unknown',
        taluk TEXT DEFAULT 'all'                -- for head, keep 'all'
    )
    """)

    # COMPLAINTS
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
        status TEXT DEFAULT 'Pending',
        admin_proof_path TEXT DEFAULT '',
        incident_district TEXT DEFAULT 'Unknown',
        incident_taluk TEXT DEFAULT 'Unknown',
        incident_area TEXT DEFAULT ''
    )
    """)

    # Backward compatible ALTER (if old DB exists)
    # users:
    if not _column_exists(conn, "users", "home_district"):
        cur.execute("ALTER TABLE users ADD COLUMN home_district TEXT DEFAULT 'Unknown'")
    if not _column_exists(conn, "users", "home_taluk"):
        cur.execute("ALTER TABLE users ADD COLUMN home_taluk TEXT DEFAULT 'Unknown'")

    # admins:
    if not _column_exists(conn, "admins", "role"):
        cur.execute("ALTER TABLE admins ADD COLUMN role TEXT DEFAULT 'admin'")
    if not _column_exists(conn, "admins", "department"):
        cur.execute("ALTER TABLE admins ADD COLUMN department TEXT DEFAULT 'general'")
    if not _column_exists(conn, "admins", "district"):
        cur.execute("ALTER TABLE admins ADD COLUMN district TEXT DEFAULT 'Unknown'")
    if not _column_exists(conn, "admins", "taluk"):
        cur.execute("ALTER TABLE admins ADD COLUMN taluk TEXT DEFAULT 'all'")

    # complaints:
    if not _column_exists(conn, "complaints", "incident_district"):
        cur.execute("ALTER TABLE complaints ADD COLUMN incident_district TEXT DEFAULT 'Unknown'")
    if not _column_exists(conn, "complaints", "incident_taluk"):
        cur.execute("ALTER TABLE complaints ADD COLUMN incident_taluk TEXT DEFAULT 'Unknown'")
    if not _column_exists(conn, "complaints", "incident_area"):
        cur.execute("ALTER TABLE complaints ADD COLUMN incident_area TEXT DEFAULT ''")

    conn.commit()
    conn.close()


# ---------------- USERS ----------------
def create_user(name, address, phone, password, home_district="Unknown", home_taluk="Unknown"):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE phone=?", (phone,))
    if cur.fetchone():
        conn.close()
        return False, "Phone already registered"

    cur.execute(
        "INSERT INTO users (name,address,phone,password,verified,home_district,home_taluk) VALUES (?,?,?,?,0,?,?)",
        (name, address, phone, password, home_district, home_taluk)
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


def update_user_password(phone, new_password):
    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE phone=?", (new_password, phone))
    conn.commit()
    conn.close()


# ---------------- ADMINS ----------------
def create_admin(name, email, password, role="admin", department="general", district="Unknown", taluk="all"):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM admins WHERE email=?", (email,))
    if cur.fetchone():
        conn.close()
        return False, "Email already registered"

    cur.execute("""
        INSERT INTO admins (name,email,password,verified,role,department,district,taluk)
        VALUES (?,?,?,0,?,?,?,?)
    """, (name, email, password, role, department, district, taluk))

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


def update_admin_password(email, new_password):
    conn = get_db()
    conn.execute("UPDATE admins SET password=? WHERE email=?", (new_password, email))
    conn.commit()
    conn.close()


# ---------------- COMPLAINTS ----------------
def insert_complaint(data):
    conn = get_db()
    conn.execute("""
        INSERT INTO complaints
        (user_id,name,address,phone,complaint,category,priority,
         photo1_path,photo2_path,assigned_department,created_at,
         status,admin_proof_path,incident_district,incident_taluk,incident_area)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["user_id"], data["name"], data["address"], data["phone"],
        data["complaint"], data["category"], data["priority"],
        data["photo1_path"], data["photo2_path"],
        data["assigned_department"], data["created_at"],
        data.get("status", "Pending"),
        data.get("admin_proof_path", ""),
        data.get("incident_district", "Unknown"),
        data.get("incident_taluk", "Unknown"),
        data.get("incident_area", "")
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


def get_complaints_for_admin(department, district, taluk):
    """
    Admin sees only dept + their taluk (inside their district).
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM complaints
        WHERE assigned_department=? AND incident_district=? AND incident_taluk=?
        ORDER BY id DESC
    """, (department, district, taluk)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_complaints_for_head(district, department=None, taluk=None):
    """
    District head can see all taluks in their district.
    Optional filters:
      - department
      - taluk
    """
    conn = get_db()
    q = "SELECT * FROM complaints WHERE incident_district=?"
    params = [district]

    if department and department != "all":
        q += " AND assigned_department=?"
        params.append(department)

    if taluk and taluk != "all":
        q += " AND incident_taluk=?"
        params.append(taluk)

    q += " ORDER BY id DESC"
    rows = conn.execute(q, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_complaint_status(complaint_id, status, admin_proof_path=""):
    conn = get_db()
    conn.execute(
        "UPDATE complaints SET status=?, admin_proof_path=? WHERE id=?",
        (status, admin_proof_path, complaint_id)
    )
    conn.commit()
    conn.close()