from flask import Flask, render_template, request, redirect, session, url_for
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# DATABASE CONNECTION
# ==============================

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ==============================
# SIMPLE AI LOGIC (RULE BASED)
# ==============================

def get_category(text: str) -> str:
    text = (text or "").lower()
    if "road" in text or "pothole" in text:
        return "Road"
    elif "garbage" in text or "waste" in text:
        return "Sanitation"
    elif "water" in text:
        return "Water"
    elif "electric" in text or "power" in text:
        return "Electricity"
    else:
        return "General"

def get_priority(text: str) -> str:
    text = (text or "").lower()
    high_words = ["accident", "fire", "danger", "hospital", "blast"]
    return "High" if any(w in text for w in high_words) else "Medium"

# ==============================
# LANDING PAGE
# ==============================

@app.route("/")
def landing():
    return render_template("choose_login.html")

# ==============================
# USER LOGIN
# ==============================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["name"]
            return redirect("/home")

    return render_template("login.html")

# ==============================
# HOME PAGE (USER DASHBOARD)
# ==============================

@app.route("/home", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect("/login")

    dept_message = None
    prediction = None
    priority = None

    if request.method == "POST":
        complaint = request.form["complaint"]

        photo1 = request.files["photo1"]
        photo2 = request.files["photo2"]

        photo1_path = ""
        photo2_path = ""

        if photo1:
            photo1_path = os.path.join(UPLOAD_FOLDER, photo1.filename)
            photo1.save(photo1_path)

        if photo2:
            photo2_path = os.path.join(UPLOAD_FOLDER, photo2.filename)
            photo2.save(photo2_path)

        prediction = get_category(complaint)
        priority = get_priority(complaint)

        conn = get_db()
        conn.execute("""
            INSERT INTO complaints 
            (user_id, name, complaint, category, priority, status, photo1_path, photo2_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            session["username"],
            complaint,
            prediction,
            priority,
            "Pending",
            photo1_path,
            photo2_path,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        dept_message = f"Complaint sent to {prediction} Department"

    return render_template(
        "index.html",
        username=session["username"],
        prediction=prediction,
        priority=priority,
        dept_message=dept_message
    )

# ==============================
# VIEW MY COMPLAINTS
# ==============================

@app.route("/my-complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    complaints = conn.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("my_complaints.html", complaints=complaints)

# ==============================
# ADMIN LOGIN
# ==============================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        admin = conn.execute(
            "SELECT * FROM admins WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if admin:
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            return redirect("/admin/dashboard")

    return render_template("admin_login.html")

# ==============================
# ADMIN DASHBOARD
# ==============================

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db()
    complaints = conn.execute(
        "SELECT * FROM complaints ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        admin_name=session["admin_name"]
    )

# ==============================
# UPDATE STATUS
# ==============================

@app.route("/complaint/<int:cid>/status", methods=["POST"])
def update_status(cid):
    if "admin_id" not in session:
        return redirect("/admin/login")

    new_status = request.form["status"]

    conn = get_db()
    conn.execute(
        "UPDATE complaints SET status=? WHERE id=?",
        (new_status, cid)
    )
    conn.commit()
    conn.close()

    return redirect("/admin/dashboard")

# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")

# ==============================

if __name__ == "__main__":
    app.run(debug=True)