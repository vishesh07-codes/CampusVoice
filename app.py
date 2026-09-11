from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "college-complaint-secret-key-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///complaints.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Database Table
class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    admin_remark = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 1. Landing Page
@app.route("/")
def home():
    return render_template("index.html")


# 2. Student Portal
@app.route("/student", methods=["GET", "POST"])
def student_portal():
    if request.method == "POST":
        name = request.form.get("student_name", "").strip()
        roll = request.form.get("roll_number", "").strip()
        category = request.form.get("category", "").strip()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not roll or not title or not description:
            flash("Kripya saari fields bharein!", "error")
            return redirect(url_for("student_portal"))

        new_complaint = Complaint(
            student_name=name,
            roll_number=roll,
            category=category,
            title=title,
            description=description,
        )
        db.session.add(new_complaint)
        db.session.commit()
        flash(
            f"Complaint successfully lodge ho gayi! Tracking ID: #{new_complaint.id}",
            "success",
        )
        return redirect(url_for("student_portal", search_roll=roll))

    search_roll = request.args.get("search_roll", "").strip()
    my_complaints = []
    if search_roll:
        my_complaints = (
            Complaint.query.filter_by(roll_number=search_roll)
            .order_by(Complaint.created_at.desc())
            .all()
        )

    return render_template(
        "student.html", complaints=my_complaints, search_roll=search_roll
    )


# 3. Admin Portal
@app.route("/admin")
def admin_portal():
    category_filter = request.args.get("category", "")
    status_filter = request.args.get("status", "")

    query = Complaint.query
    if category_filter:
        query = query.filter_by(category=category_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    all_complaints = query.order_by(Complaint.created_at.desc()).all()
    return render_template(
        "admin.html",
        complaints=all_complaints,
        selected_cat=category_filter,
        selected_stat=status_filter,
    )


# 4. Admin Update Action
@app.route("/admin/update/<int:complaint_id>", methods=["POST"])
def update_status(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    complaint.status = request.form.get("status")
    complaint.admin_remark = request.form.get("admin_remark", "").strip()
    db.session.commit()
    flash(f"Complaint #{complaint.id} ka status update ho gaya!", "success")
    return redirect(url_for("admin_portal"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
