from flask import Flask, request, render_template, redirect, url_for, session
import os
import random
from datetime import datetime

from db import (
    init_db,
    create_user, get_user_by_phone,
    create_admin, get_admin_by_email, verify_admin,
    insert_complaint, get_complaints_by_department, get_all_complaints,
    update_complaint_status,
    get_complaints_by_user, get_complaint_by_id
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_to_any_random_string")

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()



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
    if any(k in text for k in ["street light", "streetlight", "lamp post", "lamp"]):
        return "Street Lights"
    if any(k in text for k in ["mosquito", "dengue", "fever", "health"]):
        return "Health & Hygiene"
    if any(k in text for k in ["dog", "stray", "cow", "animal"]):
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



@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        try:
            create_user(name, address, phone, password)
            return redirect(url_for("login"))
        except Exception:
            msg = "Phone already registered. Try logging in."

    return render_template("register.html", msg=msg)


@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        user = get_user_by_phone(phone)
        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["address"] = user["address"]
            session["phone"] = user["phone"]
            return redirect(url_for("home"))

        msg = "Invalid phone or password"

    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



def admin_logged_in():
    return session.get("admin_logged_in") is True


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    msg = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        try:
            create_admin(name, email, phone, password)
        except Exception:
            msg = "Admin email already exists. Please login."
            return render_template("admin_register.html", msg=msg)

        otp = str(random.randint(100000, 999999))
        session["admin_otp"] = otp
        session["admin_email_pending"] = email
        return redirect(url_for("admin_verify"))

    return render_template("admin_register.html", msg=msg)


@app.route("/admin/verify", methods=["GET", "POST"])
def admin_verify():
    msg = None
    otp_demo = session.get("admin_otp")

    if request.method == "POST":
        otp_in = request.form.get("otp", "").strip()
        if otp_in == session.get("admin_otp"):
            email = session.get("admin_email_pending")
            verify_admin(email)
            session.pop("admin_otp", None)
            session.pop("admin_email_pending", None)
            return redirect(url_for("admin_login"))
        msg = "Incorrect OTP. Try again."

    return render_template("admin_verify.html", msg=msg, otp_demo=otp_demo)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    msg = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        admin = get_admin_by_email(email)
        if admin and admin["password"] == password:
            if admin["verified"] != 1:
                msg = "Admin not verified. Please verify first."
                return render_template("admin_login.html", msg=msg)

            session["admin_logged_in"] = True
            session["admin_name"] = admin["name"]
            return redirect(url_for("admin_dashboard"))

        msg = "Invalid email or password"

    return render_template("admin_login.html", msg=msg)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_name", None)
    return redirect(url_for("admin_login"))



@app.route("/", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    prediction = None
    priority = None
    dept_message = None
    error = None

    if request.method == "POST":
        complaint = request.form.get("complaint", "").strip()
        photo1 = request.files.get("photo1")
        photo2 = request.files.get("photo2")

        if not complaint or not photo1 or not photo2 or photo1.filename == "" or photo2.filename == "":
            error = "Please enter complaint and upload BOTH images."
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
        error=error,
        username=session.get("name")
    )



@app.route("/my-complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect(url_for("login"))
    complaints = get_complaints_by_user(session["user_id"])
    return render_template("my_complaints.html", complaints=complaints, username=session.get("name"))


@app.route("/my-complaints/<int:complaint_id>")
def complaint_details(complaint_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    c = get_complaint_by_id(complaint_id)
    if not c or c["user_id"] != session["user_id"]:
        return redirect(url_for("my_complaints"))

    return render_template("complaint_details.html", c=c, username=session.get("name"))



@app.route("/admin")
def admin_dashboard():
    if not admin_logged_in():
        return redirect(url_for("admin_login"))
    complaints = get_all_complaints()
    return render_template("admin_dashboard.html", complaints=complaints, admin_name=session.get("admin_name"))


@app.route("/dept/<dept>")
def dept_dashboard(dept):
    if not admin_logged_in():
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
def change_status(complaint_id):
    if not admin_logged_in():
        return redirect(url_for("admin_login"))

    status = request.form.get("status", "")
    next_url = request.form.get("next") or url_for("admin_dashboard")

    if status not in ["Pending", "In Progress", "Resolved"]:
        return redirect(next_url)

    update_complaint_status(complaint_id, status)
    return redirect(next_url)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)