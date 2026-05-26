print("🔥 APP IS RUNNING FROM THIS FILE")
import calendar
from datetime import datetime
import secrets
import os
import json
import requests
from flask import Flask, request, session, redirect, url_for
from functools import wraps
from werkzeug.utils import secure_filename

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
from datetime import timedelta

app.permanent_session_lifetime = timedelta(minutes=30)

# 🔥 REQUIRED FOR LOGIN SESSIONS
app.secret_key = secrets.token_hex(32)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.after_request
def security_headers(response):

    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response




def get_nav(role):

    if role == "admin":
        links = """
        <a href="/admin">Dashboard</a>
        <a href="/report">Reports</a>
        <a href="/logout">Logout</a>
        """

    elif role == "student":
        links = """
        <a href="/student">Dashboard</a>
        <a href="/student/payment/{sid}">Upload Payment</a>
        <a href="/logout">Logout</a>
        """

    elif role == "staff":
        links = """
        <a href="/accounts">Accounts</a>
        <a href="/logout">Logout</a>
        """

    else:
        links = "<a href='/login'>Login</a>"

    return f"""

</style>

<button class="menu-btn" onclick="openNav()">☰</button>

<div id="sidebar" class="sidebar">
    <span class="close-btn" onclick="closeNav()">×</span>
    {links}
</div>

<script>
function openNav() {{
    document.getElementById("sidebar").style.width = "250px";
}}
function closeNav() {{
    document.getElementById("sidebar").style.width = "0";
}}
</script>
"""


def get_nav(role, sid=""):

    return f"""
<style>
body {{
    margin:0;
    font-family:Arial,sans-serif;
    background:linear-gradient(135deg,#f8fbff,#eef7ff,#f7fcff);
    overflow-x:hidden;
}}
	
.main-container {{
    padding:30px;
}}

.panel {{

    background:white;

    border:1px solid #e2e8f0;

    border-radius:12px;

    box-shadow:0 2px 8px rgba(0,0,0,0.05);


    
}}

.quick-card {{
    background:white;
    border-radius:24px;
    padding:35px 25px;
    text-align:center;
    transition:0.3s;
    box-shadow:0 4px 15px rgba(0,0,0,0.05);
}}

.quick-card:hover {{
    transform:translateY(-6px);
}}

.quick-card h3 {{
    margin-top:18px;
    font-size:28px;
}}

.quick-card p {{
    color:#64748b;
    line-height:1.7;
    font-size:17px;
}}

/* MENU LINKS */

#sideMenu a {{
    text-decoration:none;
    color:#0f172a;
    font-size:30px;
    font-weight:600;
}}

#sideMenu a:hover {{
    color:#2563eb;
}}
</style>

<!-- HAMBURGER BUTTON -->
<div style="
    position:fixed;
    top:18px;
    left:18px;
    z-index:1000;
">
    <span onclick="openMenu()" style="
        font-size:34px;
        cursor:pointer;
        background:rgba(255,255,255,0.7);
        backdrop-filter:blur(10px);
        padding:10px 16px;
        border-radius:14px;
        box-shadow:0 4px 15px rgba(0,0,0,0.1);
    ">
        ☰
    </span>
</div>

<!-- OVERLAY -->
<div id="overlay" onclick="closeMenu()" style="
    display:none;
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:rgba(0,0,0,0.25);
    z-index:998;
"></div>

<!-- SIDE MENU -->
<div id="sideMenu" style="
    position:fixed;
    top:0;
    left:0;
    width:260px;
    font-size:38px;
    height:55%;
    background:rgba(255,255,255,0.75);
    backdrop-filter:blur(10px);
    -webkit-backdrop-filter:blur(20px);
    box-shadow:0 8px 32px rgba(0,0,0,0.08);
    padding:30px 25px;
    transform:translateX(-100%);
    transition:0.3s ease;
    z-index:999;
">

    <h2 style="
        color:#2563eb;
        margin-bottom:30px;
        font-size:38px;
    ">
        Menu
    </h2>

    <a href="/student">🏠 Home</a><br><br>

    <a href="/student/profile">👤 Profile</a><br><br>

    <a href="/student/accommodation">🏠 Accommodation</a><br><br>

    <a href="/student/accounts">💰 Accounts</a><br><br>

    <a href="/student/payment/{sid}">📄 Payment Proof</a><br><br>

    <a href="/student/clearance">📋 Clearance Status</a><br><br>

    <hr style="margin:25px 0;">
    
    <a href="/reset" style="
    display:block;
    padding:18px 30px;
    text-decoration:none;
    color:#0f172a;
    font-size:23px;
    font-weight:600;
">
    🔐 Reset Password
</a>

    <a href="/logout" style="color:#dc2626;">
        Logout
    </a>

</div>

<script>
function openMenu() {{
    document.getElementById("sideMenu").style.transform = "translateX(0)";
    document.getElementById("overlay").style.display = "block";
}}

function closeMenu() {{
    document.getElementById("sideMenu").style.transform = "translateX(-100%)";
    document.getElementById("overlay").style.display = "none";
}}
</script>
"""





# ---------------- DEBUG ----------------

print("🚨 RUNNING FROM:", os.getcwd())
print("📂 FILES:", os.listdir())
print("APP STARTING...")

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    role = session.get("role")

    if role == "student":
        return redirect("/student")

    elif role == "staff":
        return redirect("/staff")

    elif role == "admin":
        return redirect("/admin")

    return redirect("/login")

# ---------------- LOAD DATA ----------------

def load_students():
    try:
        with open(os.path.join(BASE_DIR, "students.json"), "r") as f:
            return json.load(f)
    except:
        return {}


def save_students(data):
    with open(os.path.join(BASE_DIR, "students.json"), "w") as f:
        json.dump(data, f, indent=4)


def load_users():
    try:
        with open(os.path.join(BASE_DIR, "users.json"), "r") as f:
            return json.load(f)
    except:
        return {}


def save_users(data):
    with open(os.path.join(BASE_DIR, "users.json"), "w") as f:
        json.dump(data, f, indent=4)

# ---------- HOSTEL CLEARANCE CALCULATOR ----------

def calculate_hostel_status(student):

    items = student.get("hostel_items", {})

    mattress = items.get("mattress", "Not Returned")
    key = items.get("key", "Not Returned")

    issues = []

    if mattress != "Returned":
        issues.append("Mattress not returned")

    if key != "Returned":
        issues.append("Key not returned")

    if issues:
        return "Pending", issues

    return "Cleared", []

# ---------------- ENSURE STUDENT STRUCTURE ----------------

def ensure_departments(student):

    if "departments" not in student:
        student["departments"] = {}

    default = {
        "communication": {"status": "Pending", "reason": ""},
        "mathematics": {"status": "Pending", "reason": ""},
        "hr": {"status": "Pending", "reason": ""},
        "training": {"status": "Pending", "reason": ""},
        "ame": {"status": "Pending", "reason": ""},
        "accounts": {"status": "Pending", "reason": ""}
    }

    for key in default:
        if key not in student["departments"]:
            student["departments"][key] = default[key]

    # AME TOOLS (from your original version)
    if "ame_tools" not in student:
        student["ame_tools"] = []


def ensure_sports(student):

    if "sports" not in student:
        student["sports"] = {}

    default = {
        "football": [],
        "basketball": [],
        "volleyball": [],
        "netball": [],
        "chess": []
    }

    for key in default:
        if key not in student["sports"]:
            student["sports"][key] = []


def ensure_accounts(student):

    if "accounts" not in student:
        student["accounts"] = {
            "total_fee": 7860,
            "paid": 0,
            "minimum_required": 4000,
            "status": "Pending",
            "reason": ""
        }


print("🔥 REACHED ROUTE SECTION")  
#---------LOGIN ROUTE--------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        users = load_users()

        if username in users and check_password_hash(
    users[username]["password"],
    password
):

            session["user"] = username
            session.permanent = True
            session["role"] = users[username]["role"]

            # optional department (for staff)
            session["department"] = users[username].get("department")

            # 🔥 REDIRECT BASED ON ROLE
            if session["role"] == "admin":
                return redirect("/admin")
            elif session["role"] == "student":
                session["accepted_terms"] = False
                return redirect("/terms")
            elif session["role"] == "staff":
                dept = session.get("department")
                if dept:
                    return redirect(f"/{dept}")
                return redirect("/login")

        return """
        <h3 style='color:red;text-align:center;'>Invalid login</h3>
        <a href="/login" style="display:block;text-align:center;">Try again</a>
        """

    # -------- UI --------
    return """
    <div style="
        min-height:100vh;
        display:flex;
        align-items:center;
        justify-content:center;
        background:linear-gradient(135deg,#2563eb,#16a34a);
        font-family:Arial;
    ">

        <div style="
            style="
    background: rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    border: 1px solid rgba(255,255,255,0.3);
"
            padding:40px;
            border-radius:16px;
            width:320px;
            box-shadow:0 10px 25px rgba(0,0,0,0.2);
            text-align:center;
        ">

            <h1 style="
                font-size:42px;
                margin-bottom:25px;
                color:#1e293b;
            ">
                Student Digital<br>Clearance System
            </h1>

            <form method="POST">

                <input name="username" placeholder="Username" required
                    style="
                        width:80%;
                        padding:12px;
                        font-size: 25px;
                        margin-bottom:15px;
                        border-radius:10px;
                        border:1px solid #ccc;
                        outline:none;
                    ">

                <input name="password" type="password" placeholder="Password" required
                    style="
                        width:80%;
                        padding:12px;
                        font-size: 25px;
                        margin-bottom:20px;
                        border-radius:10px;
                        border:1px solid #ccc;
                        outline:none;
                    ">

				<!-- REMEMBER + FORGOT -->
<div style="
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:18px;
    font-size:24px;
">

    <!-- REMEMBER -->
    <label style="
        display:flex;
        align-items:center;
        gap:8px;
        color:#475569;
        cursor:pointer;
    ">

        <input type="checkbox" name="remember">
        Remember me

    </label>

    <!-- FORGOT -->
    <a href="/forgot" style="
        text-decoration:none;
        color:#2563eb;
        font-weight:600;
    ">
        Forgot Password?
    </a>

</div>

                <button style="
                    width:50%;
                    padding:12px;
                    background:#2563eb;
                    color:white;
                    font-size: 25px;
                    border:none;
                    border-radius:10px;
                    font-weight:bold;
                    cursor:pointer;
                ">
                    Login
                </button>

            </form>

        </div>

    </div>
    """
