from flask import Flask, request, render_template, redirect, url_for, session
import os
from datetime import datetime
import random

from db import (
    init_db, create_user, get_user_by_phone, verify_user,
    insert_complaint, get_complaints_by_department
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
    if any(k in text for k in ["street light", "lamp post"]):
        return "Street Lights"
    if any(k in text for k in ["mosquito", "dengue", "fever"]):
        return "Health & Hygiene"
    if any(k in text for k in ["dog", "stray", "cow"]):
        return "Animal Control"

    return "General"


def get_priority(text: str) -> str:
    text = (text or "").lower()
    high_keywords = ["accident", "fire", "hospital", "danger"]
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


# ---------------- AUTH ----------------

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
        if user and user[4] == password and user[5] == 1:
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["address"] = user[2]
            session["phone"] = user[3]
            return redirect(url_for("home"))
        else:
            msg = "Invalid credentials"

    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- HOME ----------------

@app.route("/", methods=["GET", "POST"])
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


@app.route("/dept/<dept>")
def dept_dashboard(dept):
    complaints = get_complaints_by_department(dept)
    dept_name = dept.replace("_", " ").title()
    return render_template("department.html", complaints=complaints, dept_name=dept_name)


if __name__ == "__main__":
    app.run(debug=True)