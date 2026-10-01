from app.db import get_db
from tests.support import RouteTestCase


class AuthTests(RouteTestCase):
    def test_login_sets_identity_for_guest_and_staff(self):
        for email, role, identity_key in [
            ("guest@example.com", "guest", "guest_id"),
            ("desk@example.com", "receptionist", "staff_id"),
            ("manager@example.com", "manager", "staff_id"),
        ]:
            response = self.client.post("/login", data={"email": email, "password": "original-password"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "/")
            with self.client.session_transaction() as session:
                self.assertEqual(session["role"], role)
                self.assertIn(identity_key, session)

    def test_temporary_password_login_can_reach_change_password(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET must_change_password = 1 WHERE id = 1")
            db.commit()
        response = self.client.post("/login", data={"email": "guest@example.com", "password": "original-password"})
        self.assertEqual(response.location, "/change_password")
        self.assertEqual(self.client.get(response.location).status_code, 200)

    def test_password_confirmation_is_checked_and_new_password_works(self):
        self.login_as()
        response = self.client.post("/change_password", data={
            "current_password": "original-password", "new_password": "replacement-password",
            "confirm_password": "different-password",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"do not match", response.data)
        response = self.client.post("/change_password", data={
            "current_password": "original-password", "new_password": "replacement-password",
            "confirm_password": "replacement-password",
        })
        self.assertEqual(response.location, "/login")
        response = self.client.post("/login", data={"email": "guest@example.com", "password": "replacement-password"})
        self.assertEqual(response.location, "/")

    def test_register_creates_guest_profile_and_rejects_duplicates(self):
        data = {"username": "New Guest", "email": "new@example.com", "password": "secret", "confirm_password": "secret"}
        self.assertEqual(self.client.post("/register", data=data).location, "/login")
        self.assertEqual(self.client.post("/register", data=data).status_code, 409)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM guests").fetchone()[0], 2)

    def test_quick_register_creates_temporary_credentials_and_selects_guest(self):
        self.login_as("receptionist")
        response = self.client.post("/quick-register", data={"username": "New Guest", "email": "new@example.com"})
        self.assertEqual(response.status_code, 201)
        with self.client.session_transaction() as session:
            self.assertEqual(session["staff_booking_guest_id"], response.json["guest_id"])
        response = self.client.post("/login", data={"email": "new@example.com", "password": response.json["temporary_password"]})
        self.assertEqual(response.location, "/change_password")

    def test_deactivated_account_cannot_use_a_protected_route(self):
        self.login_as()
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET is_active = 0 WHERE id = 1")
            db.commit()
        self.assertEqual(self.client.get("/change_password").location, "/login")

    def test_auth_get_pages_name_their_templates(self):
        for path, template in [("/login", "auth/login.html"), ("/register", "auth/register.html")]:
            self.assertEqual(self.client.get(path).status_code, 200)
            self.assertEqual(self.templates[-1][0], template)

    def test_validation_and_bad_credentials_use_distinct_error_statuses(self):
        self.assertEqual(self.client.post("/login", data={"email": "guest@example.com"}).status_code, 400)
        self.assertEqual(self.client.post("/login", data={"email": "guest@example.com", "password": "wrong"}).status_code, 401)
