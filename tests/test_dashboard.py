from tests.support import RouteTestCase


class DashboardTests(RouteTestCase):
    blueprints = ("auth", "dashboard")

    def test_login_reaches_the_existing_role_homepage(self):
        for email, role in [("guest@example.com", "guest"), ("desk@example.com", "receptionist"), ("manager@example.com", "manager")]:
            response = self.client.post("/login", data={"email": email, "password": "original-password"}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.request.path, f"/home/{role}")
            self.assertEqual(self.templates[-1][0], f"dashboard/{role}.html")

    def test_other_roles_cannot_enter_guest_dashboard(self):
        self.login_as("manager")
        self.assertEqual(self.client.get("/home/guest").status_code, 403)
