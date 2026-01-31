from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "change_this_to_a_secret_key"

# -------------------------
# Root Admin (Non-deletable)
# -------------------------
ROOT_ADMIN_USERNAME = "admin"
ROOT_ADMIN_PASSWORD_HASH = generate_password_hash("admin123")

# -------------------------
# In-memory users (Phase 2 only)
# -------------------------
users = {
    ROOT_ADMIN_USERNAME: {
        "password": ROOT_ADMIN_PASSWORD_HASH,
        "role": "admin",
        "status": "active"
    }
}

pending_users = {}

# -------------------------
# Mock Learner Data (Phase 2)
# -------------------------
learners = {
    1: {
        "id": 1,
        "name": "Juan Dela Cruz",
        "title": "Grade 1 Learner",
        "image": "images/juan.jpg",
        "description": "Juan shows strong improvement in literacy skills."
    },
    2: {
        "id": 2,
        "name": "Maria Santos",
        "title": "Grade 2 Learner",
        "image": "images/maria.jpg",
        "description": "Maria excels in teamwork and communication."
    },
    3: {
        "id": 3,
        "name": "Pedro Reyes",
        "title": "Grade 3 Learner",
        "image": "images/pedro.jpg",
        "description": "Pedro demonstrates consistent academic growth."
    }
}

# -------------------------
# Decorators
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please login to access this page")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Unauthorized access: Admins only")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------
# Authentication Routes
# -------------------------
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = users.get(username)

        if not user:
            flash("Account does not exist or is pending approval")
            return redirect(url_for("login"))

        if user["status"] != "active":
            flash("Your account is not yet approved by admin")
            return redirect(url_for("login"))

        if check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        flash("Invalid credentials")

    return render_template("index.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out")
    return redirect(url_for("login"))

# -------------------------
# Registration
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users or username in pending_users:
            flash("Username already exists or is pending approval")
            return redirect(url_for("register"))

        pending_users[username] = {
            "password": generate_password_hash(password),
            "role": "user",
            "status": "pending"
        }

        flash("Account request submitted. Await admin approval.")
        return redirect(url_for("login"))

    return render_template("register.html")

# -------------------------
# Main Pages
# -------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    learner_counts = {
        "Luzon": 120,
        "Visayas": 80,
        "Mindanao": 100
    }
    return render_template("dashboard.html", role=session.get("role"), learner_counts=learner_counts)

@app.route("/learners")
@login_required
def learner_profiles():
    return render_template(
        "learner_profiles.html",
        learners=learners.values(),
        role=session.get("role")
    )

@app.route("/learners/<int:learner_id>")
@login_required
def learner_profile_detail(learner_id):
    learner = learners.get(learner_id)
    if not learner:
        flash("Learner not found")
        return redirect(url_for("learner_profiles"))

    return render_template(
        "learner_profile_detail.html",
        learner=learner,
        role=session.get("role")
    )

@app.route("/database-management")
@login_required
def database_management():
    return render_template("database_management.html", role=session.get("role"))

# -------------------------
# Admin Pages
# -------------------------
@app.route("/accounts-management")
@login_required
@admin_required
def accounts_management():
    return render_template(
        "accounts_management.html",
        users=users,
        pending_users=pending_users
    )

@app.route("/admin/approve/<username>")
@login_required
@admin_required
def approve_user(username):
    if username in pending_users:
        users[username] = pending_users.pop(username)
        users[username]["status"] = "active"
        flash(f"{username} approved successfully")
    return redirect(url_for("accounts_management"))

@app.route("/admin/delete/<username>")
@login_required
@admin_required
def delete_user(username):
    if username == ROOT_ADMIN_USERNAME:
        flash("Root admin account cannot be deleted")
        return redirect(url_for("accounts_management"))

    if username in users:
        users.pop(username)
        flash(f"Account '{username}' deleted successfully")

    return redirect(url_for("accounts_management"))

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8000)