# ---------------- FORGOT PASSWORD ----------------
@app.route("/forgot", methods=["GET", "POST"])
def forgot():

    users = load_users()

    if request.method == "POST":

        username = request.form.get("username", "").strip()

        if username in users:

            return f"""

            <div style="
                min-height:100vh;
                display:flex;
                justify-content:center;
                align-items:center;
                background:linear-gradient(135deg,#dbeafe,#f0f9ff);
                font-family:Arial;
            ">

                <div style="
                    background:white;
                    padding:40px;
                    border-radius:24px;
                    width:340px;
                    box-shadow:0 10px 30px rgba(0,0,0,0.08);
                ">

                    <h2 style="
                        text-align:center;
                        color:#2563eb;
                        margin-bottom:25px;
                    ">
                        Reset Password
                    </h2>

                    <form method="POST" action="/reset">

                        <input type="hidden"
                               name="username"
                               value="{username}">

                        <input
                            type="password"
                            name="new_password"
                            placeholder="New Password"
                            required

                            style="
                                width:100%;
                                padding:14px;
                                margin-bottom:20px;
                                border-radius:12px;
                                border:1px solid #cbd5e1;
                            "
                        >

                        <button style="
                            width:100%;
                            padding:14px;
                            border:none;
                            border-radius:14px;
                            background:#2563eb;
                            color:white;
                            font-size:16px;
                            font-weight:bold;
                            cursor:pointer;
                        ">
                            Reset Password
                        </button>

                    </form>

                </div>

            </div>

            """

        return """

        <h3 style="color:red;text-align:center;">
            User not found
        </h3>

        """

    return """

    <div style="
        min-height:100vh;
        display:flex;
        justify-content:center;
        align-items:center;
        background:linear-gradient(135deg,#dbeafe,#f0f9ff);
        font-family:Arial;
    ">

        <div style="
            background:white;
            padding:40px;
            border-radius:24px;
            width:340px;
            box-shadow:0 10px 30px rgba(0,0,0,0.08);
        ">

            <h2 style="
                text-align:center;
                color:#2563eb;
                margin-bottom:25px;
            ">
                Forgot Password
            </h2>

            <form method="POST">

                <input
                    name="username"
                    placeholder="Enter Username"
                    required

                    style="
                        width:100%;
                        padding:14px;
                        margin-bottom:20px;
                        border-radius:12px;
                        border:1px solid #cbd5e1;
                    "
                >

                <button style="
                    width:100%;
                    padding:14px;
                    border:none;
                    border-radius:14px;
                    background:#2563eb;
                    color:white;
                    font-size:16px;
                    font-weight:bold;
                    cursor:pointer;
                ">
                    Continue
                </button>

            </form>

        </div>

    </div>

    """
    
# ---------------- RESET PASSWORD ----------------
@app.route("/reset", methods=["GET", "POST"])
def reset():

    if "user" not in session:
        return redirect("/login")

    users = load_users()

    username = session["user"]

    if request.method == "POST":

        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # CHECK CURRENT PASSWORD
        if not check_password_hash(
        	users[username]["password"],
        	current_password

):

            return """
            <h3 style='color:red;text-align:center;'>
                Current password is incorrect
            </h3>
            """

        # CHECK MATCH
        if new_password != confirm_password:

            return """
            <h3 style='color:red;text-align:center;'>
                New passwords do not match
            </h3>
            """

        # SAVE NEW PASSWORD
        users[username]["password"] = generate_password_hash(new_password)

        save_users(users)

        return """
        <h3 style='color:green;text-align:center;'>
            Password updated successfully
        </h3>

        <div style="text-align:center;margin-top:20px;">
            <a href="/dashboard">Return to Dashboard</a>
        </div>
        """

    return """

    <div style="
        min-height:100vh;
        display:flex;
        justify-content:center;
        align-items:center;
        background:linear-gradient(135deg,#dbeafe,#f0f9ff);
        font-family:Arial;
    ">

        <div style="
            width:360px;
            background:white;
            padding:40px;
            border-radius:24px;
            box-shadow:0 10px 30px rgba(0,0,0,0.08);
        ">

            <h2 style="
                text-align:center;
                color:#2563eb;
                margin-bottom:25px;
            ">
                Reset Password
            </h2>

            <form method="POST">

                <div style="
    position:relative;
    margin-bottom:22px;
">

    <input
        type="password"
        id="current_password"
        name="current_password"
        placeholder="Current Password"
        required

        style="
            width:100%;
            padding:14px;
            padding-right:55px;
            border-radius:12px;
            border:1px solid #cbd5e1;
            box-sizing:border-box;
        "
    >

    <span

    onclick="
        let p = document.getElementById('current_password');

        if (p.type === 'password') {

            p.type = 'text';

            this.innerHTML = '🙈';

        } else {

            p.type = 'password';

            this.innerHTML = '👁️';

        }
    "

    style="
        position:absolute;
        right:18px;
        top:50%;
        transform:translateY(-50%);
        cursor:pointer;
        font-size:20px;
        user-select:none;
    ">

        👁️

    </span>

</div>

                <div style="
    position:relative;
    margin-bottom:22px;
">

    <input
        type="password"
        id="new_password"
        name="new_password"
        placeholder="New Password"
        required

        style="
            width:100%;
            padding:14px;
            padding-right:55px;
            border-radius:12px;
            border:1px solid #cbd5e1;
            box-sizing:border-box;
        "
    >

    <span

    onclick="
        let p = document.getElementById('new_password');

        if (p.type === 'password') {

            p.type = 'text';

            this.innerHTML = '🙈';

        } else {

            p.type = 'password';

            this.innerHTML = '👁️';

        }
    "

    style="
        position:absolute;
        right:18px;
        top:50%;
        transform:translateY(-50%);
        cursor:pointer;
        font-size:20px;
        user-select:none;
    ">

        👁️

    </span>

</div>

                <div style="
    position:relative;
    margin-bottom:22px;
">

    <input
        type="password"
        id="confirm_password"
        name="confirm_password"
        placeholder="Confirm New Password"
        required

        style="
            width:100%;
            padding:14px;
            padding-right:55px;
            border-radius:12px;
            border:1px solid #cbd5e1;
            box-sizing:border-box;
        "
    >

    <span

    onclick="
        let p = document.getElementById('confirm_password');

        if (p.type === 'password') {

            p.type = 'text';

            this.innerHTML = '🙈';

        } else {

            p.type = 'password';

            this.innerHTML = '👁️';

        }
    "

    style="
        position:absolute;
        right:18px;
        top:50%;
        transform:translateY(-50%);
        cursor:pointer;
        font-size:20px;
        user-select:none;
    ">

        👁️

    </span>

</div>

                <button style="
                    width:100%;
                    padding:14px;
                    border:none;
                    border-radius:14px;
                    background:#2563eb;
                    color:white;
                    font-size:16px;
                    font-weight:bold;
                    cursor:pointer;
                ">
                    Update Password
                </button>

            </form>

        </div>

    </div>

    """
    
            
def dept_nav(title="Department"):

    return f"""

    <!-- SIDEBAR -->
    <div id="sidebar" style="
        position:fixed;
        top:0;
        left:-260px;
        width:240px;
        height:15%;
        background:rgba(255,255,255,0.75);
    backdrop-filter:blur(5px);
    -webkit-backdrop-filter:blur(2px);
    
        box-shadow:0 0 25px rgba(0,0,0,0.12);
        transition:0.3s;
        z-index:9999;
        padding-top:80px;
    ">

        <a href="/dashboard".6
        
          style="
            display:block;
            padding:18px 30px;
            text-decoration:none;
            color:#0f172a;
            font-size:18px;
            font-weight:600;
        ">
            Dashboard
        </a>
        
        <a href="/reset" style="
    display:block;
    padding:18px 30px;
    text-decoration:none;
    color:#0f172a;
    font-size:18px;
    font-weight:600;
">
    🔐Reset Password
</a>

        <a href="/logout" style="
            display:block;
            padding:18px 30px;
            text-decoration:none;
            color:#dc2626;
            font-size:18px;
            font-weight:700;
        ">
            Logout
        </a>

    </div>

    <!-- TOP BAR -->
    <div style="
        display:flex;
        align-items:center;
        gap:18px;
        padding:20px 25px;
        background:white;
        box-shadow:0 4px 12px rgba(0,0,0,0.05);
        position:sticky;
        top:0;
        z-index:100;
    ">

        <!-- MENU BUTTON -->
        <button onclick="toggleSidebar()" style="
            background:white;
            border:none;
            width:52px;
            height:52px;
            border-radius:14px;
            font-size:28px;
            cursor:pointer;
            box-shadow:0 4px 18px rgba(0,0,0,0.08);
        ">
            ☰
        </button>

        <!-- TITLE -->
        <h1 style="
            margin:0;
            font-size:34px;
            color:#0f172a;
            font-weight:800;
        ">
            {title}
        </h1>

    </div>

    <script>
    function toggleSidebar() {{

        const sidebar = document.getElementById("sidebar");

        if(sidebar.style.left === "0px") {{
            sidebar.style.left = "-260px";
        }} else {{
            sidebar.style.left = "0px";
        }}
    }}
    </script>

    """

# ---------------- DASHBOARD REDIRECT ----------------
@app.route("/dashboard")
def dashboard():

    if "role" not in session:
        return redirect("/login")

    role = session.get("role")

    # ADMIN
    if role == "admin":
        return redirect("/admin")

    # STUDENT
    elif role == "student":
        session["accepted_terms"] = False
        return redirect("/terms")

    # STAFF / DEPARTMENTS
    elif role == "staff":

        dept = session.get("department")

        if dept:
            return redirect(f"/{dept}")

    return redirect("/login")

# --------------- NAV ----------------

NAV = ""

