import hmac
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DB_PATH = Path(
    os.environ.get("FEES_TRACKER_DB_PATH", PROJECT_ROOT / "web_demo.db")
).expanduser()
os.environ["FEES_TRACKER_DB_PATH"] = str(WEB_DB_PATH)

from backend import backend
from database import database

database.DB_PATH = WEB_DB_PATH
backend.DB_PATH = WEB_DB_PATH


def _env_flag(name, default):
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _query(sql, parameters=()):
    with sqlite3.connect(database.DB_PATH, factory=database.ClosingConnection) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, parameters).fetchall()


def _seed_demo_data():
    with sqlite3.connect(database.DB_PATH, factory=database.ClosingConnection) as conn:
        student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if student_count:
            return

        students = [
            ("Ama Demo", "Grade 3", 1200.00),
            ("Kojo Sample", "Grade 5", 1500.00),
            ("Abena Example", "Form 1", 1800.00),
            ("Kofi Placeholder", "Grade 2", 1000.00),
        ]
        conn.executemany(
            "INSERT INTO students (full_name, class_grade, term_fees_billed) VALUES (?, ?, ?)",
            students,
        )
        student_ids = {
            name: student_id
            for student_id, name in conn.execute(
                "SELECT student_id, full_name FROM students"
            ).fetchall()
        }
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payments = [
            (student_ids["Ama Demo"], 400.00, today, "Term 1", "Cash", "Demo Parent", "Grade 3"),
            (student_ids["Kojo Sample"], 1500.00, today, "Term 1", "MoMo", "Sample Guardian", "Grade 5"),
            (student_ids["Abena Example"], 700.00, today, "Term 1", "Cash", "Example Parent", "Form 1"),
        ]
        conn.executemany(
            """
            INSERT INTO payments
                (student_id, amount_paid, date_paid, term_name, payment_method, paid_by, class_grade)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            payments,
        )


def _create_app():
    app = Flask(__name__)
    secret_key = os.environ.get("SECRET_KEY")
    is_production = _env_flag("APP_ENV", "") == "production" or bool(os.environ.get("RENDER"))
    if is_production and not secret_key:
        raise RuntimeError("SECRET_KEY must be configured for production.")
    read_only_demo = _env_flag("READ_ONLY_DEMO", "true")
    if not read_only_demo and not (
        os.environ.get("WEB_ADMIN_USERNAME") and os.environ.get("WEB_ADMIN_PASSWORD")
    ):
        raise RuntimeError(
            "WEB_ADMIN_USERNAME and WEB_ADMIN_PASSWORD are required when the app is writable."
        )
    app.config.update(
        SECRET_KEY=secret_key or secrets.token_hex(32),
        DEMO_MODE=_env_flag("DEMO_MODE", "true"),
        READ_ONLY_DEMO=read_only_demo,
        WEB_ADMIN_USERNAME=os.environ.get("WEB_ADMIN_USERNAME", ""),
        WEB_ADMIN_PASSWORD=os.environ.get("WEB_ADMIN_PASSWORD", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_env_flag(
            "SESSION_COOKIE_SECURE", "true" if is_production else "false"
        ),
    )

    database.init_db()
    if app.config["DEMO_MODE"]:
        _seed_demo_data()

    @app.context_processor
    def inject_template_state():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)
        return {
            "csrf_token": session["_csrf_token"],
            "read_only_demo": app.config["READ_ONLY_DEMO"],
            "admin_signed_in": bool(session.get("admin_user")),
        }

    def validate_csrf():
        submitted = request.form.get("csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not expected or not hmac.compare_digest(submitted, expected):
            abort(400, description="The form expired. Reload the page and try again.")

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if app.config["READ_ONLY_DEMO"]:
                abort(403)
            if not session.get("admin_user"):
                return redirect(url_for("login", next=request.path))
            validate_csrf()
            return view(*args, **kwargs)

        return wrapped

    @app.get("/healthz")
    def health_check():
        _query("SELECT 1")
        return {"status": "ok"}

    @app.get("/")
    def dashboard():
        summary = backend.get_school_revenue_summary()
        students = backend.get_ledger_summary()
        recent_payments = _query(
            """
            SELECT p.payment_id, p.amount_paid, p.date_paid, p.term_name,
                   p.payment_method, p.paid_by, s.student_id, s.full_name
            FROM payments p
            JOIN students s ON s.student_id = p.student_id
            ORDER BY p.payment_id DESC
            LIMIT 6
            """
        )
        return render_template(
            "dashboard.html",
            summary=summary,
            student_count=len(students),
            students=students[:6],
            recent_payments=recent_payments,
        )

    @app.get("/students")
    def students():
        query = request.args.get("q", "").strip()
        records = backend.get_ledger_summary(query)
        return render_template("students.html", records=records, query=query)

    @app.get("/students/<int:student_id>")
    def student_detail(student_id):
        rows = _query(
            """
            SELECT student_id, full_name, class_grade, term_fees_billed
            FROM students WHERE student_id = ?
            """,
            (student_id,),
        )
        if not rows:
            abort(404)
        student = rows[0]
        history = backend.get_student_payment_history(student_id)
        total_paid = sum(float(payment[2]) for payment in history)
        return render_template(
            "student.html",
            student=student,
            history=history,
            total_paid=total_paid,
            balance=max(0.0, float(student["term_fees_billed"]) - total_paid),
        )

    @app.get("/payments/<int:payment_id>/receipt")
    def payment_receipt(payment_id):
        rows = _query(
            """
            SELECT p.payment_id, p.amount_paid, p.date_paid, p.term_name,
                   p.payment_method, p.paid_by, p.class_grade,
                   s.student_id, s.full_name, s.class_grade AS current_grade,
                   s.term_fees_billed,
                   (SELECT COALESCE(SUM(p2.amount_paid), 0)
                    FROM payments p2 WHERE p2.student_id = s.student_id) AS total_paid
            FROM payments p
            JOIN students s ON s.student_id = p.student_id
            WHERE p.payment_id = ?
            """,
            (payment_id,),
        )
        if not rows:
            abort(404)
        payment = rows[0]
        return render_template(
            "receipt.html",
            payment=payment,
            balance=max(0.0, float(payment["term_fees_billed"]) - float(payment["total_paid"])),
        )

    @app.get("/login")
    def login():
        if app.config["READ_ONLY_DEMO"]:
            abort(404)
        return render_template("login.html")

    @app.post("/login")
    def login_submit():
        if app.config["READ_ONLY_DEMO"]:
            abort(404)
        validate_csrf()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        expected_username = app.config["WEB_ADMIN_USERNAME"]
        expected_password = app.config["WEB_ADMIN_PASSWORD"]
        valid = (
            bool(expected_username and expected_password)
            and hmac.compare_digest(username, expected_username)
            and hmac.compare_digest(password, expected_password)
        )
        if not valid:
            flash("Sign-in failed. Check your username and password.", "error")
            return redirect(url_for("login"))

        session.clear()
        session["admin_user"] = expected_username
        session["_csrf_token"] = secrets.token_urlsafe(32)
        target = request.args.get("next", "")
        if not target.startswith("/") or target.startswith("//"):
            target = url_for("dashboard")
        return redirect(target)

    @app.post("/logout")
    def logout():
        validate_csrf()
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("dashboard"))

    @app.post("/students/add")
    @admin_required
    def add_student():
        try:
            backend.register_student(
                request.form.get("full_name"),
                request.form.get("class_grade"),
                request.form.get("term_fees_billed"),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("students"))
        flash("Student added.", "success")
        return redirect(url_for("students"))

    @app.post("/students/<int:student_id>/edit")
    @admin_required
    def edit_student(student_id):
        try:
            changed = backend.update_student_record(
                student_id,
                request.form.get("full_name"),
                request.form.get("class_grade"),
                request.form.get("term_fees_billed"),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("student_detail", student_id=student_id))
        if not changed:
            abort(404)
        flash("Student details updated.", "success")
        return redirect(url_for("student_detail", student_id=student_id))

    @app.post("/students/<int:student_id>/payments/add")
    @admin_required
    def add_payment(student_id):
        student_rows = _query(
            "SELECT full_name, class_grade FROM students WHERE student_id = ?",
            (student_id,),
        )
        if not student_rows:
            abort(404)
        student = student_rows[0]
        try:
            payment_id = backend.record_cash_payment(
                student_id,
                request.form.get("amount"),
                request.form.get("term"),
                request.form.get("payment_method"),
                request.form.get("paid_by"),
                student["class_grade"],
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("student_detail", student_id=student_id))
        flash(f"Payment recorded for {student['full_name']}.", "success")
        return redirect(url_for("payment_receipt", payment_id=payment_id))

    @app.post("/students/<int:student_id>/promote")
    @admin_required
    def promote_student(student_id):
        try:
            next_grade = backend.promote_student_to_next_class(student_id)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("student_detail", student_id=student_id))
        flash(f"Student promoted to {next_grade}.", "success")
        return redirect(url_for("student_detail", student_id=student_id))

    @app.post("/students/<int:student_id>/delete")
    @admin_required
    def delete_student(student_id):
        if not backend.delete_student_record(student_id):
            abort(404)
        flash("Student and related payment history deleted.", "success")
        return redirect(url_for("students"))

    @app.post("/students/promote-all")
    @admin_required
    def promote_all_students():
        try:
            count = backend.promote_all_students_to_next_class()
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("students"))
        flash(f"Promoted {count} students.", "success")
        return redirect(url_for("students"))

    return app


app = _create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
