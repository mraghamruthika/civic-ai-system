from flask import Flask, request, render_template, redirect, url_for, session
import os
from datetime import datetime
import random
from werkzeug.utils import secure_filename

from db import (
    init_db,
    create_user,
    get_user_by_phone,
    verify_user as verify_user_db,
    update_user_password,
    insert_complaint,
    get_complaints_by_user,
    get_complaints_for_admin,
    get_complaints_for_head,
    update_complaint_status,
    create_admin,
    get_admin_by_email,
    verify_admin as verify_admin_db,
    update_admin_password
)

app = Flask(__name__)
app.secret_key = "change_this_to_any_random_string"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()

TN = {
    "Tiruchirappalli": ["Tiruchirappalli", "Srirangam", "Lalgudi", "Manachanallur", "Thiruverumbur", "Musiri", "Thottiyam", "Thuraiyur"],
    "Chennai": ["Egmore", "Mylapore", "Guindy", "Perambur", "Ambattur", "Maduravoyal"],
    "Coimbatore": ["Coimbatore North", "Coimbatore South", "Pollachi", "Mettupalayam", "Sulur"],
    "Madurai": ["Madurai North", "Madurai South", "Melur", "Thirumangalam", "Usilampatti"],
    "Salem": ["Salem", "Attur", "Mettur", "Omalur", "Sankari"],
}

DISTRICTS = sorted(TN.keys())

DEPARTMENTS = [
    ("Road & Infrastructure", "roads"),
    ("Water Supply", "water"),
    ("Drainage & Sewage", "drainage"),
    ("Sanitation", "sanitation"),
    ("Electricity", "electricity"),
    ("Street Lights", "streetlights"),
    ("Health & Hygiene", "health"),
    ("Animal Control", "animals"),
    ("Emergency", "emergency"),
    ("General", "general"),
]


def get_category(text: str) -> str:
    t = (text or "").lower()

    if any(k in t for k in ["fire", "accident", "blast", "electrocution", "collapse", "gas leak"]):
        return "Emergency"
    if any(k in t for k in ["pothole", "road", "bridge", "footpath", "manhole"]):
        return "Road & Infrastructure"
    if any(k in t for k in ["water", "leak", "pipeline", "tap", "pressure"]):
        return "Water Supply"
    if any(k in t for k in ["drain", "sewage", "overflow", "stagnant"]):
        return "Drainage & Sewage"
    if any(k in t for k in ["garbage", "waste", "trash", "dustbin"]):
        return "Sanitation"
    if any(k in t for k in ["electricity", "power", "transformer", "wire", "voltage"]):
        return "Electricity"
    if any(k in t for k in ["street light", "lamp post", "streetlight", "flickering"]):
        return "Street Lights"
    if any(k in t for k in ["mosquito", "dengue", "fever", "toilet", "hygiene"]):
        return "Health & Hygiene"
    if any(k in t for k in ["dog", "stray", "cow", "animal", "bite"]):
        return "Animal Control"

    return "General"


def get_priority(text: str) -> str:
    t = (text or "").lower()
    high_keywords = [
        "accident", "fire", "hospital", "danger", "electrocution",
        "collapse", "gas leak", "open manhole"
    ]
    return "High" if any(k in t for k in high_keywords) else "Medium"


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
        "General": "general",
    }
    return mapping.get(category, "general")


@app.route("/")
def choose_login():
    return render_template("choose_login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        home_district = request.form.get("home_district", "Unknown")
        home_taluk = request.form.get("home_taluk", "Unknown")

        ok, err = create_user(name, address, phone, password, home_district, home_taluk)
        if not ok:
            msg = err or "Registration failed"
            return render_template("register.html", msg=msg, districts=DISTRICTS, tn=TN)

        otp = str(random.randint(100000, 999999))
        session["user_otp"] = otp
        session["user_otp_phone"] = phone

        return redirect(url_for("verify_user_otp_page"))

    return render_template("register.html", msg=msg, districts=DISTRICTS, tn=TN)


@app.route("/verify", methods=["GET", "POST"])
def verify_user_otp_page():
    msg = None
    otp_demo = session.get("user_otp")

    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()

        if entered_otp == session.get("user_otp"):
            phone = session.get("user_otp_phone")
            verify_user_db(phone)

            session.pop("user_otp", None)
            session.pop("user_otp_phone", None)

            return redirect(url_for("login"))
        else:
            msg = "Incorrect OTP"

    return render_template("verify.html", msg=msg, otp_demo=otp_demo, who="User")


@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        user = get_user_by_phone(phone)

        if user and user["password"] == password and user["verified"] == 1:
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_address"] = user["address"]
            session["user_phone"] = user["phone"]
            session["home_district"] = user.get("home_district", "Unknown")
            session["home_taluk"] = user.get("home_taluk", "Unknown")
            return redirect(url_for("home"))
        else:
            msg = "Invalid credentials / not verified"

    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("choose_login"))


