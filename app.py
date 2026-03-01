from flask import Flask, request, render_template, redirect, url_for, session
import os
from datetime import datetime
import random
from werkzeug.utils import secure_filename

from db import (
    init_db, create_user, get_user_by_phone, verify_user,
    insert_complaint, get_complaints_by_department, get_complaints_by_user
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_to_any_random_string")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()


# ---------------- AI LOGIC (Rule-based for now) ----------------

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


# ---------------- AUTH ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        if not (name and address and phone and password):
            msg = "Please fill all fields."
            return render_template("register.html", msg=msg)

        create_user(name, address, phone, password)

        # Keeping verified=1 by default in DB for now
        return redirect(url_for("login"))

    return render_template("register.html", msg=msg)


@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

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

@app.route("/")
def root():
    return redirect(url_for("home"))


@app.route("/home", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    prediction = None
    priority = None
    dept_message = None

    if request.method == "POST":
        complaint = request.form.get("complaint", "").strip()
        photo1 = request.files.get("photo1")
        photo2 = request.files.get("photo2")

        if not complaint:
            dept_message = "Please type your complaint."
            return render_template(
                "index.html",
                prediction=prediction,
                priority=priority,
                dept_message=dept_message,
                username=session.get("name")
            )

        # Safe filenames
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        def save_file(file_obj, suffix):
            if not file_obj or file_obj.filename.strip() == "":
                return ""
            filename = secure_filename(file_obj.filename)
            final_name = f"{timestamp}_{suffix}_{filename}"
            full_path = os.path.join(app.config["UPLOAD_FOLDER"], final_name)
            file_obj.save(full_path)
            # store relative path for url_for('static', filename=...)
            return f"uploads/{final_name}"

        photo1_rel = save_file(photo1, "1")
        photo2_rel = save_file(photo2, "2")

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
            "photo1_path": photo1_rel,
            "photo2_path": photo2_rel,
            "assigned_department": assigned_department,
            "status": "Pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        dept_message = f"✅ Complaint submitted & forwarded to {assigned_department.upper()} department."

    return render_template(
        "index.html",
        prediction=prediction,
        priority=priority,
        dept_message=dept_message,
        username=session.get("name")
    )


# ---------------- MY COMPLAINTS (NEW) ----------------

@app.route("/my-complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect(url_for("login"))

    complaints = get_complaints_by_user(session["user_id"])

    # Quick counts for UI
    counts = {
        "total": len(complaints),
        "pending": sum(1 for c in complaints if c.get("status") == "Pending"),
        "progress": sum(1 for c in complaints if c.get("status") == "In Progress"),
        "resolved": sum(1 for c in complaints if c.get("status") == "Resolved"),
    }

    return render_template(
        "my_complaints.html",
        complaints=complaints,
        counts=counts,
        username=session.get("name")
    )


# ---------------- DEPT DASHBOARD (existing) ----------------

@app.route("/dept/<dept>")
def dept_dashboard(dept):
    complaints = get_complaints_by_department(dept)
    dept_name = dept.replace("_", " ").title()
    return render_template("department.html", complaints=complaints, dept_name=dept_name, dept=dept)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # debug should be False in production, but okay for now
    app.run(host="0.0.0.0", port=port, debug=True)