# ---------------- ADMIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    if session.get("role") != "admin":
        return redirect("/login")

    students = load_students()

    # 🔥 ENSURE FUNDING EXISTS
    for sid in students:
        if "funding" not in students[sid] or not students[sid]["funding"]:
            students[sid]["funding"] = "Self Sponsored"

    users = load_users()

    # ---------------- HANDLE ACTIONS ----------------
    if request.method == "POST":

        action = request.form.get("action")

        # -------- ADD STUDENT --------
        if action == "add_student":

            sid = request.form.get("student_id", "").strip()

            if not sid.isdigit() or len(sid) != 8:
                return NAV + "<h3 style='color:red;'>Student ID must be exactly 8 digits</h3><a href='/admin'>Back</a>"

            if sid in students:
                return NAV + "<h3 style='color:red;'>Student ID already exists</h3><a href='/admin'>Back</a>"

            # SAFE conversions
            try:
                year = int(request.form.get("year", 1))
                term = int(request.form.get("term", 1))
            except:
                year, term = 1, 1

            funding = request.form.get("funding") or "Self Sponsored"

            # -------- CREATE STUDENT --------
            students[sid] = {
                "name": request.form.get("name", ""),
                "program": request.form.get("program", ""),
                "year": year,
                "term": term,
                "funding": funding,

                "profile_pic": "",
                "accommodation": "Not Set",  # ✅ FIXED
                "hostel": "N/A",
                "room": "N/A",

                "hostel_items": {
                    "mattress": "Not Assigned",
                    "key": "Not Assigned"
                },

                "library": {"books": []},

                "sports": {
                    "football": [],
                    "basketball": [],
                    "volleyball": [],
                    "netball": [],
                    "chess": []
                },

                "departments": {
                    "communication": {"status": "Pending", "reason": ""},
                    "mathematics": {"status": "Pending", "reason": ""},
                    "hr": {"status": "Pending", "reason": ""},
                    "training": {"status": "Pending", "reason": ""},
                    "ame": {"status": "Pending", "reason": ""},
                    "accounts": {"status": "Pending", "reason": ""}
                },

                # 🔥 ACCOUNTS STRUCTURE (REPLACES payment_status)
                "accounts": {
                    "total_fee": 7860,
                    "paid": 0,
                    "minimum_required": 4000,
                    "status": "Pending",
                    "reason": ""
                }
            }

            users[sid] = {
                "password": generate_password_hash("1234"),
                "role": "student"
            }

        # -------- DELETE --------
        elif action == "delete_selected":
            selected = request.form.getlist("selected")

            for sid in selected:
                students.pop(sid, None)
                users.pop(sid, None)

        save_students(students)
        save_users(users)

        return redirect("/admin")

    # -------- SEARCH + FILTER --------
    search = request.args.get("search", "").strip().lower()
    funding_filter = request.args.get("funding", "all")

    display_students = {}

    for sid, s in students.items():
        name = s.get("name", "").lower()
        funding = s.get("funding", "Self Sponsored")

        matches_search = (search in sid.lower() or search in name or search == "")
        matches_funding = (funding_filter == "all" or funding.lower() == funding_filter.lower())

        if matches_search and matches_funding:
            display_students[sid] = s

    # ---------------- DISPLAY ----------------
    total_students = len(display_students)
    fully_cleared = 0
    pending_students = 0
    print("STUDENTS LOADED:", students)

    output = dept_nav("️ Admin Dashboard") + """

<p><b>Total Students:</b> {total_students}</p>

<form method="GET" style="margin-bottom:10px;">
    <input name="search" placeholder="Search ID or Name">

    <select name="funding">
        <option value="all">All Funding Types</option>
        <option value="Self Sponsored">Self Sponsored</option>
        <option value="CDF">CDF</option>
        <option value="Other">Other</option>
    </select>

    <button>Search</button>
</form>
<hr>
"""

    output += """
<form method="POST">
<input type="hidden" name="action" value="delete_selected">

<table border="1" width="100%" cellpadding="8" style="border-collapse:collapse;">
<tr style="background:#ddd;">
    <th><input type="checkbox" onclick="toggleAll(this)"></th>
    <th>Funding</th>
    <th>ID</th>
    <th>Name</th>
    <th>Progress</th>
    <th>Accounts</th>
</tr>
"""

    for sid, s in display_students.items():

        departments = s.get("departments", {})
        acc = s.get("accounts", {})

        # 🔥 ACCOUNT STATUS (REAL DATA)
        total_fee = acc.get("total_fee", 7860)
        paid = acc.get("paid", 0)
        minimum = acc.get("minimum_required", 4000)

        outstanding = total_fee - paid

        if outstanding <= 0:
            acc_status = "Cleared"
        elif paid >= minimum:
            acc_status = "Cleared"
        else:
            acc_status = "Pending"

        # 🔥 CLEARANCE COUNT
        statuses = [
            "Cleared" if not [b for b in s.get("library", {}).get("books", []) if not b.get("returned", True)] else "Pending",
            "Cleared" if s.get("hostel_items", {}).get("mattress") in ["Returned", "NIL"] else "Pending",
            "Cleared" if s.get("hostel_items", {}).get("key") in ["Returned", "NIL"] else "Pending",
            "Cleared" if s.get("accommodation") == "Day Scholar" or (
                s.get("hostel_items", {}).get("key") == "Returned" and
                s.get("hostel_items", {}).get("mattress") == "Returned"
            ) else "Pending",
            "Cleared" if sum(len(v) for v in s.get("sports", {}).values()) == 0 else "Pending",

            departments.get("communication", {}).get("status", "Pending"),
            departments.get("mathematics", {}).get("status", "Pending"),
            departments.get("hr", {}).get("status", "Pending"),
            departments.get("training", {}).get("status", "Pending"),
            departments.get("ame", {}).get("status", "Pending"),
            acc_status,
        ]

        cleared = sum(1 for st in statuses if st == "Cleared")
        total = len(statuses)

        if cleared == total:
            fully_cleared += 1
        else:
            pending_students += 1
			
        output += f"""
<tr>
    <td><input type="checkbox" name="selected" value="{sid}"></td>
    <td>{s.get("funding","")}</td>
    <td><a href="/admin/edit/{sid}">{sid}</a></td>
    <td>{s.get('name','')}</td>
    <td>{cleared}/{total}</td>
    <td>{acc_status}</td>
</tr>
"""

    output += """
</table><br>
<button type="submit">Delete Selected</button>
</form>
"""

    output += f"""
<hr>
<h3>System Summary</h3>
<p>Fully Cleared: {fully_cleared}</p>
<p>Pending: {pending_students}</p>
"""

    output += """
<hr>
<h3>Add Student</h3>

<form method="POST">
    <input type="hidden" name="action" value="add_student">

    ID:<br><input name="student_id" required><br><br>
    Name:<br><input name="name" required><br><br>
    Program:<br><input name="program" required><br><br>
    Year:<br><input name="year" required><br><br>
    Term:<br><input name="term" required><br><br>

    Funding:<br>
    <select name="funding" required>
        <option value="Self Sponsored">Self Sponsored</option>
        <option value="CDF">CDF</option>
        <option value="Other">Other</option>
    </select>

    <button>Add Student</button>
</form>

<script>
function toggleAll(source) {
    let checkboxes = document.getElementsByName('selected');
    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = source.checked;
    }
}
</script>
"""

    return output


@app.route("/admin/edit/<sid>", methods=["GET", "POST"])
def edit_student(sid):

    if session.get("role") != "admin":
        return redirect("/login")

    students = load_students()

    if sid not in students:
        return "<h3>Student not found</h3><a href='/admin'>Back</a>"

    s = students[sid]

    if request.method == "POST":
        s["name"] = request.form.get("name")
        s["program"] = request.form.get("program")
        s["year"] = int(request.form.get("year"))
        s["term"] = int(request.form.get("term"))
        s["funding"] = request.form.get("funding")

        save_students(students)

        return redirect("/admin")

    return NAV + f"""
<div style="padding:20px;font-family:Arial;">
    <h2>Edit Student ({sid})</h2>

    <form method="POST">
        Name:<br>
        <input name="name" value="{s.get('name','')}" required><br><br>

        Program:<br>
        <input name="program" value="{s.get('program','')}" required><br><br>

        Year:<br>
        <input name="year" value="{s.get('year','')}" required><br><br>

        Term:<br>
        <input name="term" value="{s.get('term','')}" required><br><br>

        Funding:<br>
        <select name="funding">
            <option {"selected" if s.get("funding")=="Self Sponsored" else ""}>Self Sponsored</option>
            <option {"selected" if s.get("funding")=="CDF" else ""}>CDF</option>
            <option {"selected" if s.get("funding")=="Other" else ""}>Other</option>
        </select><br><br>

        <button style="padding:10px 20px;background:#2563eb;color:white;border:none;border-radius:6px;">
            Save Changes
        </button>
    </form>

    <br>
    <a href="/admin">⬅ Back</a>
</div>
"""      
                                       
# -------- STAFF MAIN ROUTE --------
@app.route("/staff")
def staff():

    if session.get("role") != "staff":
        return redirect("/login")

    dept = session.get("department", "").lower()

    if dept == "library":
        return redirect("/library")

    elif dept == "sports":
        return redirect("/sports")

    elif dept == "accounts":
        return redirect("/accounts")

    elif dept == "stores":
    	return redirect("/stores")

    elif dept == "tso":
        return redirect("/tso")
        
    elif dept == "hostel":
    	return redirect("/hostel")

    elif dept == "communication":
    	return redirect("/communication")

    elif dept == "mathematics":
        return redirect("/mathematics")

    elif dept == "hr":
        return redirect("/hr")

    elif dept == "training":
        return redirect("/training")

    elif dept == "ame":
        return redirect("/ame")

    return "<h2>No department assigned</h2>"


# -------- LIBRARY --------
@app.route("/library", methods=["GET", "POST"])
def staff_library():

    if session.get("role") != "staff" or session.get("department") != "library":
        return redirect("/login")

    students = load_students()
    for sid in students:
    	ensure_departments(students[sid])

    # -------- HANDLE ACTIONS --------
    if request.method == "POST":
        sid = request.form.get("sid")
        action = request.form.get("action")

        if sid in students:

            # 🔥 ENSURE STRUCTURE EXISTS
            if "library" not in students[sid]:
                students[sid]["library"] = {"books": []}

            books = students[sid]["library"].get("books", [])

            # -------- BORROW BOOK --------
            if action == "borrow":
                book_name = request.form.get("book_name", "").strip()

                active_books = [b for b in books if not b["returned"]]

                if len(active_books) >= 2:
                    print("❌ Cannot borrow more than 2 books")
                elif book_name:
                    books.append({
                        "name": book_name,
                        "returned": False
                    })

            # -------- RETURN BOOK --------
            elif action.startswith("return_"):
                index = int(action.split("_")[1])

                if 0 <= index < len(books):
                    books[index]["returned"] = True

            students[sid]["library"]["books"] = books

        # 🔥 SAVE
        save_students(students)

    # -------- SEARCH FILTER --------
    search = request.args.get("search", "").strip()

    display_students = students

    if search:
        display_students = {
            sid: s for sid, s in students.items()
            if search in sid
        }

    # -------- DISPLAY --------
    output = dept_nav(" Library Department") + """
    

    <form method="GET" style="margin-bottom:15px;">
        <input name="search" placeholder="Search Student ID or Name" style="padding:5px;">
        <button type="submit">Search</button>
    </form>
    <hr>
    """

    for sid, s in display_students.items():

        books = s.get("library", {}).get("books", [])

        active_books = [b for b in books if not b["returned"]]

        # -------- STATUS --------
        status = "Cleared" if len(active_books) == 0 else "Pending"

        # -------- BORROW LIMIT MESSAGE --------
        if len(active_books) >= 2:
            borrow_note = "❌ Max books reached"
        else:
            borrow_note = "✅ Can borrow"

        output += f"""
        <div style="border:1px solid #ccc;padding:10px;margin:10px;">
            <b>{s['name']} ({sid})</b><br>
            Program: {s.get('program','')} |
            Year: {s.get('year','')} |
            Term: {s.get('term','')}<br><br>

            <b>Books:</b><br>
        """

        if not books:
            output += "No books borrowed<br>"
        else:
            for i, b in enumerate(books):
                mark = "✔" if b["returned"] else "✖"

                output += f"""
                {mark} {b['name']}
                """

                if not b["returned"]:
                    output += f"""
                    <form method="POST" style="display:inline;">
                        <input type="hidden" name="sid" value="{sid}">
                        <button name="action" value="return_{i}">Return</button>
                    </form>
                    """

                output += "<br>"

        output += f"""
            <br>
            <b>Status:</b> {status}<br>
            <b>{borrow_note}</b><br><br>

            <!-- BORROW BOOK -->
            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">
                <input name="book_name" placeholder="Enter book name" required>
                <button name="action" value="borrow">Borrow Book</button>
            </form>
        </div>
        """

    return output


# -------- SPORTS --------
@app.route("/sports", methods=["GET", "POST"])
def sports():

    if session.get("role") != "staff" or session.get("department") != "sports":
        return redirect("/login")

    students = load_students()

    # -------- HANDLE ACTION --------
    if request.method == "POST":
        sid = request.form.get("sid")
        discipline = request.form.get("discipline")
        item = request.form.get("item", "").strip()
        action = request.form.get("action")

        if sid in students and discipline:

            # Ensure sports structure exists
            if "sports" not in students[sid]:
                students[sid]["sports"] = {
                    "football": [],
                    "basketball": [],
                    "volleyball": [],
                    "netball": [],
                    "chess": []
                }

            # Ensure discipline exists
            if discipline not in students[sid]["sports"]:
                students[sid]["sports"][discipline] = []

            # -------- ADD ITEM --------
            if action == "add" and item:
                students[sid]["sports"][discipline].append(item)

            # -------- REMOVE ITEM --------
            elif action == "remove":
                new_list = []
                for i in students[sid]["sports"][discipline]:
                    if isinstance(i, str) and i != item:
                        new_list.append(i)
                    elif isinstance(i, dict) and i.get("name") != item:
                        new_list.append(i)
                students[sid]["sports"][discipline] = new_list

        save_students(students)
        return redirect("/sports")

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    display_students = students if not search else {
        sid: s for sid, s in students.items()
        if search in sid.lower() or search in s.get("name", "").lower()
    }

    # -------- HELPER TO DISPLAY ITEMS SAFELY --------
    def render_items(items):
        clean = []
        for i in items:
            if isinstance(i, str):
                clean.append(i)
            elif isinstance(i, dict):
                clean.append(i.get("name", ""))
        return ", ".join(clean) if clean else "None"

    # -------- UI --------
    output = dept_nav("Sports Department") + """
    

    <form method="GET">
        <input name="search" placeholder="Search ID or Name">
        <button>Search</button>
    </form>

    <table border="1" width="100%" cellpadding="8" style="border-collapse:collapse;margin-top:10px;">
        <tr style="background:#1f2937;color:white;">
            <th>Student</th>
            <th>Football</th>
            <th>Basketball</th>
            <th>Volleyball</th>
            <th>Netball</th>
            <th>Chess</th>
        </tr>
    """

    for sid, s in display_students.items():

        sports_data = s.get("sports", {
            "football": [],
            "basketball": [],
            "volleyball": [],
            "netball": [],
            "chess": []
        })

        def cell(discipline):
            return f"""
            {render_items(sports_data.get(discipline, []))}
            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">
                <input type="hidden" name="discipline" value="{discipline}">
                <input name="item" placeholder="Item">
                <button name="action" value="add">+</button>
                <button name="action" value="remove">-</button>
            </form>
            """

        output += f"""
        <tr>
            <td><b>{s.get('name','')}<br>{sid}</b></td>
            <td>{cell("football")}</td>
            <td>{cell("basketball")}</td>
            <td>{cell("volleyball")}</td>
            <td>{cell("netball")}</td>
            <td>{cell("chess")}</td>
        </tr>
        """

    output += "</table>"

    return output

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)
    
