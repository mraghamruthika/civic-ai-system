from flask import Flask, request, render_template, redirect, url_for, session
import os
from datetime import datetime
import random

from db import (
    init_db, create_user, get_user_by_phone, verify_user,
    insert_complaint, get_complaints_by_department, get_complaints_by_user
)

app = Flask(__name__)
app.secret_key = "change_this_to_any_random_string"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()


# ---------------- AI LOGIC ----------------
def get_category(text: str) -> str:
    text = (text or "").lower()

    if any(k in text for k in ["fire", "accident", "blast", "electrocution", "collapse"]):
        return "Emergency"
    if any(k in text for k in ["pothole", "road", "bridge", "footpath"]):
        return "Road & Infrastructure"
    if any(k in text for k in ["water", "leak", "pipeline"]):
        return "Water Supply"
    if any(k in text for k in ["drain", "sewage", "overflow"]):
        return "Drainage & Sewage"
    if any(k in text for k in ["garbage", "waste", "trash"]):
        return "Sanitation"
    if any(k in text for k in ["electricity", "power", "transformer"]):
        return "Electricity"
    if any(k in text for k in ["street light", "lamp post", "streetlight"]):
        return "Street Lights"
    if any(k in text for k in ["mosquito", "dengue", "fever"]):
        return "Health & Hygiene"
    if any(k in text for k in ["dog", "stray", "cow"]):
        return "Animal Control"

    return "General"


def get_priority(text: str) -> str:
    text = (text or "").lower()
    high_keywords = ["accident", "fire", "hospital", "danger", "injury", "bleeding"]
    return "High" if any(w in text for w in high_keywords) else "Medium"


def get_department(category: str) -> str:
    mapping = {
        "Road & Infrastructure": "roads",
        "Water Supply": "water",
        "Drainage & Sewage": "drainage",
        "Sanitation": "sanitation",
        "Electricity": "electricity",
        "Street Lights": "streetlights",
        "Health & Hygiene": "health",
        "Animal Control": "animals",
        "Emergency": "emergency",
        "General": "general"
    }
    return mapping.get(category, "general")


# ---------------- LANDING ----------------
@app.route("/")
def landing():
    return render_template("landing.html")


# ---------------- USER AUTH ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        phone = request.form.get("phone")
        password = request.form.get("password")

        create_user(name, address, phone, password)

        otp = str(random.randint(100000, 999999))
        session["otp"] = otp
        session["otp_phone"] = phone

        return redirect(url_for("verify_otp"))

    return render_template("register.html", msg=msg)


@app.route("/verify", methods=["GET", "POST"])
def verify_otp():
    msg = None
    otp_demo = session.get("otp")

    if request.method == "POST":
        if request.form.get("otp") == session.get("otp"):
            verify_user(session.get("otp_phone"))
            return redirect(url_for("login"))
        else:
            msg = "Incorrect OTP"

    return render_template("verify.html", msg=msg, otp_demo=otp_demo)


@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None
    if request.method == "POST":
        phone = request.form.get("phone")
        password = request.form.get("password")

        user = get_user_by_phone(phone)
        if user and user["password"] == password and user["verified"] == 1:
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["address"] = user["address"]
            session["phone"] = user["phone"]
            return redirect(url_for("home"))
        else:
            msg = "Invalid credentials or not verified"

    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ---------------- USER HOME ----------------
@app.route("/home", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    prediction = None
    priority = None
    dept_message = None

    if request.method == "POST":
        complaint = request.form.get("complaint")
        photo1 = request.files.get("photo1")
        photo2 = request.files.get("photo2")

        if not complaint:
            dept_message = "Please type your complaint."
        elif not photo1 or photo1.filename == "" or not photo2 or photo2.filename == "":
            dept_message = "Please upload both proof images."
        else:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename1 = f"{timestamp}_1_{photo1.filename}"
            filename2 = f"{timestamp}_2_{photo2.filename}"

            photo1_path = os.path.join(app.config["UPLOAD_FOLDER"], filename1).replace("\\", "/")
            photo2_path = os.path.join(app.config["UPLOAD_FOLDER"], filename2).replace("\\", "/")

            photo1.save(photo1_path)
            photo2.save(photo2_path)

            prediction = get_category(complaint)
            priority = get_priority(complaint)
            assigned_department = get_department(prediction)

            insert_complaint({
                "user_id": session["user_id"],
                "name": session["name"],
                "address": session["address"],
                "phone": session["phone"],
                "complaint": complaint,
                "category": prediction,
                "priority": priority,
                "status": "Pending",
                "photo1_path": photo1_path,
                "photo2_path": photo2_path,
                "assigned_department": assigned_department,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            dept_message = f"Complaint forwarded to {assigned_department.upper()} department."

    return render_template(
        "index.html",
        prediction=prediction,
        priority=priority,
        dept_message=dept_message,
        username=session.get("name")
    )


# ✅ FIX: My complaints route
@app.route("/my-complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect(url_for("login"))

    complaints = get_complaints_by_user(session["user_id"])
    return render_template("my_complaints.html", complaints=complaints, username=session.get("name"))


# ---------------- ADMIN LOGIN (simple) ----------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    msg = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == "admin" and password == "admin123":
            session["is_admin"] = True
            return redirect(url_for("admin_home"))
        else:
            msg = "Invalid admin credentials"

    return f"""
    <html><head><title>Admin Login</title></head>
    <body style="font-family:Arial;max-width:420px;margin:60px auto;">
      <h2>Admin Login</h2>
      <p style="color:red;">{msg or ""}</p>
      <form method="POST">
        <label>Username</label><br>
        <input name="username" style="width:100%;padding:10px;"><br><br>
        <label>Password</label><br>
        <input type="password" name="password" style="width:100%;padding:10px;"><br><br>
        <button style="padding:10px 16px;">Login</button>
      </form>
      <p style="margin-top:14px;"><a href="/">Back</a></p>
    </body></html>
    """


@app.route("/admin")
def admin_home():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    return """
    <html><head><title>Admin</title></head>
    <body style="font-family:Arial;max-width:700px;margin:50px auto;">
      <h2>Admin Dashboard</h2>
      <p>Open a department dashboard:</p>
      <ul>
        <li><a href="/dept/roads">Roads</a></li>
        <li><a href="/dept/water">Water</a></li>
        <li><a href="/dept/drainage">Drainage</a></li>
        <li><a href="/dept/sanitation">Sanitation</a></li>
        <li><a href="/dept/electricity">Electricity</a></li>
        <li><a href="/dept/streetlights">Street Lights</a></li>
        <li><a href="/dept/health">Health</a></li>
        <li><a href="/dept/animals">Animals</a></li>
        <li><a href="/dept/emergency">Emergency</a></li>
        <li><a href="/dept/general">General</a></li>
      </ul>
      <p><a href="/logout">Logout</a></p>
    </body></html>
    """


# ---------------- DEPARTMENT DASHBOARD ----------------
@app.route("/dept/<dept>")
def dept_dashboard(dept):
    complaints = get_complaints_by_department(dept)
    dept_name = dept.replace("_", " ").title()
    return render_template("department.html", complaints=complaints, dept_name=dept_name, dept=dept)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)