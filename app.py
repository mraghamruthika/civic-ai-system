from flask import Flask, request, render_template, redirect, url_for, session, abort
import os
from datetime import datetime
import random

from db import (
    init_db,
    # user
    create_user, get_user_by_phone, verify_user,
    # admin
    create_admin, get_admin_by_email, verify_admin,
    # complaints
    insert_complaint, get_complaints_by_department,
    update_complaint_status, get_complaints_by_user
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_to_any_random_string")

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()


# ---------------- AI LOGIC ----------------
import joblib

MODEL = None
MODEL_PATH = "model.pkl"

def load_model():
    global MODEL
    if MODEL is None:
        if os.path.exists(MODEL_PATH):
            MODEL = joblib.load(MODEL_PATH)
    return MODEL


def get_category(text: str) -> str:
    text = (text or "").strip()
    m = load_model()

    # If ML model exists, use it
    if m is not None and text:
        try:
            return m.predict([text])[0]
        except Exception:
            pass  # fallback below if something fails

    # Fallback keyword logic (safe backup)
    t = text.lower()
    if any(k in t for k in ["fire", "accident", "blast", "electrocution", "collapse"]):
        return "Emergency"
    if any(k in t for k in ["pothole", "road", "bridge", "footpath"]):
        return "Road & Infrastructure"
    if any(k in t for k in ["water", "leak", "pipeline"]):
        return "Water Supply"
    if any(k in t for k in ["drain", "sewage", "overflow"]):
        return "Drainage & Sewage"
    if any(k in t for k in ["garbage", "waste", "trash"]):
        return "Sanitation"
    if any(k in t for k in ["electricity", "power", "transformer"]):
        return "Electricity"
    if any(k in t for k in ["street light", "lamp post"]):
        return "Street Lights"
    if any(k in t for k in ["mosquito", "dengue", "fever"]):
        return "Health & Hygiene"
    if any(k in t for k in ["dog", "stray", "cow"]):
        return "Animal Control"
    return "General"

# ---------------- LANDING PAGE (User/Admin choice) ----------------
@app.route("/")
def landing():
    # Two buttons: User Login / Admin Login
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
    otp_demo = session.get("otp")  # demo OTP display

    if request.method == "POST":
        if request.form.get("otp") == session.get("otp"):
            verify_user(session.get("otp_phone"))
            return redirect(url_for("login"))
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
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["address"] = user["address"]
            session["phone"] = user["phone"]
            session["role"] = "user"
            return redirect(url_for("home"))
        msg = "Invalid credentials / Not verified"
    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ---------------- USER HOME ----------------
@app.route("/home", methods=["GET", "POST"])
def home():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    prediction = None
    priority = None
    dept_message = None

    if request.method == "POST":
        complaint = request.form.get("complaint")
        photo1 = request.files.get("photo1")
        photo2 = request.files.get("photo2")

        if not photo1 or not photo2:
            dept_message = "Please upload both proof images."
            return render_template("index.html", prediction=None, priority=None,
                                   dept_message=dept_message, username=session.get("name"))

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
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin_proof": None,
            "status_updated_at": None
        })

        dept_message = f"Complaint forwarded to {assigned_department.upper()} department."

    return render_template(
        "index.html",
        prediction=prediction,
        priority=priority,
        dept_message=dept_message,
        username=session.get("name")
    )


@app.route("/my-complaints")
def my_complaints():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    rows = get_complaints_by_user(session["user_id"])
    return render_template("my_complaints.html", complaints=rows, username=session.get("name"))


# ---------------- ADMIN AUTH (THIS FIXES YOUR 404) ----------------
@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        create_admin(name, email, password)

        otp = str(random.randint(100000, 999999))
        session["admin_otp"] = otp
        session["admin_otp_email"] = email
        return redirect(url_for("admin_verify"))

    return render_template("admin_register.html", msg=msg)


@app.route("/admin/verify", methods=["GET", "POST"])
def admin_verify():
    msg = None
    otp_demo = session.get("admin_otp")

    if request.method == "POST":
        if request.form.get("otp") == session.get("admin_otp"):
            verify_admin(session.get("admin_otp_email"))
            return redirect(url_for("admin_login"))
        msg = "Incorrect OTP"

    return render_template("admin_verify.html", msg=msg, otp_demo=otp_demo)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    # ✅ THIS ROUTE REMOVES YOUR 404
    msg = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        admin = get_admin_by_email(email)
        if admin and admin["password"] == password and admin["verified"] == 1:
            session.clear()
            session["role"] = "admin"
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            return redirect(url_for("admin_dashboard"))
        msg = "Invalid credentials / Not verified"

    return render_template("admin_login.html", msg=msg)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("landing"))


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    # Simple admin dashboard page (you can show dept links here)
    admin_name = session.get("admin_name")
    return render_template("admin_dashboard.html", admin_name=admin_name)


# Department dashboard (admin only)
@app.route("/dept/<dept>")
def dept_dashboard(dept):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    complaints = get_complaints_by_department(dept)
    dept_name = dept.replace("_", " ").title()

    return render_template(
        "department.html",
        complaints=complaints,
        dept_name=dept_name,
        dept=dept,
        admin_name=session.get("admin_name")
    )


# Update complaint status (admin only)
@app.route("/complaint/<int:complaint_id>/status", methods=["POST"])
def change_status(complaint_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    status = request.form.get("status")
    admin_proof = request.form.get("admin_proof")  # proof text (can be file later)
    next_url = request.form.get("next") or url_for("admin_dashboard")

    update_complaint_status(
        complaint_id=complaint_id,
        status=status,
        admin_proof=admin_proof,
        status_updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    return redirect(next_url)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)