# -------- ACCOUNTS --------
@app.route("/accounts", methods=["GET", "POST"])
def accounts():

    if session.get("role") != "staff" or session.get("department") != "accounts":
        return redirect("/login")

    students = load_students()

    # 🔥 ENSURE STRUCTURE EXISTS FOR ALL STUDENTS
    for sid in students:

        if "accounts" not in students[sid]:

            students[sid]["accounts"] = {

                "total_fee": 7860,
                "paid": 0,
                "minimum_required": 4000,
                "status": "Pending",
                "reason": "",
                "payments": [],
                "history": []

            }

        # 🔥 ENSURE PAYMENTS LIST EXISTS
        if "payments" not in students[sid]["accounts"]:

            students[sid]["accounts"]["payments"] = []

        # 🔥 ENSURE HISTORY EXISTS
        if "history" not in students[sid]["accounts"]:

            students[sid]["accounts"]["history"] = []

    # -------- HANDLE ACTION --------
    if request.method == "POST":

        sid = request.form.get("sid")

        index = request.form.get("index")

        action = request.form.get("action")

        # -------- APPROVE / REJECT PAYMENT --------
        if sid and index is not None and action in ["approve", "reject"]:

            index = int(index)

            payment = students[sid]["accounts"]["payments"][index]

            if action == "approve":

                payment["status"] = "Approved"

                students[sid]["accounts"]["paid"] += payment["amount"]

                # 🔥 SAVE TO BILLING HISTORY
                students[sid]["accounts"]["history"].append({

                    "amount": payment["amount"],

                    "reason": "Online Payment",

                    "status": "Approved"

                })

            elif action == "reject":

                payment["status"] = "Rejected"

                payment["reason"] = request.form.get("reason", "")

            save_students(students)

            return redirect("/accounts")

        # -------- NORMAL UPDATE --------
        if sid in students:

            acc = students[sid]["accounts"]

            # 🔹 UPDATE PAID
            paid_input = request.form.get("paid", "").strip()

            if paid_input:

                try:

                    amount = float(paid_input)

                    acc["paid"] = amount

                    # 🔥 SAVE MANUAL PAYMENT HISTORY
                    acc["history"].append({

                        "amount": amount,

                        "reason": "Manual Accounts Update",

                        "status": "Recorded"

                    })

                except:
                    pass

            # 🔹 UPDATE TOTAL
            total_input = request.form.get("total_fee", "").strip()

            if total_input:

                try:
                    acc["total_fee"] = float(total_input)

                except:
                    pass

            # 🔹 UPDATE MINIMUM
            min_input = request.form.get("minimum_required", "").strip()

            if min_input:

                try:
                    acc["minimum_required"] = float(min_input)

                except:
                    pass

            # 🔹 MANUAL CLEAR
            if action == "clear":

                acc["status"] = "Cleared"

                acc["reason"] = "Cleared by Accounts Office"

            else:

                # 🔥 AUTO LOGIC
                total = acc.get("total_fee", 7860)

                paid = acc.get("paid", 0)

                minimum = acc.get("minimum_required", 4000)

                outstanding = total - paid

                if outstanding <= 0:

                    acc["status"] = "Cleared"

                    acc["reason"] = "Fees fully paid"

                elif paid >= minimum:

                    acc["status"] = "Cleared"

                    acc["reason"] = "Meets minimum payment requirement"

                else:

                    acc["status"] = "Pending"

                    acc["reason"] = f"Outstanding balance: K{outstanding}"

        save_students(students)

        return redirect("/accounts")

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    display_students = students if not search else {

        sid: s for sid, s in students.items()

        if search in sid.lower()
        or search in s.get("name", "").lower()

    }

    # -------- OUTPUT --------
    output = dept_nav("Accounts Department") + """

    

    <form method="GET">

        <input
            name="search"
            placeholder="Search ID or Name"
        >

        <button>Search</button>

    </form>

    <hr>
    """

    # -------- SHOW PENDING PAYMENTS --------
    for sid, s in students.items():

        payments = s.get("accounts", {}).get("payments", [])

        for i, p in enumerate(payments):

            if p.get("status") == "Pending":

                output += f"""

                <div style="
                    border:1px solid #ccc;
                    padding:15px;
                    margin-bottom:10px;
                ">

                    <p>
                        <b>{s.get("name")} ({sid})</b>
                    </p>

                    <p>
                        Amount: K{p["amount"]}
                    </p>

                    <img
                        src="/uploads/{p['file']}"
                        width="200"
                    >

                    <br><br>

                    <form method="POST">

                        <input
                            type="hidden"
                            name="sid"
                            value="{sid}"
                        >

                        <input
                            type="hidden"
                            name="index"
                            value="{i}"
                        >

                        <button
                            name="action"
                            value="approve"

                            style="
                                background:green;
                                color:white;
                            "
                        >
                            Approve
                        </button>

                        <br><br>

                        Reject Reason:<br>

                        <input name="reason">

                        <br><br>

                        <button
                            name="action"
                            value="reject"

                            style="
                                background:red;
                                color:white;
                            "
                        >
                            Reject
                        </button>

                    </form>

                </div>
                """

    # -------- STUDENT ACCOUNTS --------
    for sid, s in display_students.items():

        acc = s.get("accounts", {})

        total = acc.get("total_fee", 7860)

        paid = acc.get("paid", 0)

        minimum = acc.get("minimum_required", 4000)

        outstanding = total - paid

        # 🔥 RECALCULATE STATUS
        if outstanding <= 0:

            status = "Cleared"

            reason = "Fees fully paid"

        elif paid >= minimum:

            status = "Cleared"

            reason = "Meets minimum payment requirement"

        else:

            status = "Pending"

            reason = f"Outstanding balance: K{outstanding}"

        output += f"""

        <div style="
            border:1px solid #ccc;
            padding:15px;
            margin:15px;
            border-radius:10px;
            background:#fff;
        ">

            <h3>
                {s.get('name','')} ({sid})
            </h3>

            <table border="1"
            width="100%"
            cellpadding="8"

            style="
                border-collapse:collapse;
            ">

                <tr>
                    <th>Total Fees</th>
                    <td>K{total}</td>
                </tr>

                <tr>
                    <th>Amount Paid</th>
                    <td>K{paid}</td>
                </tr>

                <tr>
                    <th>Outstanding Balance</th>
                    <td>K{outstanding}</td>
                </tr>

                <tr>
                    <th>Minimum Required Payment</th>
                    <td>K{minimum}</td>
                </tr>

            </table>

            <br>

            <b>Status:</b> {status}<br>

            <b>Note:</b> {reason}

            <br><br>

            <h4>📄 Payment History</h4>

            <table border="1"
            width="100%"
            cellpadding="8"

            style="
                border-collapse:collapse;
                margin-bottom:20px;
            ">

                <tr style="background:#eee;">

                    <th>Amount</th>

                    <th>Status</th>

                    <th>Reason</th>

                </tr>

                {

                    "".join(

                        f'''

                        <tr>

                            <td>K{p.get("amount",0)}</td>

                            <td>{p.get("status","")}</td>

                            <td>{p.get("reason","")}</td>

                        </tr>

                        '''

                        for p in acc.get("history", [])

                    )

                }

            </table>

            <form method="POST">

                <input
                    type="hidden"
                    name="sid"
                    value="{sid}"
                >

                <input
                    name="paid"
                    placeholder="Update Amount Paid"
                >

                <br><br>

                <input
                    name="total_fee"
                    placeholder="Total Fees"
                >

                <br><br>

                <input
                    name="minimum_required"
                    placeholder="Minimum Required"
                >

                <br><br>

                <button>
                    Update
                </button>

                <button
                    name="action"
                    value="clear"
                >
                    Clear
                </button>

            </form>

        </div>
        """

    return output



# -------- STORES --------
@app.route("/stores", methods=["GET", "POST"])
def stores():

    if session.get("role") != "staff" or session.get("department") != "stores":
        return redirect("/login")

    students = load_students()
    for sid in students:
    	ensure_departments(students[sid])

    if request.method == "POST":
        sid = request.form.get("sid")
        action = request.form.get("action")

        if sid in students:
            items = students[sid].get("hostel_items", {})

            if items.get("mattress") != "NIL":
                if action == "assign":
                    items["mattress"] = "Assigned"
                elif action == "returned":
                    items["mattress"] = "Returned"

        save_students(students)

    # -------- SEARCH --------
    search = request.args.get("search", "").strip()
    display_students = students

    if search:
        display_students = {sid: s for sid, s in students.items() if search in sid}

    output = dept_nav("Stores Department") + """
    

    <form method="GET">
        <input name="search" placeholder="Search ID or Name">
        <button>Search</button>
    </form><hr>
    """

    for sid, s in display_students.items():
        mattress = s.get("hostel_items", {}).get("mattress", "Not Assigned")

        output += f"""
        <div>
            <b>{s['name']} ({sid})</b><br>
            Mattress: {mattress}<br>

            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">
                <button name="action" value="assign">Assign</button>
                <button name="action" value="returned">Returned</button>
            </form>
        </div><hr>
        """

    return output

# -------- TSO --------
@app.route("/tso", methods=["GET", "POST"])
def tso():

    if session.get("role") != "staff" or session.get("department") != "tso":
        return redirect("/login")

    students = load_students()

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    display_students = students

    if search:
        display_students = {
            sid: s for sid, s in students.items()
            if search in sid.lower()
            or search in s.get("name", "").lower()
        }

    # -------- DISPLAY --------
    output = dept_nav("Technical Services Office") + """

    <div style="padding:30px;">

        

        <br>

        <form method="GET">

            <input
                name="search"
                placeholder="Search Student ID or Name"
                style="
                    padding:12px;
                    width:320px;
                    border-radius:10px;
                    border:1px solid #ccc;
                "
            >

            <button style="
                padding:12px 22px;
                border:none;
                background:#2563eb;
                color:white;
                border-radius:10px;
                cursor:pointer;
            ">
                Search
            </button>

        </form>

        <br><br>

        <table border="1" cellpadding="10" style="
            border-collapse:collapse;
            width:100%;
            font-size:18px;
        ">

            <tr style="background:#e2e8f0;">
                <th>ID</th>
                <th>Name</th>
                <th>Type</th>
                <th>Hostel</th>
                <th>Room</th>
                <th>Physical Clearance</th>
            </tr>
    """

    for sid, s in display_students.items():

        acc = s.get("accommodation", "Not Set")
        hostel_name = s.get("hostel", "NIL")
        room = s.get("room", "NIL")

        output += f"""
        <tr>

            <td>{sid}</td>
            <td>{s.get('name','')}</td>
            <td>{acc}</td>
            <td>{hostel_name}</td>
            <td>{room}</td>

            <td style="font-weight:bold;">
                Physical Clearance Required
            </td>

        </tr>
        """

    output += """
        </table>

    </div>
    """

    return output


