from app.db import get_db
from tests.support import RouteTestCase


class StaffTests(RouteTestCase):
    blueprints = ("auth", "staff")

    def test_manager_can_list_create_and_edit_staff(self):
        self.login_as("manager")
        self.assertEqual(self.client.get("/staff/").status_code, 200)
        self.assertEqual(self.templates[-1][1]["staff"][0]["role"], "manager")
        response = self.client.post("/staff/create", data={"username": "New Reception", "email": "newdesk@example.com", "role": "receptionist"})
        self.assertEqual(response.status_code, 201)
        employee_id = response.json["employee_id"]
        self.assertEqual(employee_id, "REC-002")
        self.assertEqual(self.client.get(f"/staff/edit/{employee_id}").status_code, 200)
        self.assertEqual(self.client.post(f"/staff/edit/{employee_id}", data={"role": "manager"}).status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT user_role FROM users WHERE email = 'newdesk@example.com'").fetchone()[0], "manager")

    def test_staff_creation_rejects_invalid_email_and_duplicate_username(self):
        self.login_as("manager")
        self.assertEqual(self.client.post("/staff/create", data={"username": "New", "email": "invalid", "role": "manager"}).status_code, 400)
        self.assertEqual(self.client.post("/staff/create", data={"username": "Guest", "email": "other@example.com", "role": "manager"}).status_code, 409)
        self.assertEqual(self.client.post("/staff/edit/REC-001", data={"username": "Guest"}).status_code, 409)

    def test_deactivation_blocks_an_existing_staff_session(self):
        self.login_as("manager")
        staff_client = self.app.test_client()
        staff_client.post("/login", data={"email": "desk@example.com", "password": "original-password"})
        self.assertEqual(self.client.post("/staff/deactivate/REC-001").status_code, 200)
        self.assertEqual(staff_client.get("/change_password").location, "/login")

    def test_role_change_is_applied_to_an_existing_session(self):
        self.login_as("manager")
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET user_role = 'receptionist' WHERE id = 3")
            db.commit()
        self.assertEqual(self.client.get("/staff/").status_code, 403)

    def test_missing_employee_returns_404_and_guest_is_forbidden(self):
        self.login_as("manager")
        self.assertEqual(self.client.post("/staff/edit/missing", data={"username": "New"}).status_code, 404)
        self.login_as()
        self.assertEqual(self.client.get("/staff/").status_code, 403)
