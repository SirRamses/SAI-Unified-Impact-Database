# -------------------------
# Imports
# -------------------------
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from functools import wraps
import os
import pandas as pd
from dotenv import load_dotenv
import uuid

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:SAIProject#237@db.oadpigfwhmsnetcelgyr.supabase.co:5432/postgres"
)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "tmp_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------
# SQLAlchemy setup
# -------------------------
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# -------------------------
# Flask app
# -------------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change_this_to_a_secret_key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB limit

# -------------------------
# Root Admin (in-memory)
# -------------------------
ROOT_ADMIN_USERNAME = "admin"
ROOT_ADMIN_PASSWORD_HASH = generate_password_hash("admin123")
users = {
    ROOT_ADMIN_USERNAME: {"password": ROOT_ADMIN_PASSWORD_HASH, "role": "admin", "status": "active"}
}
pending_users = {}

# -------------------------
# Models
# -------------------------
class LearnerProfile(Base):
    __tablename__ = "learner_profiles"
    learner_number = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    gender = Column(String)
    region = Column(String)
    learning_hub = Column(String)
    program = Column(String)
    class_name = Column("class", String)
    co_learner = Column(String)
    grade_level = Column(String)

class PreCompetencyEvaluation(Base):
    __tablename__ = "pre_competency_evaluation"
    id = Column(Integer, primary_key=True)
    learner_number = Column(String, ForeignKey("learner_profiles.learner_number", ondelete="CASCADE"))
    score = Column(Integer)

class PostCompetencyEvaluation(Base):
    __tablename__ = "post_competency_evaluation"
    id = Column(Integer, primary_key=True)
    learner_number = Column(String, ForeignKey("learner_profiles.learner_number", ondelete="CASCADE"))
    score = Column(Integer)

class PreConfidenceSelfEsteem(Base):
    __tablename__ = "pre_confidence_and_self_esteem"
    id = Column(Integer, primary_key=True)
    learner_number = Column(String, ForeignKey("learner_profiles.learner_number", ondelete="CASCADE"))
    score = Column(Integer)

class PostConfidenceSelfEsteem(Base):
    __tablename__ = "post_confidence_and_self_esteem"
    id = Column(Integer, primary_key=True)
    learner_number = Column(String, ForeignKey("learner_profiles.learner_number", ondelete="CASCADE"))
    score = Column(Integer)

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    learner_number = Column(String, ForeignKey("learner_profiles.learner_number", ondelete="CASCADE"))
    date = Column(String)
    status = Column(String)

class WorksheetScore(Base):
    __tablename__ = "worksheet_score"
    id = Column(Integer, primary_key=True)
    learner_number = Column(String, ForeignKey("learner_profiles.learner_number", ondelete="CASCADE"))
    ws_number = Column(Integer)
    score = Column(Integer)

class HopeIndex(Base):
    __tablename__ = "hope_index"
    id = Column(Integer, primary_key=True)
    learner_number = Column(String, ForeignKey("learner_profiles.learner_number", ondelete="CASCADE"))
    day_number = Column(Integer)
    am_score = Column(Integer)
    pm_score = Column(Integer)

#Base.metadata.create_all(bind=engine)

# -------------------------
# Decorators
# -------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please login first")
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admins only")
            return redirect(url_for("learners_list"))
        return f(*args, **kwargs)
    return wrapper