# -------- HOSTEL --------
@app.route("/hostel", methods=["GET", "POST"])
def hostel():

    # 🔒 Access control
    if session.get("role") != "staff" or session.get("department") != "hostel":
        return redirect("/login")

    students = load_students()

    # -------- HANDLE ACTIONS --------
    if request.method == "POST":

        sid = request.form.get("sid")
        action = request.form.get("action")

        if sid in students:

            # -------- DAY SCHOLAR --------
            if action == "day":

                students[sid]["accommodation"] = "Day Scholar"
                students[sid]["hostel"] = "NIL"
                students[sid]["room"] = "NIL"

            # -------- BOARDER --------
            elif action == "boarder":

                room = request.form.get("room", "").strip()
                hostel_name = request.form.get("hostel_name", "").strip()

                if room and hostel_name:

                    students[sid]["accommodation"] = "Boarding"
                    students[sid]["hostel"] = hostel_name
                    students[sid]["room"] = room

        save_students(students)

        return redirect("/hostel")

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    display_students = students

    if search:
        display_students = {
            sid: s for sid, s in students.items()
            if search in sid.lower()
            or search in s.get("name", "").lower()
        }

    # -------- DISPLAY --------
    output = dept_nav("Hostel Department") + """

    <div style="padding:30px;">

        

        <br>

        <form method="GET">

            <input
                name="search"
                placeholder="Search Student ID or Name"
                style="
                    padding:12px;
                    width:320px;
                    border-radius:10px;
                    border:1px solid #ccc;
                "
            >

            <button style="
                padding:12px 22px;
                border:none;
                background:#2563eb;
                color:white;
                border-radius:10px;
                cursor:pointer;
            ">
                Search
            </button>

        </form>

        <br><br>

        <table border="1" cellpadding="10" style="
            border-collapse:collapse;
            width:100%;
            font-size:18px;
        ">

            <tr style="background:#e2e8f0;">
                <th>ID</th>
                <th>Name</th>
                <th>Type</th>
                <th>Hostel</th>
                <th>Room</th>
                <th>Physical Clearance</th>
                <th>Action</th>
            </tr>
    """

    for sid, s in display_students.items():

        acc = s.get("accommodation", "Not Set")
        hostel_name = s.get("hostel", "NIL")
        room = s.get("room", "NIL")

        output += f"""
        <tr>

            <td>{sid}</td>
            <td>{s.get('name','')}</td>
            <td>{acc}</td>
            <td>{hostel_name}</td>
            <td>{room}</td>

            <td style="font-weight:bold;">
                Physical Clearance Required
            </td>

            <td>
                <form method="POST" style="display:inline;">

                    <input type="hidden" name="sid" value="{sid}">

                    <button name="action" value="day">
                        Day
                    </button>

                    <br><br>

                    <input name="hostel_name" placeholder="Hostel" required><br>
                    <input name="room" placeholder="Room" required><br>

                    <button name="action" value="boarder">
                        Boarder
                    </button>

                </form>
            </td>

        </tr>
        """

    output += """
        </table>

    </div>
    """

    return output
    
# -------- COMMUNICATION SKILLS --------
@app.route("/communication", methods=["GET", "POST"])
def communication():

    if session.get("role") != "staff" or session.get("department") != "communication":
        return redirect("/login")

    students = load_students()
    for sid in students:
    	ensure_departments(students[sid])

    if request.method == "POST":
        sid = request.form.get("sid")
        status = request.form.get("status")
        reason = request.form.get("reason")

        if sid in students:

            if "departments" not in students[sid]:
                students[sid]["departments"] = {}

            students[sid]["departments"]["communication"] = {
                "status": status,
                "reason": reason
            }

        save_students(students)

    search = request.args.get("search", "").strip()
    display_students = students if not search else {
        sid: s for sid, s in students.items() if search in sid
    }

    output = dept_nav(" Communication Skills  Department") + """
    

    <form method="GET">
        <input name="search" placeholder="Search Student ID or Name">
        <button>Search</button>
    </form><hr>
    """

    for sid, s in display_students.items():
        dept = s.get("departments", {}).get("communication", {})
        status = dept.get("status", "Pending")
        reason = dept.get("reason", "")

        output += f"""
        <div style="border:1px solid #ccc;padding:10px;margin:10px;">
            <b>{s['name']} ({sid})</b><br>
            Status: {status}<br>
            Reason: {reason}<br><br>

            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">
                <select name="status">
                    <option value="Cleared">Cleared</option>
                    <option value="Pending">Pending</option>
                </select>
                <input name="reason" placeholder="Reason">
                <button>Update</button>
            </form>
        </div>
        """

    return output


# -------- MATHEMATICS --------
@app.route("/mathematics", methods=["GET", "POST"])
def mathematics():

    if session.get("role") != "staff" or session.get("department") != "mathematics":
        return redirect("/login")

    students = load_students()

    # 🔥 Ensure departments exist
    for sid in students:
        ensure_departments(students[sid])

    # -------- POST --------
    if request.method == "POST":
        sid = request.form.get("sid")
        status = request.form.get("status")
        reason = request.form.get("reason")

        if sid in students:
            students[sid]["departments"]["mathematics"] = {
                "status": status,
                "reason": reason
            }

            save_students(students)

        return redirect("/mathematics")

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    display_students = students if not search else {
        sid: s for sid, s in students.items()
        if search in sid.lower() or search in s.get("name", "").lower()
    }

    # -------- OUTPUT --------
    output = dept_nav(" Mathematics Department") + """
    

    <form method="GET" style="margin-bottom:10px;">
        <input name="search" placeholder="Search Student ID or Name" style="padding:5px;">
        <button>Search</button>
    </form>
    <hr>
    """

    for sid, s in display_students.items():

        dept = s.get("departments", {}).get("mathematics", {})
        status = dept.get("status", "Pending")
        reason = dept.get("reason", "")

        output += f"""
        <div style="border:1px solid #ccc;padding:10px;margin:10px;">
            <b>{s.get('name','')} ({sid})</b><br>
            Status: {status}<br>
            Reason: {reason}<br><br>

            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">
                
                <select name="status">
                    <option value="Cleared" {"selected" if status=="Cleared" else ""}>Cleared</option>
                    <option value="Pending" {"selected" if status=="Pending" else ""}>Pending</option>
                </select>

                <input name="reason" value="{reason}" placeholder="Reason">
                <button>Update</button>
            </form>
        </div>
        """

    return output


# -------- HUMAN RESOURCE --------
@app.route("/hr", methods=["GET", "POST"])
def hr():

    if session.get("role") != "staff" or session.get("department") != "hr":
        return redirect("/login")

    students = load_students()

    # 🔥 Ensure departments exist
    for sid in students:
        ensure_departments(students[sid])

    # -------- POST --------
    if request.method == "POST":
        sid = request.form.get("sid")
        status = request.form.get("status")
        reason = request.form.get("reason")

        if sid in students:
            students[sid]["departments"]["hr"] = {
                "status": status,
                "reason": reason
            }

            save_students(students)

        return redirect("/hr")

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    display_students = students if not search else {
        sid: s for sid, s in students.items()
        if search in sid.lower() or search in s.get("name", "").lower()
    }

    # -------- OUTPUT --------
    output = dept_nav("Human Resource Department") + """
    

    <form method="GET" style="margin-bottom:10px;">
        <input name="search" placeholder="Search Student ID or Name" style="padding:5px;">
        <button>Search</button>
    </form>
    <hr>
    """

    for sid, s in display_students.items():

        dept = s.get("departments", {}).get("hr", {})
        status = dept.get("status", "Pending")
        reason = dept.get("reason", "")

        output += f"""
        <div style="border:1px solid #ccc;padding:10px;margin:10px;">
            <b>{s.get('name','')} ({sid})</b><br>
            Status: {status}<br>
            Reason: {reason}<br><br>

            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">

                <select name="status">
                    <option value="Cleared" {"selected" if status=="Cleared" else ""}>Cleared</option>
                    <option value="Pending" {"selected" if status=="Pending" else ""}>Pending</option>
                </select>

                <input name="reason" value="{reason}" placeholder="Reason">
                <button>Update</button>
            </form>
        </div>
        """

    return output


# -------- HEAD OF TRAINING --------
@app.route("/training", methods=["GET", "POST"])
def training():

    if session.get("role") != "staff" or session.get("department") != "training":
        return redirect("/login")

    students = load_students()

    for sid in students:
        ensure_departments(students[sid])

    # -------- HANDLE ACTION --------
    if request.method == "POST":
        sid = request.form.get("sid")
        status = request.form.get("status")
        reason = request.form.get("reason")

        if sid in students:

            students[sid]["departments"]["training"] = {
                "status": status,
                "reason": reason
            }

        save_students(students)
        return redirect("/training")

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    if search:
        display_students = {
            sid: s for sid, s in students.items()
            if search in sid.lower() or search in s.get("name", "").lower()
        }
    else:
        display_students = students

    # -------- UI --------
    output = dept_nav("Head Of Training Section ") + """
    
    <form method="GET">
        <input name="search" placeholder="Search ID or Name">
        <button>Search</button>
    </form>
    <hr>
    """

    for sid, s in display_students.items():

        dept = s.get("departments", {}).get("training", {})
        status = dept.get("status", "Pending")
        reason = dept.get("reason", "")

        output += f"""
        <div style="border:1px solid #ccc;padding:12px;margin:10px;border-radius:8px;">
            <b>{s.get('name','Unknown')} ({sid})</b><br><br>

            <b>Status:</b> {status}<br>
            <b>Reason:</b> {reason}<br><br>

            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">

                <select name="status">
                    <option value="Cleared">Cleared</option>
                    <option value="Pending">Pending</option>
                </select><br><br>

                <input name="reason" placeholder="Reason (if pending)"><br><br>

                <button>Update</button>
            </form>
        </div>
        """

    return output


