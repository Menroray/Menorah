import math
import os
import re
import sqlite3
from datetime import datetime
from html import escape
from pathlib import Path

from database.database import BACKUP_DIR, BASE_DIR, ClosingConnection, DB_PATH, RECEIPTS_DIR


def _connect_db():
    """Centralize the database connection strategy to reduce drift and maintenance issues."""
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _clean_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def _clean_money(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("GH₵", "").replace(",", "").strip()
    try:
        return float(cleaned or 0.0)
    except ValueError:
        return 0.0


def _validate_required_text(value, field_name):
    cleaned = _clean_text(value)
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _validate_positive_amount(value, field_name):
    amount = _clean_money(value)
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f"{field_name} must be a valid non-negative value.")
    return amount


def _validate_student_id(student_id):
    try:
        student_id = int(student_id)
    except (TypeError, ValueError):
        raise ValueError("Student ID must be a valid integer.")
    if student_id <= 0:
        raise ValueError("Student ID must be greater than zero.")
    return student_id


def create_database_backup(backup_dir=None):
    """Create a timestamped SQLite backup file to protect the school data store."""
    target_dir = Path(backup_dir) if backup_dir else BACKUP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as source_conn:
        source_conn.execute("PRAGMA wal_checkpoint(FULL)")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = target_dir / f"school_fees_backup_{timestamp}.db"

        with sqlite3.connect(str(backup_path)) as backup_conn:
            source_conn.backup(backup_conn)

        return str(backup_path)


def restore_database_from_backup(backup_path):
    """Restore a current database file from a saved backup copy."""
    source = Path(backup_path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Backup file not found: {source}")

    with sqlite3.connect(str(source)) as source_conn:
        with sqlite3.connect(DB_PATH) as target_conn:
            source_conn.backup(target_conn)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")

    return True


def list_database_backups(backup_dir=None):
    """Return all known database backup files, newest first."""
    target_dir = Path(backup_dir) if backup_dir else BACKUP_DIR
    if not target_dir.exists():
        return []
    backups = sorted(target_dir.glob("*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
    return [str(path) for path in backups]


# ========================================================
# ADMIN VALIDATION UTILITIES
# ========================================================
def verify_admin_login(username, password):
    """Verifies user credentials against the secure data store."""
    username = _clean_text(username)
    password = _clean_text(password)
    if not username or not password:
        return False

    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM admin_users WHERE username = ? AND password = ?",
            (username, password),
        )
        return cursor.fetchone() is not None


def change_admin_password(username, current_password, new_password):
    """Updates an admin password after verifying the current credentials."""
    username = _clean_text(username)
    current_password = _clean_text(current_password)
    new_password = _clean_text(new_password)

    if not username or not current_password or not new_password:
        return False, "All fields are required."

    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT admin_id FROM admin_users WHERE username = ? AND password = ?",
            (username, current_password),
        )
        if cursor.fetchone() is None:
            return False, "Current password is incorrect."

        cursor.execute(
            "UPDATE admin_users SET password = ? WHERE username = ? AND password = ?",
            (new_password, username, current_password),
        )
        conn.commit()
    return True, "Password updated successfully."

# ========================================================
# C - CREATE LOG ENGINE
# ========================================================
def register_student(name, grade, bill):
    cleaned_name = _validate_required_text(name, "Student name")
    cleaned_grade = _validate_required_text(grade, "Class/grade")
    amount = _validate_positive_amount(bill, "Term billed amount")

    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (full_name, class_grade, term_fees_billed) VALUES (?, ?, ?)",
            (cleaned_name, cleaned_grade, amount),
        )
        conn.commit()
        return cursor.lastrowid

def find_student_by_name(student_name):
    if not student_name:
        return None

    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT student_id, full_name, class_grade, term_fees_billed FROM students WHERE LOWER(full_name) LIKE LOWER(?) ORDER BY student_id LIMIT 1",
            (f"%{student_name.strip()}%",),
        )
        student = cursor.fetchone()

    return None if student is None else {
        "student_id": student[0],
        "full_name": student[1],
        "class_grade": student[2],
        "term_fees_billed": student[3],
    }


def record_cash_payment(student_id, amount, term, payment_method="Cash", paid_by="", class_grade=""):
    valid_student_id = _validate_student_id(student_id)
    amount_value = _validate_positive_amount(amount, "Payment amount")
    term_name = _validate_required_text(term, "Payment term")
    payment_method_name = (payment_method or "Cash").strip() or "Cash"
    paid_by_name = (paid_by or "").strip()
    class_name = (class_grade or "").strip()

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO payments (student_id, amount_paid, date_paid, term_name, payment_method, paid_by, class_grade) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                valid_student_id,
                amount_value,
                date_str,
                term_name,
                payment_method_name,
                paid_by_name,
                class_name,
            ),
        )
        conn.commit()
        return cursor.lastrowid

