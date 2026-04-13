# AI Appointment Booking Website + Admin Panel

A lightweight Flask application for clinic appointment booking with AI-assisted triage and an admin dashboard.

## Features
- Patient-facing booking form for service/date/time/symptoms.
- Rule-based AI triage (`Low`, `Medium`, `High`) based on symptoms.
- Admin panel to review appointments and update status.
- SQLite persistence with zero external DB setup.

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then open:
- `http://127.0.0.1:5000/` for booking
- `http://127.0.0.1:5000/admin` for admin panel

## Notes
This demo uses heuristic triage rules and should not be used for emergency diagnosis.