# -------- AME STORES --------
@app.route("/ame", methods=["GET", "POST"])
def ame():

    if session.get("role") != "staff" or session.get("department") != "ame":
        return redirect("/login")

    students = load_students()

    # -------- ENSURE STRUCTURE --------
    for sid in students:
        if "ame_tools" not in students[sid]:
            students[sid]["ame_tools"] = []

    # -------- HANDLE ACTION --------
    if request.method == "POST":
        sid = request.form.get("sid")
        action = request.form.get("action")

        if sid in students:

            tools = students[sid]["ame_tools"]

            # -------- ADD TOOL --------
            if action == "add":
                tool_name = request.form.get("tool", "").strip()

                if tool_name:
                    tools.append({
                        "name": tool_name,
                        "returned": False
                    })

            # -------- RETURN TOOL --------
            elif action.startswith("return_"):
                index = int(action.split("_")[1])

                if 0 <= index < len(tools):
                    tools[index]["returned"] = True

            students[sid]["ame_tools"] = tools

        save_students(students)
        return redirect("/ame")

    # -------- SEARCH --------
    search = request.args.get("search", "").strip().lower()

    if search:
        display_students = {
            sid: s for sid, s in students.items()
            if search in sid.lower() or search in s.get("name", "").lower()
        }
    else:
        display_students = students

    # -------- UI --------
    output = dept_nav("AME Stores") + """
    

    <form method="GET">
        <input name="search" placeholder="Search ID or Name">
        <button>Search</button>
    </form>
    <hr>
    """

    for sid, s in display_students.items():

        tools = s.get("ame_tools", [])

        active_tools = [t for t in tools if not t["returned"]]

        # -------- STATUS --------
        status = "Cleared" if len(active_tools) == 0 else "Pending"

        output += f"""
        <div style="border:1px solid #ccc;padding:12px;margin:10px;border-radius:8px;">
            <b>{s.get('name','Unknown')} ({sid})</b><br><br>

            <b>Tools:</b><br>
        """

        if not tools:
            output += "No tools issued<br>"
        else:
            for i, t in enumerate(tools):
                mark = "✔" if t["returned"] else "✖"

                output += f"{mark} {t['name']} "

                if not t["returned"]:
                    output += f"""
                    <form method="POST" style="display:inline;">
                        <input type="hidden" name="sid" value="{sid}">
                        <button name="action" value="return_{i}">Return</button>
                    </form>
                    """

                output += "<br>"

        output += f"""
            <br>
            <b>Status:</b> {status}<br><br>

            <!-- ADD TOOL -->
            <form method="POST">
                <input type="hidden" name="sid" value="{sid}">
                <input name="tool" placeholder="Enter tool name" required>
                <button name="action" value="add">Add Tool</button>
            </form>
        </div>
        """

    return output
    
    print("ROUTES:", app.url_map)
    # ---------------- STAFF FORM (GET) ----------------
    return """
    <h2>Staff Clearance Panel</h2>

    <form method="POST">

        Student ID:<br>
        <input name="student_id" required><br><br>

        Department:<br>
        <select name="department">
            <option value="library">Library</option>
            <option value="sports">Sports</option>
            <option value="accounts">Accounts</option>
            <option value="stores">Stores</option>
            <option value="tso">Technical Services Office</option>
        </select><br><br>

        Issue (Sports only):<br>
        <input name="issue"><br><br>

        Balance (Accounts only):<br>
        <input name="balance" type="number"><br><br>

        Returned items? (yes/no):<br>
        <input name="returned"><br><br>

        Key returned? (yes/no):<br>
        <input name="key"><br><br>

        <button type="submit">Update Clearance</button>

    </form>
    """




@app.route("/terms", methods=["GET", "POST"])
def terms():

    if session.get("role") != "student":
        return redirect("/login")

    # ✅ when student accepts
    if request.method == "POST":

        session["accepted_terms"] = True

        return redirect("/student")

    return f"""

    <div style="
        max-width:1100px;
        margin:auto;
        margin-top:40px;
        background:white;
        padding:40px;
        border-radius:18px;
        box-shadow:0 6px 20px rgba(0,0,0,0.08);
        font-family:Arial;
    ">

        <h1 style="
            color:#2563eb;
            font-size:48px;
            margin-bottom:10px;
        ">
            Student Clearance Terms & Conditions
        </h1>

        <p style="
            color:#555;
            font-size:22px;
            margin-bottom:35px;
        ">
            Please read and accept the following conditions before proceeding.
        </p>

        <div style="
            font-size:24px;
            line-height:1.9;
            color:#111827;
        ">

            <p>
                1. Every student is required to complete clearance with all assigned departments before final approval is granted.
            </p>

            <p>
                2. Clearance statuses are subject to verification by the responsible department.
            </p>

            <p>
                3. Students are responsible for returning all institutional property issued to them during the academic period.
            </p>

            <p>
                4. Failure to return items issued by Stores, Hostel, or Technical Services Office (TSO) may result in penalties or replacement charges.
            </p>

            <p>
                5. Current penalty fee:
            </p>

            <div style="
                margin-left:40px;
                margin-top:15px;
                margin-bottom:25px;
                padding:20px;
                background:#f1f5f9;
                border-radius:12px;
                font-weight:bold;
                color:#dc2626;
            ">
                Penalty Amount: K{200}
            </div>

            <p>
                6. The institution reserves the right to withhold final clearance where verification is incomplete or disputed.
            </p>

            <p>
                7. Submission of false information or fraudulent documents may lead to disciplinary action.
            </p>

            <p>
                8. Clearance records may be audited and verified by administration at any time.
            </p>

        </div>

        <div style="
            text-align:center;
            margin-top:45px;
        ">

            <form method="POST">

                <button style="
                    background:linear-gradient(135deg,#2563eb,#16a34a);
                    color:white;
                    border:none;
                    padding:18px 40px;
                    border-radius:14px;
                    font-size:22px;
                    font-weight:bold;
                    cursor:pointer;
                ">
                    ✅ I Agree & Continue
                </button>

            </form>

        </div>

    </div>
    """

# -------- STUDENT PAGE --------
from flask import render_template
@app.route("/student")
def student():

    if session.get("role") != "student":
        session["accepted_terms"] = False
        return redirect("/terms")

    sid = session.get("user")

    students = load_students()

    if sid not in students:
        return "<h3>Student not found</h3>"

    s = students[sid]

    name = s.get("name", "Student")

    profile_pic = s.get("profile_pic") or "https://via.placeholder.com/120"
    
    nav = get_nav("student", sid)

    
    return nav + f"""

<div class="main-container" style="
    display:flex;
    justify-content:flex-end;
    align-items:flex-start;
    padding:40px;
">

    <!-- RIGHT SIDE -->
    <div style="
        position:relative;
        display:flex;
        justify-content:flex-end;
        width:100%;
    ">

        <!-- WELCOME CARD -->
        <div class="glass" style="
            display:flex;
            align-items:center;
            gap:14px;
            padding:12px 20px;
            border-radius:22px;
            background:rgba(255,255,255,0.75);
            box-shadow:0 10px 30px rgba(0,0,0,0.08);
        ">

            <img src="{profile_pic}" style="
                width:58px;
                height:58px;
                border-radius:50%;
                object-fit:cover;
                border:3px solid #2563eb;
            ">

            <div>

                <div style="
                    font-size:24px;
                    color:#64748b;
                ">
                    Welcome,
                </div>

                <div style="
                    font-size:28px;
                    font-weight:800;
                    color:#0f172a;
                ">
                    {name}
                </div>

            </div>

        </div>

    </div>

</div>

<div style="
    text-align:center;
    width:100%;
    margin-top:300px;
    font-family:Arial,sans-serif;
">

    <!-- SMALL TITLE -->
    <div style="
        font-size:100px;          
        font-weight:780;
        margin-bottom:32px;

        background:linear-gradient(135deg,#2563eb,#0ea5e9);
        background-size:100%;

        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;

        background-clip:text;
        color:transparent;

        letter-spacing:2px;     
    ">
        STUDENT DIGITAL
    </div>

    <!-- HUGE TITLE -->
    <div style="
        font-size:150px;        
        font-weight:940;
        line-height:0.9;        

        background:linear-gradient(135deg,#2563eb,#0ea5e9);
        background-size:100%;

        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;

        background-clip:text;
        color:transparent;

        letter-spacing:-5px;    
    ">
        CLEARANCE<br>
        SYSTEM
    </div>

</div>


"""
@app.route("/student/profile", methods=["GET", "POST"])
def student_profile():

    students = load_students()
    sid = session.get("user")

    if not sid or sid not in students:
        return redirect("/login")

    s = students[sid]

    # 🔥 DEFAULT PROFILE DATA
    name = s.get("name", "Student")
    program = s.get("program", "N/A")
    year = s.get("year", "N/A")
    term = s.get("term", "N/A")
    funding = s.get("funding", "N/A")

    profile_pic = s.get("profile_pic", "/static/default.png")

    # -------- HANDLE PROFILE UPDATE --------
    if request.method == "POST":

        if "profile_pic" in request.files:
            file = request.files["profile_pic"]

            if file and file.filename != "":

                from werkzeug.utils import secure_filename
                import os

                # 🔥 ensure folder exists
                upload_folder = os.path.join("static", "profile_pics")
                os.makedirs(upload_folder, exist_ok=True)

                filename = f"{sid}_{secure_filename(file.filename)}"
                filepath = os.path.join(upload_folder, filename)

                file.save(filepath)

                # 🔥 save path in student data
                s["profile_pic"] = "/" + filepath.replace("\\", "/")
                save_students(students)

                profile_pic = s["profile_pic"]

    return NAV + f"""
<div style="padding:20px; font-family:Arial;">

    <!-- PROFILE PICTURE -->
    <form method="POST" enctype="multipart/form-data">

        <label style="cursor:pointer;">

            <img src="{profile_pic}" 
                 style="
                    width:330px;
                    height:330px;
                    border-radius:50%;
                    object-fit:cover;
                    box-shadow:0 8px 16px rgba(0,0,0,0.2);
                 ">

            <input type="file"
                   name="profile_pic"
                   accept="image/*"
                   style="display:none;"
                   onchange="this.form.submit()">

        </label>

    </form>

    <!-- DETAILS CARD -->
    <div style="
        margin-top:20px;
        padding:20px;
        background:white;
        border-radius:16px;
        line-height:2;
        font-size:28px;
        box-shadow:0 16px 32px rgba(0,0,0,0.12);
    ">

        <h3 style="
            margin-top:0;
            margin-bottom:20px;
            font-size:34px;
        ">
            {name}
        </h3>

        <p><b>ID:</b> {sid}</p>

        <p><b>Program:</b> {program}</p>

        <p><b>Year:</b> {year}</p>

        <p><b>Term:</b> {term}</p>

        <p><b>Funding:</b> {funding}</p>

    </div>

</div>

<!-- BACK BUTTON -->
<div style="text-align:center; margin-top:30px;">

    <a href="/student" style="
        display:inline-block;
        padding:12px 24px;
        background:linear-gradient(135deg,#2563eb,#16a34a);
        color:white;
        border-radius:12px;
        text-decoration:none;
        font-weight:bold;
        box-shadow:0 4px 12px rgba(0,0,0,0.2);
    ">
        ⬅ Back to Main Menu
    </a>

</div>
"""
        
@app.route("/student/accommodation")
def student_accommodation():

    if session.get("role") != "student":
        return redirect("/login")

    students = load_students()
    sid = session.get("user")

    if sid not in students:
        return "<h2>Student not found</h2>"

    s = students[sid]
    nav = get_nav("student", sid)

    # ✅ CORRECT DATA SOURCE (matches your system)
    acc = s.get("accommodation", "Not Assigned")
    hostel = s.get("hostel", "Not Assigned")
    room = s.get("room", "Not Assigned")

    items = s.get("hostel_items", {})
    key = items.get("key", "Not Issued")
    mattress = items.get("mattress", "Not Issued")

    return nav + f"""
<div style="padding:20px; font-family:Arial;">

    <h2 style="margin-bottom:15px; font-size:58px;"> Accommodation</h2>

    <div style="
        background: white
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        border: 1px solid (135deg, rgba(37,99,235,0.2), rgba(22,163,74,0.2));
    ">

        <table width="100%" cellpadding="10" style="
            border-collapse: collapse;
            font-size: 45px;
            background: white;
            border-radius: 10px;
        ">

                <tr style="background:#f1f5f9;">
                    <th align="left">Item</th>
                    <th align="left">Details</th>
                </tr>

                <tr><td><b>Type</b></td><td>{acc}</td></tr>
                <tr><td><b>Hostel</b></td><td>{hostel}</td></tr>
                <tr><td><b>Room</b></td><td>{room}</td></tr>
                <tr><td><b>Key</b></td><td>{key}</td></tr>
                <tr><td><b>Mattress</b></td><td>{mattress}</td></tr>

            </table>

        </div>

    </div>
    <div style="text-align:center; margin-top:30px;">
    <a href="/student" style="
        display:inline-block;
        padding:12px 24px;
        background:linear-gradient(135deg,#2563eb,#16a34a);
        color:white;
        border-radius:12px;
        text-decoration:none;
        font-weight:bold;
        box-shadow:0 4px 12px rgba(0,0,0,0.2);
    ">
        ⬅ Back to Main Menu
    </a>
</div>
    """
    