# -------------------------
# Auth Routes
# -------------------------
@app.route("/")
def home_page():
    return redirect(url_for("login_page"))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = users.get(username)
        if not user:
            flash("Account does not exist or is pending approval")
            return redirect(url_for("login_page"))
        if user["status"] != "active":
            flash("Your account is not approved yet")
            return redirect(url_for("login_page"))
        if check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user["role"]
            return redirect(url_for("dashboard_page"))
        flash("Invalid credentials")
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Username and password are required")
            return redirect(url_for("register_page"))
        if username in users or username in pending_users:
            flash("Username already exists or is pending approval")
            return redirect(url_for("register_page"))
        pending_users[username] = {
            "password": generate_password_hash(password),
            "role": "user",
            "status": "pending"
        }
        flash("Account request submitted. Await admin approval.")
        return redirect(url_for("login_page"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout_page():
    session.clear()
    flash("Logged out successfully")
    return redirect(url_for("login_page"))

# -------------------------
# Dashboard & Learners
# -------------------------
@app.route("/dashboard")
@login_required
def dashboard_page():
    counts = {"Luzon": 0, "Visayas": 0, "Mindanao": 0}
    db_error = None

    try:
        db = SessionLocal()
        counts = {
            "Luzon": db.query(LearnerProfile).filter_by(region="Luzon").count(),
            "Visayas": db.query(LearnerProfile).filter_by(region="Visayas").count(),
            "Mindanao": db.query(LearnerProfile).filter_by(region="Mindanao").count()
        }
    except Exception as e:
        db_error = "Database not connected (offline mode)"
    finally:
        try:
            db.close()
        except:
            pass

    return render_template(
        "dashboard.html",
        learner_counts=counts,
        db_error=db_error,
        role=session.get("role")
    )


@app.route("/learners")
@login_required
def learners_list():
    # Paths for uploaded Excel files for 3 regions
    uploaded_luzon = session.get("uploaded_excel_luzon")
    uploaded_visayas = session.get("uploaded_excel_visayas")
    uploaded_mindanao = session.get("uploaded_excel_mindanao")

    # Initialize empty dictionaries
    dfs_luzon = []
    dfs_visayas = []
    dfs_mindanao = []

    # Helper function to read learner_profiles from Excel
    def read_learner_profiles(path):
        if path and os.path.exists(path):
            try:
                df = pd.read_excel(path, sheet_name="learner_profiles")
                df = df.fillna("")
                return df.to_dict("records")
            except Exception as e:
                flash(f"Failed to load learner_profiles from {path}: {e}")
        return []

    dfs_luzon = read_learner_profiles(uploaded_luzon)
    dfs_visayas = read_learner_profiles(uploaded_visayas)
    dfs_mindanao = read_learner_profiles(uploaded_mindanao)

    return render_template(
        "learner_profiles.html",
        dfs_luzon=dfs_luzon,
        dfs_visayas=dfs_visayas,
        dfs_mindanao=dfs_mindanao,
        role=session.get("role")
    )


# -------------------------
# Database Management
# -------------------------
REQUIRED_SHEETS = [
    "learner_profiles",
    "pre_confidence_and_self_esteem",
    "post_confidence_and_self_esteem",
    "attendance",
    "worksheet_score",
    "hope_index",
    "pre_competency_evaluation",
    "post_competency_evaluation"
]

# -------------------------
# Learner consistency validator
# -------------------------
def validate_learner_consistency(dfs):
    errors = []

    master_df = dfs["learner_profiles"].fillna("")
    master_set = {
        (str(r["learner_number"]).strip(), r["name"].strip())
        for _, r in master_df.iterrows()
    }

    for sheet, df in dfs.items():
        if sheet == "learner_profiles":
            continue

        df = df.fillna("")

        if "learner_number" not in df.columns or "name" not in df.columns:
            errors.append(f"{sheet}: missing learner_number or name column")
            continue

        for _, row in df.iterrows():
            key = (
                str(row["learner_number"]).strip(),
                row["name"].strip()
            )
            if key not in master_set:
                errors.append(
                    f"{sheet}: learner_number {key[0]} with name '{key[1]}' "
                    "does not match learner_profiles"
                )

    return errors

@app.route("/database-management", methods=["GET", "POST"])
@login_required
@admin_required
def database_management_page():
    # We'll store uploaded paths per region
    uploaded_paths = session.get("uploaded_excel_paths", {"Luzon": None, "Visayas": None, "Mindanao": None})
    
    # Dictionaries to hold data for template
    dfs_luzon, dfs_visayas, dfs_mindanao = {}, {}, {}

    # -------------------------
    # HANDLE POST
    # -------------------------
    if request.method == "POST":
        region = request.form.get("region")  # Which region the upload/save is for

        # =========================
        # UPLOAD & VALIDATE
        # =========================
        if "file" in request.files:
            file = request.files["file"]

            if file.filename == "":
                flash("No file selected")
                return redirect(url_for("database_management_page"))

            if not file.filename.endswith(".xlsx"):
                flash("Only .xlsx files are allowed")
                return redirect(url_for("database_management_page"))

            temp_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.xlsx")
            file.save(temp_path)

            try:
                dfs = pd.read_excel(temp_path, sheet_name=None)

                missing = [s for s in REQUIRED_SHEETS if s not in dfs]
                if missing:
                    os.remove(temp_path)
                    flash(f"Missing required sheets: {', '.join(missing)}")
                    return redirect(url_for("database_management_page"))

                errors = validate_learner_consistency(dfs)
                if errors:
                    os.remove(temp_path)
                    for err in errors[:10]:
                        flash(err)
                    flash("Upload failed due to learner inconsistency across sheets")
                    return redirect(url_for("database_management_page"))

                # Save path in session per region
                uploaded_paths[region] = temp_path
                session["uploaded_excel_paths"] = uploaded_paths
                flash(f"{region} Excel uploaded and validated successfully")
                return redirect(url_for("database_management_page"))

            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                flash(f"Upload failed: {e}")
                return redirect(url_for("database_management_page"))

        # =========================
        # SAVE TO DATABASE
        # =========================
        if "save_db" in request.form:
            uploaded_path = uploaded_paths.get(region)
            if not uploaded_path or not os.path.exists(uploaded_path):
                flash(f"No uploaded file to save for {region}")
                return redirect(url_for("database_management_page"))

            db = SessionLocal()
            try:
                dfs = pd.read_excel(uploaded_path, sheet_name=None)

                for row in dfs["learner_profiles"].fillna("").to_dict("records"):
                    db.merge(LearnerProfile(
                        learner_number=str(row["learner_number"]),
                        name=row["name"],
                        gender=row.get("gender"),
                        region=row.get("region"),
                        learning_hub=row.get("learning_hub"),
                        program=row.get("program"),
                        class_name=row.get("class"),
                        co_learner=row.get("co_learner"),
                        grade_level=row.get("grade_level")
                    ))

                db.commit()
                os.remove(uploaded_path)
                uploaded_paths[region] = None
                session["uploaded_excel_paths"] = uploaded_paths
                flash(f"All {region} data saved successfully")
                return redirect(url_for("database_management_page"))

            except Exception as e:
                db.rollback()
                flash(f"Database save failed for {region}: {e}")
            finally:
                db.close()

    # -------------------------
    # Load uploaded Excel for preview per region
    # -------------------------
    for region_name, path in uploaded_paths.items():
        if path and os.path.exists(path):
            try:
                dfs = pd.read_excel(path, sheet_name=None)
                # Assign to correct variable for template
                if region_name == "Luzon":
                    dfs_luzon = {sheet: df.fillna("").to_dict("records") for sheet, df in dfs.items()}
                elif region_name == "Visayas":
                    dfs_visayas = {sheet: df.fillna("").to_dict("records") for sheet, df in dfs.items()}
                elif region_name == "Mindanao":
                    dfs_mindanao = {sheet: df.fillna("").to_dict("records") for sheet, df in dfs.items()}
            except Exception as e:
                flash(f"Failed to load uploaded file for {region_name}: {e}")
                uploaded_paths[region_name] = None
                session["uploaded_excel_paths"] = uploaded_paths

    return render_template(
        "database_management.html",
        dfs_luzon=dfs_luzon,
        dfs_visayas=dfs_visayas,
        dfs_mindanao=dfs_mindanao,
        role=session.get("role")
    )



# -------------------------
# Accounts Management
# -------------------------
@app.route("/accounts-management")
@login_required
@admin_required
def accounts_management_page():
    return render_template(
        "accounts_management.html",
        users=users,
        pending_users=pending_users,
        role=session.get("role")
    )

@app.route("/admin/approve/<username>")
@login_required
@admin_required
def approve_user_page(username):
    if username in pending_users:
        users[username] = pending_users.pop(username)
        users[username]["status"] = "active"
        flash(f"{username} approved successfully")
    return redirect(url_for("accounts_management_page"))

@app.route("/admin/delete/<username>")
@login_required
@admin_required
def delete_user_page(username):
    if username == ROOT_ADMIN_USERNAME:
        flash("Root admin account cannot be deleted")
        return redirect(url_for("accounts_management_page"))
    if username in users:
        users.pop(username)
        flash(f"Account '{username}' deleted successfully")
    return redirect(url_for("accounts_management_page"))

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8000)