@app.route("/user/forgot", methods=["GET", "POST"])
def user_forgot():
    msg = None

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        user = get_user_by_phone(phone)

        if not user:
            msg = "Phone not found"
            return render_template("forgot_user.html", msg=msg)

        otp = str(random.randint(100000, 999999))
        session["fp_user_otp"] = otp
        session["fp_user_phone"] = phone

        return redirect(url_for("user_reset"))

    return render_template("forgot_user.html", msg=msg)


@app.route("/user/reset", methods=["GET", "POST"])
def user_reset():
    msg = None
    otp_demo = session.get("fp_user_otp")

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        new_password = request.form.get("new_password", "").strip()

        if otp != session.get("fp_user_otp"):
            msg = "Incorrect OTP"
            return render_template("reset_user.html", msg=msg, otp_demo=otp_demo)

        phone = session.get("fp_user_phone")
        update_user_password(phone, new_password)

        session.pop("fp_user_otp", None)
        session.pop("fp_user_phone", None)

        return redirect(url_for("login"))

    return render_template("reset_user.html", msg=msg, otp_demo=otp_demo)


@app.route("/home", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    prediction = None
    priority = None
    dept_message = None

    if request.method == "POST":
        complaint = request.form.get("complaint", "").strip()
        incident_district = request.form.get("incident_district", "Unknown")
        incident_taluk = request.form.get("incident_taluk", "Unknown")
        incident_area = request.form.get("incident_area", "").strip()

        photo1 = request.files.get("photo1")
        photo2 = request.files.get("photo2")

        if not photo1 or not photo2 or not photo1.filename or not photo2.filename:
            dept_message = "Please upload both proof images."
            return render_template(
                "index.html",
                username=session.get("user_name"),
                prediction=None,
                priority=None,
                dept_message=dept_message,
                districts=DISTRICTS,
                tn=TN
            )

        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        filename1 = f"{ts}_1_{secure_filename(photo1.filename)}"
        filename2 = f"{ts}_2_{secure_filename(photo2.filename)}"

        photo1_path = os.path.join(app.config["UPLOAD_FOLDER"], filename1).replace("\\", "/")
        photo2_path = os.path.join(app.config["UPLOAD_FOLDER"], filename2).replace("\\", "/")

        photo1.save(photo1_path)
        photo2.save(photo2_path)

        prediction = get_category(complaint)
        priority = get_priority(complaint)
        assigned_department = get_department(prediction)

        insert_complaint({
            "user_id": session["user_id"],
            "name": session["user_name"],
            "address": session["user_address"],
            "phone": session["user_phone"],
            "complaint": complaint,
            "category": prediction,
            "priority": priority,
            "photo1_path": photo1_path,
            "photo2_path": photo2_path,
            "assigned_department": assigned_department,
            "status": "Pending",
            "admin_proof_path": "",
            "incident_district": incident_district,
            "incident_taluk": incident_taluk,
            "incident_area": incident_area,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        dept_message = f"Complaint routed to {assigned_department.upper()} | {incident_district} - {incident_taluk}"

    return render_template(
        "index.html",
        username=session.get("user_name"),
        prediction=prediction,
        priority=priority,
        dept_message=dept_message,
        districts=DISTRICTS,
        tn=TN
    )


@app.route("/my-complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect(url_for("login"))

    rows = get_complaints_by_user(session["user_id"])
    return render_template(
        "my_complaints.html",
        complaints=rows,
        username=session.get("user_name")
    )


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    msg = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "admin")
        department = request.form.get("department", "general")
        district = request.form.get("district", "Unknown")
        taluk = request.form.get("taluk", "all")

        if role == "head":
            department = "all"
            taluk = "all"

        ok, err = create_admin(name, email, password, role, department, district, taluk)
        if not ok:
            msg = err or "Admin registration failed"
            return render_template(
                "admin_register.html",
                msg=msg,
                departments=DEPARTMENTS,
                districts=DISTRICTS,
                tn=TN
            )

        otp = str(random.randint(100000, 999999))
        session["admin_otp"] = otp
        session["admin_otp_email"] = email

        return redirect(url_for("admin_verify_page"))

    return render_template(
        "admin_register.html",
        msg=msg,
        departments=DEPARTMENTS,
        districts=DISTRICTS,
        tn=TN
    )


@app.route("/admin/verify", methods=["GET", "POST"])
def admin_verify_page():
    msg = None
    otp_demo = session.get("admin_otp")

    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()

        if entered_otp == session.get("admin_otp"):
            email = session.get("admin_otp_email")
            verify_admin_db(email)

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
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        admin = get_admin_by_email(email)

        if admin and admin["password"] == password and admin["verified"] == 1:
            session.pop("user_id", None)
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            session["admin_email"] = admin["email"]
            session["admin_role"] = admin.get("role", "admin")
            session["admin_department"] = admin.get("department", "general")
            session["admin_district"] = admin.get("district", "Unknown")
            session["admin_taluk"] = admin.get("taluk", "all")

            if session["admin_role"] == "head":
                return redirect(url_for("head_dashboard"))
            return redirect(url_for("dept_dashboard"))
        else:
            msg = "Invalid credentials / not verified"

    return render_template("admin_login.html", msg=msg)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_email", None)
    session.pop("admin_role", None)
    session.pop("admin_department", None)
    session.pop("admin_district", None)
    session.pop("admin_taluk", None)
    return redirect(url_for("choose_login"))


@app.route("/admin/forgot", methods=["GET", "POST"])
def admin_forgot():
    msg = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        admin = get_admin_by_email(email)

        if not admin:
            msg = "Email not found"
            return render_template("forgot_admin.html", msg=msg)

        otp = str(random.randint(100000, 999999))
        session["fp_admin_otp"] = otp
        session["fp_admin_email"] = email

        return redirect(url_for("admin_reset"))

    return render_template("forgot_admin.html", msg=msg)


@app.route("/admin/reset", methods=["GET", "POST"])
def admin_reset():
    msg = None
    otp_demo = session.get("fp_admin_otp")

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        new_password = request.form.get("new_password", "").strip()

        if otp != session.get("fp_admin_otp"):
            msg = "Incorrect OTP"
            return render_template("reset_admin.html", msg=msg, otp_demo=otp_demo)

        email = session.get("fp_admin_email")
        update_admin_password(email, new_password)

        session.pop("fp_admin_otp", None)
        session.pop("fp_admin_email", None)

        return redirect(url_for("admin_login"))

    return render_template("reset_admin.html", msg=msg, otp_demo=otp_demo)



@app.route("/admin/department")
def dept_dashboard():
    if "admin_id" not in session or session.get("admin_role") != "admin":
        return redirect(url_for("admin_login"))

    dept = session.get("admin_department", "general")
    district = session.get("admin_district", "Unknown")
    taluk = session.get("admin_taluk", "Unknown")

    rows = get_complaints_for_admin(dept, district, taluk)

    return render_template(
        "department.html",
        complaints=rows,
        admin_name=session.get("admin_name"),
        dept=dept,
        district=district,
        taluk=taluk,
        err=request.args.get("err")
    )


@app.route("/head")
def head_dashboard():
    if "admin_id" not in session or session.get("admin_role") != "head":
        return redirect(url_for("admin_login"))

    district = session.get("admin_district", "Unknown")
    dept_filter = request.args.get("dept", "all")
    taluk_filter = request.args.get("taluk", "all")

    rows = get_complaints_for_head(
        district,
        department=None if dept_filter == "all" else dept_filter,
        taluk=None if taluk_filter == "all" else taluk_filter
    )

    taluks = TN.get(district, [])
    dept_keys = ["all"] + [key for _, key in DEPARTMENTS]

    return render_template(
        "head_dashboard.html",
        admin_name=session.get("admin_name"),
        district=district,
        taluks=taluks,
        departments=dept_keys,
        dept_filter=dept_filter,
        taluk_filter=taluk_filter,
        complaints=rows
    )


@app.route("/admin")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    if session.get("admin_role") == "head":
        return redirect(url_for("head_dashboard"))

    return redirect(url_for("dept_dashboard"))



@app.route("/complaint/<int:complaint_id>/status", methods=["POST"])
def complaint_status_update(complaint_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    status = request.form.get("status", "Pending").strip()
    next_url = request.form.get("next", "/admin/department")

    def add_err(url, code):
        return f"{url}{'&' if '?' in url else '?'}err={code}"

    proof = request.files.get("proof")

    if status in ["In Progress", "Resolved"]:
        if not proof or not proof.filename:
            return redirect(add_err(next_url, "proof_required"))

    proof_path = ""
    if proof and proof.filename:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        fname = f"{ts}_admin_{secure_filename(proof.filename)}"
        proof_path = os.path.join(app.config["UPLOAD_FOLDER"], fname).replace("\\", "/")
        proof.save(proof_path)

    update_complaint_status(complaint_id, status, proof_path)
    return redirect(next_url)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)