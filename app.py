from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "appointments.db"

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"


SERVICES = {
    "General Checkup": 30,
    "Dermatology": 45,
    "Mental Health": 60,
    "Nutrition": 40,
    "Pediatrics": 30,
}


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                service TEXT NOT NULL,
                preferred_date TEXT NOT NULL,
                preferred_time TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                ai_priority TEXT NOT NULL,
                ai_note TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def score_priority(symptoms: str, service: str) -> tuple[str, str]:
    text = symptoms.lower()
    urgent_tokens = ["severe", "pain", "bleeding", "chest", "faint", "suicidal", "emergency"]
    moderate_tokens = ["fever", "rash", "stress", "anxiety", "vomit", "dizzy", "headache"]

    urgent_hits = sum(token in text for token in urgent_tokens)
    moderate_hits = sum(token in text for token in moderate_tokens)

    if "Mental" in service and ("panic" in text or "suicidal" in text):
        return "High", "Behavioral-health urgency detected. Prioritize same-day clinician review."

    if urgent_hits >= 2:
        return "High", "Multiple urgent symptoms detected. Recommend earliest slot and triage call."
    if urgent_hits == 1 or moderate_hits >= 2:
        return "Medium", "Some concerning symptoms detected. Book within 24-48 hours."

    return "Low", "Routine symptoms detected. Next available slot is appropriate."


@app.before_request
def ensure_db() -> None:
    if not DB_PATH.exists():
        init_db()


@app.route("/")
def home() -> str:
    return render_template("index.html", services=SERVICES)


@app.post("/book")
def book() -> Any:
    form = request.form
    required_fields = ["patient_name", "email", "phone", "service", "preferred_date", "preferred_time", "symptoms"]

    if any(not form.get(field, "").strip() for field in required_fields):
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("home"))

    service = form["service"].strip()
    symptoms = form["symptoms"].strip()

    priority, note = score_priority(symptoms, service)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO appointments (
                patient_name, email, phone, service,
                preferred_date, preferred_time, symptoms,
                ai_priority, ai_note, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
            """,
            (
                form["patient_name"].strip(),
                form["email"].strip(),
                form["phone"].strip(),
                service,
                form["preferred_date"].strip(),
                form["preferred_time"].strip(),
                symptoms,
                priority,
                note,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()

    flash(f"Appointment request submitted. AI triage priority: {priority}.", "success")
    return redirect(url_for("home"))


@app.get("/admin")
def admin() -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM appointments ORDER BY ai_priority DESC, preferred_date, preferred_time"
        ).fetchall()

    counts = {"Pending": 0, "Confirmed": 0, "Completed": 0, "Cancelled": 0}
    for row in rows:
        if row["status"] in counts:
            counts[row["status"]] += 1

    return render_template("admin.html", appointments=rows, counts=counts)


@app.post("/admin/update/<int:appointment_id>")
def update_status(appointment_id: int) -> Any:
    new_status = request.form.get("status", "Pending")
    if new_status not in {"Pending", "Confirmed", "Completed", "Cancelled"}:
        flash("Invalid status value.", "error")
        return redirect(url_for("admin"))

    with get_db() as conn:
        conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, appointment_id))
        conn.commit()

    flash(f"Appointment #{appointment_id} updated to {new_status}.", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