# ========================================================
# R - READ DATA MATRICES
# ========================================================
def get_ledger_summary(search_query=""):
    with _connect_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                s.student_id, s.full_name, s.class_grade, s.term_fees_billed,
                IFNULL(SUM(p.amount_paid), 0.0) as total_paid
            FROM students s
            LEFT JOIN payments p ON s.student_id = p.student_id
            WHERE
                s.full_name LIKE ? OR
                s.class_grade LIKE ? OR
                EXISTS (
                    SELECT 1 FROM payments p2
                    WHERE p2.student_id = s.student_id AND (
                        p2.term_name LIKE ? OR
                        CAST(p2.amount_paid AS TEXT) LIKE ? OR
                        p2.date_paid LIKE ?
                    )
                )
            GROUP BY s.student_id
        """
        filter_val = f"%{search_query}%"
        cursor.execute(query, (filter_val, filter_val, filter_val, filter_val, filter_val))
        rows = cursor.fetchall()

    processed = []
    for row in rows:
        s_id, name, grade, billed, paid = row
        owing = billed - paid
        status = "Fully Paid ✅" if owing <= 0 else "Owing"
        processed.append((s_id, name, grade, f"GH₵{billed:.2f}", f"GH₵{paid:.2f}", f"GH₵{max(0.0, owing):.2f}", status))

    search_value = (search_query or "").strip().lower()
    if search_value:
        processed = [
            record for record in processed
            if any(search_value in str(value).lower() for value in record)
        ]

    return processed

def get_student_payment_history(student_id):
    valid_student_id = _validate_student_id(student_id)
    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT payment_id, term_name, amount_paid, date_paid, payment_method, paid_by FROM payments WHERE student_id = ? ORDER BY payment_id DESC",
            (valid_student_id,),
        )
        rows = cursor.fetchall()
    return rows


def get_school_revenue_summary():
    with _connect_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                IFNULL(SUM(s.term_fees_billed), 0.0) as overall_billed,
                IFNULL((SELECT SUM(amount_paid) FROM payments), 0.0) as overall_collected
            FROM students s
        """
        cursor.execute(query)
        overall_billed, overall_collected = cursor.fetchone()

    overall_owing = overall_billed - overall_collected
    return {
        "billed": f"GH₵{overall_billed:,.2f}",
        "collected": f"GH₵{overall_collected:,.2f}",
        "owing": f"GH₵{max(0.0, overall_owing):,.2f}"
    }

# ========================================================
# U - UPDATE METHODS
# ========================================================
def update_student_record(student_id, name, grade, bill):
    valid_student_id = _validate_student_id(student_id)
    cleaned_name = _validate_required_text(name, "Student name")
    cleaned_grade = _validate_required_text(grade, "Class/grade")
    amount = _validate_positive_amount(bill, "Updated bill amount")

    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET full_name = ?, class_grade = ?, term_fees_billed = ? WHERE student_id = ?",
            (cleaned_name, cleaned_grade, amount, valid_student_id),
        )
        conn.commit()
        return cursor.rowcount


def _next_class_label(class_label):
    """Moves a class like 'Grade 3' or 'Form 2' to the next level."""
    label = (class_label or "").strip()
    if not label:
        raise ValueError("Student class cannot be empty.")

    match = re.search(r"(\d+)", label)
    if not match:
        raise ValueError(f"Class '{label}' cannot be promoted automatically. Use a numbered class like Grade 3 or Form 2.")

    next_number = int(match.group(1)) + 1
    return re.sub(r"\d+", str(next_number), label, count=1)


def promote_all_students_to_next_class():
    """Moves every student record to the next class/grade in the system."""
    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, class_grade FROM students")
        students = cursor.fetchall()

        updated = 0
        for student_id, class_grade in students:
            next_grade = _next_class_label(class_grade)
            cursor.execute(
                "UPDATE students SET class_grade = ? WHERE student_id = ?",
                (next_grade, int(student_id)),
            )
            updated += 1

        conn.commit()
        return updated


def promote_student_to_next_class(student_id):
    """Moves one student record to the next class/grade in the system."""
    valid_student_id = _validate_student_id(student_id)
    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT class_grade FROM students WHERE student_id = ?", (valid_student_id,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError("Selected student was not found.")

        next_grade = _next_class_label(row[0])
        cursor.execute(
            "UPDATE students SET class_grade = ? WHERE student_id = ?",
            (next_grade, valid_student_id),
        )
        conn.commit()
        return next_grade

# ========================================================
# D - DELETE INSTANCES
# ========================================================
def delete_student_record(student_id):
    valid_student_id = _validate_student_id(student_id)
    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE student_id = ?", (valid_student_id,))
        conn.commit()
        return cursor.rowcount

