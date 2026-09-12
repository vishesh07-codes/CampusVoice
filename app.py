import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "college-complaint-secret-key-2026"

database_url = os.environ.get("DATABASE_URL")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
elif os.environ.get("RENDER"):
    # Render par agar cloud DB nahi hai toh safe fallback (crash nahi hoga)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///college_system.db"
else:
    # Aapke local laptop par XAMPP MySQL chalega
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://root:@localhost/college_complaint_db"
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ================= DATABASE MODELS =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    admin_remark = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User", backref=db.backref("complaints", lazy=True))


with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="admin@college.edu").first():
        admin = User(
            name="Admin",
            email="admin@college.edu",
            password=generate_password_hash("admin123"),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()


# ================= 1. HOME =================
@app.route("/")
def home():
    return render_template("index.html")


# ================= 2. REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required!", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered! Please login.", "error")
            return redirect(url_for("login"))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role="student",
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ================= 3. LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["role"] = user.role

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("student_dashboard"))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


# ================= 4. STUDENT DASHBOARD =================
@app.route("/dashboard")
def student_dashboard():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    user_id = session["user_id"]
    total = Complaint.query.filter_by(user_id=user_id).count()
    pending = Complaint.query.filter_by(user_id=user_id, status="Pending").count()
    in_progress = Complaint.query.filter_by(
        user_id=user_id, status="In Progress"
    ).count()
    resolved = Complaint.query.filter_by(user_id=user_id, status="Resolved").count()

    recent = (
        Complaint.query.filter_by(user_id=user_id)
        .order_by(Complaint.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        name=session.get("user_name"),
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        complaints=recent,
    )


# ================= 5. SUBMIT COMPLAINT =================
@app.route("/submit", methods=["GET", "POST"])
def submit_complaint():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    if request.method == "POST":
        category = request.form.get("category")
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()

        if not category or not subject or not description:
            flash("Please fill in all details.", "error")
            return redirect(url_for("submit_complaint"))

        new_c = Complaint(
            user_id=session["user_id"],
            category=category,
            subject=subject,
            description=description,
            status="Pending",
        )
        db.session.add(new_c)
        db.session.commit()
        return redirect(url_for("my_complaints"))

    return render_template("submit.html", name=session.get("user_name"))


# ================= 6. MY COMPLAINTS =================
@app.route("/complaints")
def my_complaints():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    complaints = (
        Complaint.query.filter_by(user_id=session["user_id"])
        .order_by(Complaint.created_at.desc())
        .all()
    )
    return render_template(
        "complaints.html", complaints=complaints, name=session.get("user_name")
    )


# ================= 7. ADMIN DASHBOARD =================
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    total = Complaint.query.count()
    pending = Complaint.query.filter_by(status="Pending").count()
    in_progress = Complaint.query.filter_by(status="In Progress").count()
    resolved = Complaint.query.filter_by(status="Resolved").count()

    all_complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template(
        "admin.html",
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        complaints=all_complaints,
    )


# ================= 8. ADMIN STATUS UPDATE =================
@app.route("/admin/update/<int:complaint_id>", methods=["POST"])
def admin_update_status(complaint_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    c = Complaint.query.get_or_404(complaint_id)
    c.status = request.form.get("status")
    c.admin_remark = request.form.get("admin_remark", "").strip()
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


# ================= 9. LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
