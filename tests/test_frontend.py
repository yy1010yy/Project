from datetime import date, timedelta
from pathlib import Path

from jinja2 import FileSystemLoader

from app.db import get_db
from app.utils.presentation import SITE_IMAGES
from tests.support import RouteTestCase


ROOT = Path(__file__).resolve().parents[1]


class FrontendTests(RouteTestCase):
    """Render the real templates against an isolated database."""

    blueprints = ("auth", "dashboard", "rooms", "bookings", "staff")

    def setUp(self):
        super().setUp()
        self.app.jinja_loader = FileSystemLoader(ROOT / "templates")

    def test_public_home_and_local_assets(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A quieter kind", response.data)
        self.assertIn(b'lang="en-MY"', response.data)
        self.assertNotIn(b"cdn.tailwindcss", response.data)
        for filename in ("css/site.css", "js/site.js", *[image["file"] for image in SITE_IMAGES.values()]):
            with self.subTest(filename=filename):
                asset = self.client.get(f"/assets/{filename}")
                self.assertEqual(asset.status_code, 200)
                asset.close()
        self.assertIn("/login", self.client.get("/rooms/").location)

    def test_authentication_errors_keep_email_without_password(self):
        for path in ("/login", "/register"):
            self.assertEqual(self.client.get(path).status_code, 200)
        response = self.client.post("/login", data={"email": "guest@example.com", "password": "wrong-secret"})
        self.assertEqual(response.status_code, 401)
        self.assertIn(b'role="alert"', response.data)
        self.assertIn(b'guest@example.com', response.data)
        self.assertNotIn(b"wrong-secret", response.data)
        self.login_as()
        response = self.client.post("/change_password", data={
            "current_password": "incorrect", "new_password": "new-password", "confirm_password": "new-password",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Current password is incorrect", response.data)

    def test_guest_reservations_are_scoped_to_the_signed_in_guest(self):
        with self.app.app_context():
            db = get_db()
            db.execute("INSERT INTO users (id, username, email, hashed_password, user_role) VALUES (4, 'Other Guest', 'other@example.com', 'unused', 'guest')")
            db.execute("INSERT INTO guests (id, user_id) VALUES (13, 4)")
            db.executemany(
                "INSERT INTO bookings (guest_id, room_id, check_in_date, check_out_date, booking_status) VALUES (?, 1, ?, ?, 'confirmed')",
                [(12, self.checkin, self.checkout), (13, "2030-11-11", "2030-11-12")],
            )
            db.commit()
        self.login_as()
        response = self.client.get("/home/guest")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Room 101", response.data)
        self.assertNotIn(b"11 Nov 2030", response.data)
        self.assertNotIn(b"other@example.com", response.data)

    def test_guest_booking_review_and_creation_use_existing_routes(self):
        self.login_as()
        self.assertEqual(self.client.get("/rooms/").status_code, 200)
        response = self.client.get(self.booking_url("guest-confirm"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RM 300.00", response.data)
        self.assertIn(b'/bookings/guest-create', response.data)
        response = self.client.post("/bookings/guest-create", data={"room_id": 1, "checkin": self.checkin, "checkout": self.checkout})
        self.assertTrue(response.json["success"])
        self.assertEqual(self.client.get("/home/guest").status_code, 200)
        self.assertEqual(len(self.templates[-1][1]["reservations"]), 1)

    def test_staff_ledgers_use_live_dates_and_do_not_add_status_actions(self):
        today = date.today()
        with self.app.app_context():
            db = get_db()
            db.executemany(
                "INSERT INTO bookings (guest_id, room_id, check_in_date, check_out_date, booking_status) VALUES (12, 1, ?, ?, ?)",
                [(today.isoformat(), (today + timedelta(days=1)).isoformat(), "confirmed"),
                 ((today - timedelta(days=2)).isoformat(), today.isoformat(), "checked in"),
                 (today.isoformat(), (today + timedelta(days=2)).isoformat(), "cancelled")],
            )
            db.commit()
        for role in ("receptionist", "manager"):
            self.login_as(role)
            response = self.client.get(f"/home/{role}")
            self.assertEqual(response.status_code, 200)
            context = self.templates[-1][1]
            self.assertEqual(len(context["arrivals"]), 1)
            self.assertEqual(len(context["departures"]), 1)
            self.assertEqual(len(context["reservations"]), 3)
            self.assertNotIn(b'<form', response.data)

    def test_staff_existing_and_new_guest_pages(self):
        self.login_as("receptionist")
        for endpoint in ("staff-start", "staff-new", "staff-existing"):
            self.assertEqual(self.client.get(self.booking_url(endpoint)).status_code, 200)
        response = self.client.post(self.booking_url("staff-existing"), data={"action": "search", "query": "Guest"})
        self.assertIn(b"Select Guest", response.data)
        response = self.client.post(self.booking_url("staff-existing"), data={"action": "select", "guest_id": 12})
        review = self.client.get(response.location)
        self.assertEqual(review.status_code, 200)
        self.assertIn(b"RM 300.00", review.data)
        self.assertIn(b"guest@example.com", review.data)

    def test_manager_team_pages_and_guest_permission_error(self):
        self.login_as("manager")
        for path in ("/staff/", "/staff/create", "/staff/edit/REC-001"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.login_as()
        response = self.client.get("/staff/")
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"<!doctype html>", response.data)
        self.assertEqual(self.client.get("/does-not-exist").status_code, 404)

    def test_inventory_is_staff_only_and_password_change_gate_is_preserved(self):
        self.login_as("manager")
        self.assertIn(b"Edit room 101", self.client.get("/rooms/").data)
        self.login_as()
        self.assertNotIn(b"Edit room 101", self.client.get("/rooms/").data)
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET must_change_password = 1 WHERE id = 1")
            db.commit()
        self.assertIn("/change_password", self.client.get("/").location)
