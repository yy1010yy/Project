"""Local preview only; deliberately independent of the user's app factory."""
import argparse
import secrets
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, render_template, request
from werkzeug.security import generate_password_hash

from app.auth import auth_bp
from app.bookings import bookings_bp
from app.dashboard import dashboard_bp
from app.db import close_db, get_db
from app.rooms import rooms_bp
from app.staff import staff_bp


ROOT = Path(__file__).resolve().parent


def create_preview_app(database_path=None, demo=True):
    app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=None)
    preview_dir = ROOT / ".preview"
    preview_dir.mkdir(exist_ok=True)
    secret_file = preview_dir / "session-key"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32))
    app.config.update(
        SECRET_KEY=secret_file.read_text(),
        DATABASE=str(database_path or preview_dir / "demo.db"),
        TEMPLATES_AUTO_RELOAD=True,
    )
    app.teardown_appcontext(close_db)
    for blueprint in (auth_bp, dashboard_bp, rooms_bp, bookings_bp, staff_bp):
        app.register_blueprint(blueprint)

    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def error_page(error):
        if request.path.startswith("/assets/"):
            return "Not found", error.code
        return render_template("errors/error.html", code=error.code), error.code

    if demo:
        with app.app_context():
            db = get_db()
            db.executescript((ROOT / "app" / "database" / "schema.sql").read_text())
            if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                password = generate_password_hash("courtyard-demo")
                for username, email, role in (("Amira", "guest@example.com", "guest"), ("Reception", "desk@example.com", "receptionist"), ("Manager", "manager@example.com", "manager")):
                    cursor = db.execute("INSERT INTO users (username, email, hashed_password, user_role) VALUES (?, ?, ?, ?)", (username, email, password, role))
                    if role == "guest":
                        db.execute("INSERT INTO guests (user_id) VALUES (?)", (cursor.lastrowid,))
                    else:
                        prefix = "REC" if role == "receptionist" else "MNR"
                        db.execute("INSERT INTO staff (user_id, employee_id) VALUES (?, ?)", (cursor.lastrowid, f"{prefix}-001"))
                db.execute("UPDATE employee_id_counter SET id_counter = 2 WHERE employee_role IN ('receptionist', 'manager')")
                db.executemany("INSERT INTO rooms (room_number, room_type, room_price, room_physical_status) VALUES (?, ?, ?, ?)", [(101, "standard", 180, "clean"), (102, "deluxe", 260, "clean"), (103, "family", 340, "clean"), (104, "business suite", 390, "clean"), (105, "standard", 180, "dirty"), (106, "deluxe", 260, "maintenance")])
                today = date.today()
                db.executemany("INSERT INTO bookings (guest_id, room_id, check_in_date, check_out_date, booking_status) VALUES (1, ?, ?, ?, ?)", [(1, today.isoformat(), (today + timedelta(days=1)).isoformat(), "confirmed"), (2, (today - timedelta(days=2)).isoformat(), today.isoformat(), "checked in"), (3, (today + timedelta(days=5)).isoformat(), (today + timedelta(days=8)).isoformat(), "confirmed")])
                db.commit()
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--database", help="Use an existing database without initializing or seeding it")
    args = parser.parse_args()
    create_preview_app(args.database, demo=not bool(args.database)).run(host="127.0.0.1", port=args.port, debug=False)