# ========================================================
# RECEIPT EXPORT MANAGEMENT
# ========================================================
def generate_receipt_file(student_id, student_name, class_grade, amount, term, payment_method="Cash", paid_by=""):
    valid_student_id = _validate_student_id(student_id)
    student_name = _validate_required_text(student_name, "Student name")
    class_grade = _validate_required_text(class_grade, "Class/grade")
    amount_value = _validate_positive_amount(amount, "Receipt amount")
    term_name = _validate_required_text(term, "Payment term")

    receipt_dir = os.path.join(BASE_DIR, "receipts")
    if not os.path.exists(receipt_dir):
        os.makedirs(receipt_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(receipt_dir, f"Receipt_{valid_student_id}_{timestamp}.html")
    txt_path = os.path.join(receipt_dir, f"Receipt_{valid_student_id}_{timestamp}.txt")

    with _connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.term_fees_billed, IFNULL(SUM(p.amount_paid), 0.0)
            FROM students s LEFT JOIN payments p ON s.student_id = p.student_id WHERE s.student_id = ?
        """, (valid_student_id,))
        row = cursor.fetchone()
    if row is None:
        raise ValueError("Selected student was not found.")
    billed, total_paid = row

    billed = float(billed or 0.0)
    total_paid = float(total_paid or 0.0)
    owing = billed - total_paid
    status = "Fully Paid ✅" if owing <= 0 else "Balance Owing"
    payment_method = (payment_method or "Cash").strip() or "Cash"
    paid_by = (paid_by or "").strip()
    class_grade = (class_grade or "").strip() or "N/A"
    issue_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    amount_display = float(amount_value)

    summary_lines = [
        "=========================================",
        "          SCHOOL FEES CASH RECEIPT        ",
        "=========================================",
        f"Date/Time:      {issue_date}",
        f"Student ID:     {student_id}",
        f"Student Name:   {student_name}",
        f"Class/Grade:    {class_grade}",
        f"Payment Method: {payment_method}",
    ]
    if paid_by:
        summary_lines.append(f"Paid By:        {paid_by}")
    summary_lines.extend([
        "-----------------------------------------",
        f"Term Targeted:  {term_name}",
        f"Amount Paid:    GH₵{amount_display:.2f} ({payment_method.upper()})",
        "-----------------------------------------",
        f"Total Term Bill: GH₵{billed:.2f}",
        f"Total Paid:      GH₵{total_paid:.2f}",
        f"Current Balance: GH₵{max(0.0, owing):.2f} ({status})",
        "=========================================",
        "       Thank you for your payment!       ",
        "=========================================",
    ])

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    html_lines = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "<meta charset=\"UTF-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        "<title>School Fees Receipt</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; background: #f3f4f6; margin: 0; padding: 32px; color: #111827; }",
        ".receipt { max-width: 760px; margin: 0 auto; background: #ffffff; border: 2px solid #d1d5db; border-radius: 16px; padding: 24px; box-shadow: 0 12px 30px rgba(17, 24, 39, 0.08); }",
        ".header { text-align: center; border-bottom: 2px solid #111827; padding-bottom: 16px; margin-bottom: 18px; }",
        ".header h1 { margin: 0; font-size: 28px; letter-spacing: 1px; }",
        ".meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 20px; margin: 14px 0; font-size: 14px; }",
        ".label { font-weight: bold; color: #374151; }",
        ".summary { margin-top: 20px; border-top: 2px solid #e5e7eb; padding-top: 16px; }",
        ".row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 15px; }",
        ".footer { text-align: center; margin-top: 22px; font-weight: bold; font-size: 15px; color: #111827; }",
        "@media print { body { background: #ffffff; padding: 0; } .receipt { box-shadow: none; border: none; border-radius: 0; max-width: 100%; } }",
        "</style>",
        "</head>",
        "<body>",
        f"<div class=\"receipt\">",
        "<div class=\"header\">",
        "<h1>School Fees Cash Receipt</h1>",
        "</div>",
        "<div class=\"meta\">",
        f"<div><span class=\"label\">Date/Time:</span> {escape(issue_date)}</div>",
        f"<div><span class=\"label\">Student ID:</span> {escape(str(student_id))}</div>",
        f"<div><span class=\"label\">Student Name:</span> {escape(student_name)}</div>",
        f"<div><span class=\"label\">Class/Grade:</span> {escape(class_grade)}</div>",
        f"<div><span class=\"label\">Payment Method:</span> {escape(payment_method)}</div>",
        f"<div><span class=\"label\">Paid By:</span> {escape(paid_by or 'N/A')}</div>",
        "</div>",
        "<div class=\"summary\">",
        f"<div class=\"row\"><span>Term</span><span>{escape(term_name)}</span></div>",
        f"<div class=\"row\"><span>Amount Paid</span><span>GH₵{amount_display:.2f}</span></div>",
        f"<div class=\"row\"><span>Total Term Bill</span><span>GH₵{billed:.2f}</span></div>",
        f"<div class=\"row\"><span>Total Paid</span><span>GH₵{total_paid:.2f}</span></div>",
        f"<div class=\"row\"><span>Current Balance</span><span>GH₵{max(0.0, owing):.2f}</span></div>",
        f"<div class=\"row\"><span>Status</span><span>{escape(status)}</span></div>",
        "</div>",
        "<div class=\"footer\">Thank you for your payment!</div>",
        "</div>",
        "</body>",
        "</html>",
    ]
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    return html_path
