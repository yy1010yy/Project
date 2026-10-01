from concurrent.futures import ThreadPoolExecutor

from app.db import get_db
from tests.support import RouteTestCase


class BookingTests(RouteTestCase):
    blueprints = ("auth", "rooms", "bookings")

    def test_start_dispatches_to_the_existing_role_flows(self):
        for role, endpoint in [("guest", "guest-confirm"), ("receptionist", "staff-start"), ("manager", "staff-start")]:
            self.login_as(role)
            response = self.client.post("/bookings/start", data={"room_id": 1, "checkin_date": self.checkin, "checkout_date": self.checkout})
            self.assertIn(f"/bookings/{endpoint}?", response.location)

    def test_guest_creation_and_conflicting_retry(self):
        self.login_as()
        data = {"room_id": 1, "checkin": self.checkin, "checkout": self.checkout}
        self.assertEqual(self.client.post("/bookings/guest-create", data=data).status_code, 200)
        self.assertEqual(self.client.post("/bookings/guest-create", data=data).status_code, 409)
        with self.app.app_context():
            row = get_db().execute("SELECT guest_id, booking_status FROM bookings").fetchone()
            self.assertEqual(tuple(row), (12, "confirmed"))

    def test_simultaneous_submissions_create_only_one_booking(self):
        def submit():
            client = self.app.test_client()
            with client.session_transaction() as session:
                session.update(user_id=1, role="guest", guest_id=12)
            return client.post("/bookings/guest-create", data={
                "room_id": 1, "checkin": self.checkin, "checkout": self.checkout,
            }).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(statuses), [200, 409])

    def test_invalid_confirmation_returns_to_rooms_homepage(self):
        self.login_as()
        self.assertEqual(self.client.get("/bookings/guest-confirm").location, "/rooms/")

    def test_maintenance_room_cannot_be_booked_directly(self):
        self.login_as()
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE rooms SET room_physical_status = 'maintenance' WHERE id = 1")
            db.commit()
        response = self.client.post("/bookings/guest-create", data={"room_id": 1, "checkin": self.checkin, "checkout": self.checkout})
        self.assertEqual(response.status_code, 409)

    def test_existing_guest_get_search_select_confirm_and_create(self):
        self.login_as("receptionist")
        url = self.booking_url("staff-existing")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.templates[-1][1]["guests"], [])
        response = self.client.post(url, data={"action": "search", "query": "gue"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.templates[-1][1]["guests"][0]["id"], 12)
        response = self.client.post(url, data={"action": "select", "guest_id": "12"})
        self.assertIn("/bookings/staff-confirm?", response.location)
        self.assertEqual(self.client.get(response.location).status_code, 200)
        context = self.templates[-1][1]
        self.assertEqual(context["guest"]["email"], "guest@example.com")
        self.assertEqual(context["room_details"]["room_price"], 150)
        response = self.client.post("/bookings/staff-create", data={"room": 1, "checkin": self.checkin, "checkout": self.checkout})
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertNotIn("staff_booking_guest_id", session)

    def test_missing_query_and_missing_guest_are_handled(self):
        self.login_as("receptionist")
        self.assertEqual(self.client.post(self.booking_url("staff-existing"), data={"action": "search"}).status_code, 200)
        response = self.client.get(self.booking_url("staff-confirm"))
        self.assertIn("/bookings/staff-existing?", response.location)

    def test_new_guest_booking_keeps_the_same_selection_flow(self):
        self.login_as("manager")
        response = self.client.post(self.booking_url("staff-start"), data={"guest_type": "new"})
        self.assertIn("/bookings/staff-new?", response.location)
        self.assertEqual(self.client.get(response.location).status_code, 200)
        response = self.client.post("/quick-register", data={"username": "Walk-in Guest", "email": "walkin@example.com"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get(self.booking_url("staff-confirm")).status_code, 200)
        response = self.client.post("/bookings/staff-create", data={"room": 1, "checkin": self.checkin, "checkout": self.checkout})
        self.assertEqual(response.status_code, 200)

    def test_guests_cannot_access_staff_booking_actions(self):
        self.login_as()
        self.assertEqual(self.client.get(self.booking_url("staff-existing")).status_code, 403)
        self.assertEqual(self.client.post("/bookings/staff-create").status_code, 403)