@app.route("/student/accounts")
def student_accounts():

    students = load_students()

    sid = session.get("user")

    if not sid or sid not in students:
        return redirect("/login")

    s = students[sid]

    acc = s.get("accounts", {})

    total_fee = acc.get("total_fee", 7860)

    paid = acc.get("paid", 0)

    minimum_required = acc.get("minimum_required", 4000)

    outstanding = total_fee - paid

    # 🔥 USE HISTORY INSTEAD OF PAYMENTS
    history = acc.get("history", [])

    # 🔥 BUILD PAYMENT HISTORY ROWS
    payment_rows = ""

    for p in history:

        payment_rows += f"""

        <tr>

            <td>
                K{p.get('amount', 0)}
            </td>

            <td>
                {p.get('status', 'Pending')}
            </td>

            <td>
                {p.get('reason', '')}
            </td>

        </tr>
        """

    return NAV + f"""

    <div style="
        padding:20px;
        font-size:40px;
        font-family:Arial;
    ">

        <h3>
            Accounts Summary
        </h3>

        <table border="1"
        width="100%"
        cellpadding="8"

        style="
            border-collapse:collapse;
            font-size:38px;
        ">

            <tr style="background:#ddd;">

                <th>Item</th>

                <th>Value</th>

            </tr>

            <tr>

                <th>Total Fees</th>

                <td>K{total_fee}</td>

            </tr>

            <tr>

                <th>Amount Paid</th>

                <td>K{paid}</td>

            </tr>

            <tr>

                <th>Outstanding Balance</th>

                <td>K{outstanding}</td>

            </tr>

            <tr>

                <th>Minimum Required</th>

                <td>K{minimum_required}</td>

            </tr>

        </table>

        <br><br>

        <h3>
             Payment History
        </h3>

        <table border="1"
        width="100%"
        cellpadding="8"

        style="
            border-collapse:collapse;
            font-size:38px;
        ">

            <tr style="background:#ddd;">

                <th>Amount</th>

                <th>Status</th>

                <th>Reason</th>

            </tr>

            {payment_rows}

        </table>

    </div>

    <div style="
        text-align:center;
        margin-top:30px;
    ">

        <a href="/student"

        style="
            display:inline-block;
            padding:12px 24px;
            background:linear-gradient(135deg,#2563eb,#16a34a);
            color:white;
            border-radius:12px;
            text-decoration:none;
            font-weight:bold;
            box-shadow:0 4px 12px rgba(0,0,0,0.2);
        ">

            ⬅ Back to Main Menu

        </a>

    </div>
    """
    
@app.route("/student/payment/<sid>")
def payment_page(sid):

    return f"""
    {NAV}
    <div style="padding:20px; font-family:Arial;font-size:38px;">

        <h2> Upload Payment Proof</h2>

        <div style="
            border:1px solid #ddd;
            padding:20px;
            font-size:38px;
            border-radius:10px;
            max-width:400px;
            style="
    background: rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    border: 1px solid rgba(255,255,255,0.3);
"
        ">

            <form method="POST" action="/upload-proof" enctype="multipart/form-data">

                <input type="hidden" name="student_id" value="{sid}">

                <label>Amount Paid:</label><br>
                <input type="number" name="amount" required style="width:100%;padding:8px;"><br><br>

                <label>Upload Proof (screenshot/photo):</label><br>
                <input type="file" name="proof" accept="image/*" required><br><br>

                <button style="
                    background:#2563eb;
                    color:white;
                    padding:10px 20px;
                    border:none;
                    font-size:28px;
                    border-radius:6px;
                    cursor:pointer;
                    width:100%;
                ">
                    Submit Payment
                </button>

            </form>

        </div>
    </div>
    <div style="text-align:center; margin-top:30px;">
    <a href="/student" style="
        display:inline-block;
        padding:12px 24px;
        background:linear-gradient(135deg,#2563eb,#16a34a);
        color:white;
        border-radius:12px;
        text-decoration:none;
        font-weight:bold;
        box-shadow:0 4px 12px rgba(0,0,0,0.2);
    ">
        ⬅ Back to Main Menu
    </a>
</div>
    """

import os

@app.route("/upload-proof", methods=["POST"])
def upload_proof():

    import os  # 🔥 ensure imported (safe even if already imported)

    students = load_students()

    student_id = request.form.get("student_id")
    amount = request.form.get("amount")
    file = request.files.get("proof")

    print("Student ID:", student_id)
    print("Amount:", amount)
    print("File:", file)

    if not student_id or student_id not in students:
        return "❌ Invalid student"

    if not file or file.filename == "":
        return "❌ No file uploaded"

    if not amount:
        return "❌ Amount missing"

    # 🔥 ENSURE accounts structure FIRST
    if "accounts" not in students[student_id]:
        students[student_id]["accounts"] = {
            "total_fee": 7860,
            "paid": 0,
            "minimum_required": 4000,
            "payments": []
        }

    if "payments" not in students[student_id]["accounts"]:
        students[student_id]["accounts"]["payments"] = []

    # 🔥 SAFE UPLOAD FOLDER
    upload_folder = "uploads"
    os.makedirs(upload_folder, exist_ok=True)

    # 🔥 SAFE FILE NAME
    count = len(students[student_id]["accounts"]["payments"])

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{student_id}_{count}{ext}"

    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # 🔥 VALIDATE AMOUNT
    try:
        amount = float(amount)
    except:
        return "❌ Invalid amount"

    # 🔥 ADD PAYMENT
    students[student_id]["accounts"]["payments"].append({
        "amount": amount,
        "file": filename,
        "status": "Pending",
        "reason": ""
    })

    save_students(students)

    return get_nav("student", student_id) + """
    <h3 style='color:green;'>✅ Payment uploaded. Awaiting approval.</h3>
    <a href='/student'>Back</a>
    
    <div style="text-align:center; margin-top:30px;">
    <a href="/student" style="
        display:inline-block;
        padding:12px 24px;
        background:linear-gradient(135deg,#2563eb,#16a34a);
        color:white;
        border-radius:12px;
        text-decoration:none;
        font-weight:bold;
        box-shadow:0 4px 12px rgba(0,0,0,0.2);
    ">
        ⬅ Back to Main Menu
    </a>
</div>
    """


@app.route("/student/clearance")
def student_clearance():

    if session.get("role") != "student":
        return redirect("/login")

    students = load_students()

    sid = session.get("user")

    if sid not in students:
        return "<h2>Student not found</h2>"

    s = students[sid]

    # 🔥 Hostel items
    items = s.get("hostel_items", {})

    mattress = items.get("mattress", "Not Assigned")

    # 🔥 Navigation
    nav = get_nav("student", sid)

    # -------- LIBRARY --------
    books = s.get("library", {}).get("books", [])

    library_missing = [
        b["name"]
        for b in books
        if not b.get("returned", True)
    ]

    library_status = "Cleared" if not library_missing else "Pending"

    library_reason = (
        "None"
        if not library_missing
        else ", ".join(library_missing)
    )

    # -------- SPORTS --------
    sports = s.get("sports", {})

    sports_items = sum(len(v) for v in sports.values())

    sports_status = (
        "Cleared"
        if sports_items == 0
        else "Pending"
    )

    sports_reason = (
        "None"
        if sports_items == 0
        else "Unreturned sports items"
    )

    # -------- STORES --------
    stores_status = "Cleared" if mattress in ["Returned", "NIL"] else "Pending"
    stores_reason = "None" if stores_status == "Cleared" else "Mattress not returned"

    # -------- TSO --------
    tso_status = "Physical Clearance Required"

    tso_reason = "Key and physical asset verification"

    # -------- HOSTEL --------
    hostel_status = "Physical Clearance Required"

    hostel_reason = "Room inspection and hostel verification"

    # -------- DEPARTMENTS --------
    departments = s.get("departments", {})

    # -------- AME --------
    ame_data = departments.get("ame", {"tools": []})

    tools = ame_data.get("tools", [])

    pending_tools = [
        t["name"]
        for t in tools
        if not t.get("returned", True)
    ]

    ame_status = (
        "Cleared"
        if not pending_tools
        else "Pending"
    )

    ame_reason = (
        "None"
        if not pending_tools
        else ", ".join(pending_tools)
    )

    # -------- ACCOUNTS --------
    acc_data = s.get("accounts", {})

    total_fee = acc_data.get("total_fee", 0)

    paid = acc_data.get("paid", 0)

    minimum_required = acc_data.get(
        "minimum_required",
        4000
    )

    outstanding = total_fee - paid

    if outstanding <= 0:

        accounts_status = "Cleared"

        accounts_reason = "Fees fully paid"

    elif paid >= minimum_required:

        accounts_status = "Cleared"

        accounts_reason = (
            "Meets minimum payment requirement"
        )

    else:

        accounts_status = "Pending"

        accounts_reason = (
            f"Outstanding balance: K{outstanding}"
        )



    # -------- OVERALL --------
    statuses = [

        library_status,

        sports_status,

        accounts_status,

        departments.get(
            "communication",
            {}
        ).get("status", "Pending"),

        departments.get(
            "mathematics",
            {}
        ).get("status", "Pending"),

        departments.get(
            "hr",
            {}
        ).get("status", "Pending"),

        departments.get(
            "training",
            {}
        ).get("status", "Pending"),

        ame_status

    ]

    cleared = sum(
        1
        for s in statuses
        if s == "Cleared"
    )

    total = len(statuses)

    overall = f"{cleared}/{total} Cleared"

    if cleared == total:

        overall += " ✅ FULLY CLEARED"

    else:

        overall += " ⏳ PENDING"
        generated_time = datetime.now().strftime("%d %B %Y | %I:%M %p")
        
        

    # -------- OUTPUT --------
    return nav + f"""
    <div style="
    padding:20px;
    font-family:Arial;
    background:white;
    font-size:38px;
    border-radius:12px;
    margin:20px;
    box-shadow:0 2px 10px rgba(0,0,0,0.1);
">

        <h2> Clearance Status</h2>
        
        <div style="
    margin-bottom:25px;
    font-size:20px;
    color:#475569;
    font-weight:bold;
">
    Generated:
    {generated_time}
</div>

        <table border="2" width="100%" cellpadding="14" style="border-collapse:collapse; font-size:38px;">
            <tr style="background:#eee;">
                <th>Department</th>
                <th>Status</th>
                <th>Reason</th>
            </tr>

            <tr><td>Library</td><td>{library_status}</td><td>{library_reason}</td></tr>
            <tr><td>Sports</td><td>{sports_status}</td><td>{sports_reason}</td></tr>
            <tr><td>Accounts</td><td>{accounts_status}</td><td>{accounts_reason}</td></tr>
            

            <tr><td>Communication Skills</td><td>{departments.get("communication", {}).get("status", "Pending")}</td><td>{departments.get("communication", {}).get("reason", "")}</td></tr>
            <tr><td>Mathematics</td><td>{departments.get("mathematics", {}).get("status", "Pending")}</td><td>{departments.get("mathematics", {}).get("reason", "")}</td></tr>
            <tr><td>Human Resource</td><td>{departments.get("hr", {}).get("status", "Pending")}</td><td>{departments.get("hr", {}).get("reason", "")}</td></tr>
            <tr><td>Head Of Training Section</td><td>{departments.get("training", {}).get("status", "Pending")}</td><td>{departments.get("training", {}).get("reason", "")}</td></tr>
            <tr><td>AME Stores</td><td>{ame_status}</td><td>{ame_reason}</td></tr>
            <tr><td>Stores</td><td>{stores_status}</td><td>{stores_reason}</td></tr>
                
        </table>

            <!-- PHYSICAL CLEARANCE -->


    <td colspan="3" style="
        height:50px;
        font-weight:bold;
        border:none;
        background:white;
    "></td>

</tr>

<tr>

    <td>
        Technical Services Office
    </td>


    <div>
        Key and room inspection verification
    </div>

    <div style="
        margin-top:18px;
        font-weight:bold;
    ">
        Signature
    </div>

    <div style="
        width:240px;
        height:45px;
        border:2px solid #999;
        border-radius:8px;
        margin-top:8px;
    "></div>

</td>

<tr>

    <tr>

    <td colspan="3" style="
        height:50px;
        font-weight:bold;
        border:none;
        background:white;
    "></td>

</tr>

<tr>

    <td>
        Hostel
    </td>

    <td style="
        color:#ea580c;
        font-weight:bold;
    ">
        

    <td>

        <div>
            Room inspection and hostel verification
        </div>

        <div style="
            margin-top:18px;
            font-weight:bold;
        ">
            Signature
        </div>

        <div style="
            width:240px;
            height:45px;
            border:2px solid #999;
            border-radius:8px;
            margin-top:8px;
        "></div>

    </td>

</tr>

        <p style="
            margin-top:15px;
            color:#555;
            font-size:24px;
        ">

            If any clearance status appears incorrect
            or requires verification,
            please visit the respective department.

        </p>

        <div style="
            text-align:center;
            margin-top:20px;
        ">

            <h2>{overall}</h2>

        </div>

    </div>

    <div style="
        width:100%;
        display:flex;
        justify-content:flex-end;
        margin-top:30px;
    ">

        <a href="/print_clearance"
        target="_blank">

            <button style="
                background:#64748b;
                color:white;
                border:none;
                padding:14px 30px;
                border-radius:12px;
                font-size:18px;
                font-weight:bold;
                cursor:pointer;
                box-shadow:0 8px 20px rgba(0,0,0,0.12);
            ">

                🖨️ Export Clearance

            </button>

        </a>

    </div>

    <div style="
        text-align:center;
        margin-top:30px;
    ">

        <a href="/student"

        style="
            display:inline-block;
            padding:12px 24px;
            background:linear-gradient(135deg,#2563eb,#16a34a);
            color:white;
            border-radius:12px;
            text-decoration:none;
            font-weight:bold;
            box-shadow:0 4px 12px rgba(0,0,0,0.2);
        ">

            ⬅ Back to Main Menu

        </a>

    </div>
    """

