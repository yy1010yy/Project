import sqlite3
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from app.db import close_db, get_db


SCHEMA = Path(__file__).resolve().parents[1] / "app" / "database" / "schema.sql"


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = Flask(__name__)
        self.app.config["DATABASE"] = str(Path(self.directory.name) / "hotel.db")
        self.app.teardown_appcontext(close_db)

    def test_schema_can_be_initialized_twice_without_resetting_counters(self):
        with self.app.app_context():
            db = get_db()
            db.executescript(SCHEMA.read_text())
            db.execute("UPDATE employee_id_counter SET id_counter = 7 WHERE employee_role = 'manager'")
            db.commit()
            db.executescript(SCHEMA.read_text())
            self.assertEqual(db.execute("SELECT id_counter FROM employee_id_counter WHERE employee_role = 'manager'").fetchone()[0], 7)

    def test_schema_enforces_email_role_and_foreign_keys(self):
        with self.app.app_context():
            db = get_db()
            db.executescript(SCHEMA.read_text())
            for email, role in [("invalid", "guest"), ("guest@example.com", "invalid")]:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute("INSERT INTO users (email, username, hashed_password, user_role) VALUES (?, ?, ?, ?)", (email, "Guest", "hash", role))
                db.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO guests (user_id) VALUES (999)")

    def test_connection_is_reused_and_closed_at_context_exit(self):
        with self.app.app_context():
            db = get_db()
            self.assertIs(db, get_db())
        with self.assertRaises(sqlite3.ProgrammingError):
            db.execute("SELECT 1")
