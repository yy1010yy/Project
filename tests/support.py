import importlib
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, template_rendered
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash

from app.db import close_db, get_db
from tests.test_database import SCHEMA


class RouteTestCase(unittest.TestCase):
    blueprints = ("auth",)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True, SECRET_KEY="regression-tests-only",
            DATABASE=str(Path(self.directory.name) / "hotel.db"),
        )
        self.app.teardown_appcontext(close_db)
        for name in self.blueprints:
            module = importlib.import_module(f"app.{name}")
            self.app.register_blueprint(getattr(module, f"{name}_bp"))
        if "dashboard" not in self.blueprints:
            self.app.add_url_rule("/", endpoint="dashboard.index", view_func=lambda: "Home")

        # Backend tests isolate route contracts with minimal templates.
        # FrontendTests replaces this loader to exercise the real pages.
        paths = (
            "auth/login.html", "auth/register.html", "auth/change_password.html",
            "rooms/index.html", "bookings/guest_confirm.html",
            "bookings/staff_start.html", "bookings/new_guest.html",
            "bookings/staff_existing_user.html", "bookings/staff_confirm.html",
            "staff/staff.html", "staff/create.html", "staff/edit.html",
            "dashboard/guest.html", "dashboard/receptionist.html", "dashboard/manager.html",
            "errors/error.html",
        )
        self.app.jinja_loader = DictLoader({path: "{{ error or '' }}" for path in paths})
        self.templates = []
        def capture(sender, template, context, **kwargs):
            self.templates.append((template.name, context))
        template_rendered.connect(capture, self.app, weak=False)
        self.addCleanup(template_rendered.disconnect, capture, self.app)

        with self.app.app_context():
            db = get_db()
            db.executescript(SCHEMA.read_text())
            password_hash = generate_password_hash("original-password")
            db.executemany(
                "INSERT INTO users (id, email, username, hashed_password, user_role) VALUES (?, ?, ?, ?, ?)",
                [(1, "guest@example.com", "Guest", password_hash, "guest"),
                 (2, "desk@example.com", "Reception", password_hash, "receptionist"),
                 (3, "manager@example.com", "Manager", password_hash, "manager")],
            )
            # Multi-digit guest IDs catch the original one-item tuple defect.
            db.execute("INSERT INTO guests (id, user_id) VALUES (12, 1)")
            db.executemany("INSERT INTO staff (user_id, employee_id) VALUES (?, ?)",
                           [(2, "REC-001"), (3, "MNR-001")])
            db.execute("UPDATE employee_id_counter SET id_counter = 2 WHERE employee_role IN ('receptionist', 'manager')")
            db.execute("INSERT INTO rooms (id, room_number, room_type, room_price) VALUES (1, 101, 'standard', 150)")
            db.commit()
        self.client = self.app.test_client()
        self.checkin = (date.today() + timedelta(days=2)).isoformat()
        self.checkout = (date.today() + timedelta(days=4)).isoformat()

    def login_as(self, role="guest"):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = {"guest": 1, "receptionist": 2, "manager": 3}[role]
            session["role"] = role
            if role == "guest":
                session["guest_id"] = 12
            else:
                session["staff_id"] = {"receptionist": 1, "manager": 2}[role]

    def booking_url(self, endpoint):
        return f"/bookings/{endpoint}?room=1&checkin={self.checkin}&checkout={self.checkout}"