from datetime import datetime
from flask import session, redirect

@app.route("/print_clearance")
def print_clearance():

    # ==================================
    # LOGIN CHECK
    # ==================================
    if "user" not in session:
        return redirect("/login")

    students = load_students()

    sid = session.get("user")

    if sid not in students:
        return "<h3>Student not found</h3>"

    s = students[sid]

    name = s.get("name", "Unknown Student")

    student_departments = s.get("departments", {})

    # ==================================
    # GENERATION INFO
    # ==================================
    generated_time = datetime.now().strftime(
        "%d %B %Y | %I:%M %p"
    )

    document_id = (
        f"CLR-{sid}-"
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    # ==================================
    # DEPARTMENTS
    # ==================================
    department_list = [

        "Library",
        "Sports",
        "Accounts",
        "Stores",
        "Communication Skills",
        "Mathematics",
        "Human Resource",
        "Head Of Training Section",
        "AME Stores",
        "Technical Services Office",
        "Hostel"

    ]

    dept_keys = {

        "Library": "library",
        "Sports": "sports",
        "Accounts": "accounts",
        "Stores": "stores",
        "Communication Skills": "communication",
        "Mathematics": "mathematics",
        "Human Resource": "hr",
        "Head Of Training Section": "training",
        "AME Stores": "ame",
        "Technical Services Office": "tso",
        "Hostel": "hostel"

    }

    rows = []

    not_cleared = []

    # ==================================
    # LOOP DEPARTMENTS
    # ==================================
    for dept in department_list:

        key = dept_keys.get(dept, dept.lower())

        status = "Pending"

        reason = "Pending Clearance"

        # ==================================
        # LIBRARY
        # ==================================
        if dept == "Library":

            books = s.get("library", {}).get("books", [])

            unreturned = [

                b for b in books

                if not b.get("returned", True)

            ]

            if len(unreturned) == 0:

                status = "Cleared"

                reason = "No outstanding books"

            else:

                status = "Pending"

                reason = "Unreturned books"

        # ==================================
        # SPORTS
        # ==================================
        elif dept == "Sports":

            sports = s.get("sports", {})

            total_items = sum(
                len(v)
                for v in sports.values()
            )

            if total_items == 0:

                status = "Cleared"

                reason = "No sports items pending"

            else:

                status = "Pending"

                reason = "Sports items not returned"

        # ==================================
        # STORES
        # ==================================
        elif dept == "Stores":

            items = s.get("hostel_items", {})

            mattress = items.get("mattress")

            if mattress in ["Returned", "NIL"]:

                status = "Cleared"

                reason = "Mattress returned"

            else:

                status = "Pending"

                reason = "Mattress not returned"

        # ==================================
        # ACCOUNTS
        # ==================================
        elif dept == "Accounts":

            acc = s.get("accounts", {})

            total_fee = acc.get(
                "total_fee",
                7860
            )

            paid = acc.get("paid", 0)

            minimum = acc.get(
                "minimum_required",
                4000
            )

            outstanding = total_fee - paid

            if outstanding <= 0 or paid >= minimum:

                status = "Cleared"

                reason = "Accounts requirements met"

            else:

                status = "Pending"

                reason = (
                    f"Outstanding balance: "
                    f"K{outstanding}"
                )

        # ==================================
        # AME
        # ==================================
        elif dept == "AME Stores":

            ame_data = student_departments.get(
                "ame",
                {"tools": []}
            )

            tools = ame_data.get("tools", [])

            pending_tools = [

                t["name"]

                for t in tools

                if not t.get("returned", True)

            ]

            if len(pending_tools) == 0:

                status = "Cleared"

                reason = "All AME tools returned"

            else:

                status = "Pending"

                reason = ", ".join(
                    pending_tools
                )

        # ==================================
        # TECHNICAL SERVICES OFFICE
        # ==================================
        elif dept == "Technical Services Office":

            status = (
                "Physical Clearance Required"
            )

            reason = """
            <div style="
                font-weight:bold;
                margin-bottom:14px;
            ">
                Key verification required
            </div>

            <div style="
                font-weight:bold;
                margin-bottom:8px;
            ">
                Signature
            </div>

            <div style="
                width:230px;
                height:42px;
                border:2px solid #999;
                border-radius:6px;
            "></div>
            """

        # ==================================
        # HOSTEL
        # ==================================
        elif dept == "Hostel":

            status = (
                "Physical Clearance Required"
            )

            reason = """
            <div style="
                font-weight:bold;
                margin-bottom:14px;
            ">
                Room inspection and hostel verification
            </div>

            <div style="
                font-weight:bold;
                margin-bottom:8px;
            ">
                Signature
            </div>

            <div style="
                width:230px;
                height:42px;
                border:2px solid #999;
                border-radius:6px;
            "></div>
            """

        # ==================================
        # NORMAL DEPARTMENTS
        # ==================================
        else:

            dept_data = student_departments.get(
                key,
                {}
            )

            status = dept_data.get(
                "status",
                "Pending"
            )

            reason = dept_data.get(
                "reason",
                "Pending Clearance"
            )

        # ==================================
        # EXPORT CHECK
        # ==================================
        if dept not in [

            "Technical Services Office",
            "Hostel"

        ]:

            if status != "Cleared":

                not_cleared.append(dept)

        # ==================================
        # COLOR
        # ==================================
        if status == "Cleared":

            color = "#16a34a"

        elif "Physical" in status:

            color = "#ea580c"

        else:

            color = "#dc2626"

        # ==================================
        # ROWS
        # ==================================
        rows.append(f"""
        <tr style="
            page-break-inside:avoid;
        ">

            <td>
                <b>{dept}</b>
            </td>

            <td style="
                color:{color};
                font-weight:bold;
            ">
                {status}
            </td>

            <td>
                {reason}
            </td>

        </tr>
        """)

    # ==================================
    # BLOCK EXPORT
    # ==================================
    if len(not_cleared) > 0:

        uncleared = ", ".join(not_cleared)

        return f"""
        <div style="
            font-family:Arial;
            max-width:700px;
            margin:80px auto;
            background:white;
            padding:40px;
            border-radius:14px;
            border:1px solid #e2e8f0;
            box-shadow:0 4px 12px rgba(0,0,0,0.08);
        ">

            <h1 style="
                color:#dc2626;
            ">
                Clearance Export Unavailable
            </h1>

            <p style="
                font-size:18px;
                line-height:1.7;
                color:#334155;
            ">

                Your clearance process is not yet complete.

                Please complete clearance with all
                required departments before generating
                an official clearance report.

            </p>

            <div style="
                margin-top:25px;
                padding:18px;
                background:#f8fafc;
                border:1px solid #cbd5e1;
                border-radius:10px;
            ">

                <b>
                    Pending Departments:
                </b>

                <br><br>

                {uncleared}

            </div>

        </div>
        """

    # ==================================
    # FINAL HTML
    # ==================================
    return f"""
    <html>

    <head>

        <title>
            Clearance Report
        </title>

    </head>

    <body style="
        font-family:Arial;
        padding:40px;
        background:white;
    ">

        <h1 style="
            text-align:center;
            color:#2563eb;
        ">
            STUDENT CLEARANCE REPORT
        </h1>

        <div style="
            text-align:center;
            color:#64748b;
            margin-top:10px;
        ">
            Generated:
            {generated_time}
        </div>

        <div style="
            text-align:center;
            color:#dc2626;
            margin-top:10px;
            margin-bottom:40px;
            font-weight:bold;
        ">
            Document ID:
            {document_id}

            <br><br>

            This clearance form is valid
            only on the generated date
            and time.
        </div>

        <h2>
            Student Name:
            {name}
        </h2>

        <h2>
            Student ID:
            {sid}
        </h2>

        <br>

        <table border="1"
               width="100%"
               cellpadding="12"
               style="
                    border-collapse:collapse;
                    font-size:18px;
               ">

            <tr style="
                background:#2563eb;
                color:white;
            ">

                <th>
                    Department
                </th>

                <th>
                    Status
                </th>

                <th>
                    Remarks
                </th>

            </tr>

            {''.join(rows)}

        </table>

        <br><br>

        <div style="
            text-align:right;
            color:#64748b;
            font-size:15px;
        ">
            Generated by Student Digital Clearance System
        </div>

        <script>
            window.print()
        </script>

    </body>

    </html>
    """
    
# ---------------- ERROR HANDLERS ----------------
import logging

@app.errorhandler(404)
def page_not_found(e):
    logging.warning(f"404 error: {request.path}")

    return NAV + f"""
    <div style="padding:20px; font-family:Arial;">
        <h2 style="color:red;">404 - Page Not Found</h2>
        <p>No route exists for: <b>{request.path}</b></p>
        <a href="/">Return Home</a>
    </div>
    """, 404

@app.errorhandler(500)
def server_error(e):
    return NAV + "<h2>500 - Server Error</h2>", 500
  
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
    
# -------- RUN APP --------
import os

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )