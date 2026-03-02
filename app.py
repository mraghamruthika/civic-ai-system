from flask import Flask, request, render_template, redirect, url_for, session
import os
from datetime import datetime
import random

from db import (
    init_db,
    # user
    create_user, get_user_by_phone, verify_user,
    # complaints
    insert_complaint, get_complaints_by_department, get_complaints_by_user,
    update_complaint_status,
    # admin
    create_admin, get_admin_by_email, verify_admin
)

app = Flask(__name__)
app.secret_key = "change_this_to_any_random_string"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()

# ---------------- AI LOGIC (simple) ----------------
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
    if any(k in text for k in ["street light", "lamp post"]):
        return "Street Lights"
    if any(k in text for k in ["mosquito", "dengue", "fever"]):
        return "Health & Hygiene"
    if any(k in text for k in ["dog", "stray", "cow"]):
        return "Animal Control"

    return "General"


def get_priority(text: str) -> str:
    text = (text or "").lower()
    high_keywords = ["accident", "fire", "hospital", "danger", "electrocution", "collapse"]
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


# ---------------- LANDING (Choose Login) ----------------
@app.route("/")
def choose_login():
    return render_template("choose_login.html")


# ---------------- USER AUTH ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        phone = request.form.get("phone")
        password = request.form.get("password")

        # Create user (verified=0 by default)
        ok, err = create_user(name, address, phone, password)
        if not ok:
            msg = err or "Registration failed"
            return render_template("register.html", msg=msg)

        # OTP demo (stored in session)
        otp = str(random.randint(100000, 999999))
        session["user_otp"] = otp
        session["user_otp_phone"] = phone

        return redirect(url_for("verify_user_otp"))

    return render_template("register.html", msg=msg)


@app.route("/verify", methods=["GET", "POST"])
def verify_user_otp():
    msg = None
    otp_demo = session.get("user_otp")  # demo only

    if request.method == "POST":
        if request.form.get("otp") == session.get("user_otp"):
            verify_user(session.get("user_otp_phone"))
            session.pop("user_otp", None)
            session.pop("user_otp_phone", None)
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
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["address"] = user["address"]
            session["phone"] = user["phone"]
            return redirect(url_for("home"))
        else:
            msg = "Invalid credentials / not verified"

    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("choose_login"))


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

        if not photo1 or not photo2:
            dept_message = "Please upload both proof images."
            return render_template(
                "index.html",
                prediction=None,
                priority=None,
                dept_message=dept_message,
                username=session.get("name")
            )

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
            "photo1_path": photo1_path,
            "photo2_path": photo2_path,
            "assigned_department": assigned_department,
            "status": "Pending",
            "admin_proof_path": "",
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


@app.route("/my-complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect(url_for("login"))

    rows = get_complaints_by_user(session["user_id"])
    return render_template("my_complaints.html", complaints=rows, username=session.get("name"))


# ---------------- ADMIN AUTH ----------------
@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        ok, err = create_admin(name, email, password)
        if not ok:
            msg = err or "Admin registration failed"
            return render_template("admin_register.html", msg=msg)

        otp = str(random.randint(100000, 999999))
        session["admin_otp"] = otp
        session["admin_otp_email"] = email
        return redirect(url_for("admin_verify"))

    return render_template("admin_register.html", msg=msg)


@app.route("/admin/verify", methods=["GET", "POST"])
def admin_verify():
    msg = None
    otp_demo = session.get("admin_otp")  # demo only

    if request.method == "POST":
        if request.form.get("otp") == session.get("admin_otp"):
            verify_admin(session.get("admin_otp_email"))
            session.pop("admin_otp", None)
            session.pop("admin_otp_email", None)
            return redirect(url_for("admin_login"))
        else:
            msg = "Incorrect OTP"

    return render_template("admin_verify.html", msg=msg, otp_demo=otp_demo)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    msg = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        admin = get_admin_by_email(email)
        if admin and admin["password"] == password and admin["verified"] == 1:
            # store admin session
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            session["admin_email"] = admin["email"]
            return redirect(url_for("admin_dashboard"))
        else:
            msg = "Invalid admin credentials / not verified"

    return render_template("admin_login.html", msg=msg)


@app.route("/admin/logout")
def admin_logout():
    # remove only admin keys
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_email", None)
    return redirect(url_for("choose_login"))


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html", admin_name=session.get("admin_name"))


# ---------------- DEPARTMENT DASHBOARD ----------------
@app.route("/dept/<dept>")
def dept_dashboard(dept):
    if "admin_id" not in session:
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


@app.route("/complaint/<int:complaint_id>/status", methods=["POST"])
def complaint_status_update(complaint_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    status = request.form.get("status", "Pending")
    next_url = request.form.get("next", "/admin")

    # Optional proof file upload for status update
    proof = request.files.get("proof")
    proof_path = ""

    if proof and proof.filename:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        fname = f"{timestamp}_admin_{proof.filename}"
        proof_path = os.path.join(app.config["UPLOAD_FOLDER"], fname).replace("\\", "/")
        proof.save(proof_path)

    update_complaint_status(complaint_id, status, proof_path)
    return redirect(next_url)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)