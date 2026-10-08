import sqlite3
import tempfile
import unittest
from pathlib import Path

from flask import abort

from app import create_app
from app.db import get_db


class AppFactoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = {
            "TESTING": True,
            "SECRET_KEY": "factory-tests-only",
            "DATABASE": str(Path(self.directory.name) / "hotel.db"),
            "SESSION_FILE_DIR": str(Path(self.directory.name) / "sessions"),
        }
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def test_home_templates_assets_and_blueprints(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/register").status_code, 200)
        for filename in ("css/site.css", "js/site.js", "images/courtyard.png"):
            with self.subTest(filename=filename):
                response = self.client.get(f"/assets/{filename}")
                self.assertEqual(response.status_code, 200)
                response.close()
        for path in ("/rooms/", "/staff/", "/bookings/staff-start"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.location)

    def test_init_db_preserves_existing_data_and_teardown_closes_connection(self):
        self.assertFalse(Path(self.config["DATABASE"]).exists())
        runner = self.app.test_cli_runner()
        result = runner.invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        with self.app.app_context():
            db = get_db()
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            db.execute("INSERT INTO rooms (room_number, room_type, room_price) VALUES (101, 'standard', 150)")
            db.commit()
        with self.assertRaises(sqlite3.ProgrammingError):
            db.execute("SELECT 1")
        result = runner.invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM rooms").fetchone()[0], 1)
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM employee_id_counter").fetchone()[0], 3)

    def test_registration_login_and_logout_use_server_side_sessions(self):
        result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        response = self.client.post("/register", data={
            "username": "Guest", "email": "guest@example.com",
            "password": "guest-password", "confirm_password": "guest-password",
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.post("/login", data={
            "email": "guest@example.com", "password": "guest-password",
        })
        self.assertEqual(response.status_code, 302)
        # A fresh factory must read the persisted session from the same directory.
        second_client = create_app(self.config).test_client()
        cookie = self.client.get_cookie("session")
        self.assertIsNotNone(cookie)
        second_client.set_cookie("session", cookie.value)
        self.assertEqual(second_client.get("/home/guest").status_code, 200)
        second_client.get("/logout")
        response = second_client.get("/home/guest")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_shared_error_pages(self):
        @self.app.route("/forbidden")
        def forbidden():
            abort(403)

        @self.app.route("/server-error")
        def server_error():
            abort(500)

        for path, code in (("/forbidden", 403), ("/missing", 404), ("/server-error", 500)):
            with self.subTest(code=code):
                response = self.client.get(path)
                self.assertEqual(response.status_code, code)
                self.assertIn(b"<!doctype html>", response.data)

    def test_missing_secret_key_reports_configuration_error(self):
        with self.assertRaisesRegex(RuntimeError, "Set SECRET_KEY"):
            create_app({**self.config, "SECRET_KEY": None})
