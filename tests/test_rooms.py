from app.db import get_db
from tests.support import RouteTestCase


class RoomTests(RouteTestCase):
    blueprints = ("auth", "rooms")

    def test_rooms_require_login_and_render_the_homepage(self):
        self.assertEqual(self.client.get("/rooms/").location, "/login")
        self.login_as()
        self.assertEqual(self.client.get("/rooms/").status_code, 200)
        self.assertEqual(self.templates[-1][0], "rooms/index.html")

    def test_search_excludes_conflicts_but_allows_adjacent_stays(self):
        self.login_as()
        with self.app.app_context():
            db = get_db()
            db.execute("INSERT INTO bookings (guest_id, room_id, check_in_date, check_out_date, booking_status) VALUES (12, 1, ?, ?, 'confirmed')", (self.checkin, self.checkout))
            db.commit()
        query = {"check_in": self.checkin, "check_out": self.checkout}
        self.assertEqual(self.client.get("/rooms/search", query_string=query).json["rooms"], [])
        compact_query = {key: value.replace("-", "") for key, value in query.items()}
        self.assertEqual(self.client.get("/rooms/search", query_string=compact_query).json["rooms"], [])
        query = {"check_in": self.checkout, "check_out": "2099-12-31"}
        self.assertEqual(len(self.client.get("/rooms/search", query_string=query).json["rooms"]), 1)

    def test_add_uses_schema_values_and_returns_success(self):
        self.login_as("manager")
        response = self.client.post("/rooms/add", data={"room_number": "102", "room_status": "out of service", "room_type": "business suite", "room_price": "225.50"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json["success"])
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT room_type FROM rooms WHERE room_number = 102").fetchone()[0], "business suite")

    def test_price_update_saves_a_number_and_rejects_nonfinite_values(self):
        self.login_as("receptionist")
        self.assertEqual(self.client.post("/rooms/edit/1", data={"room_price": "199.50"}).status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT room_price FROM rooms WHERE id = 1").fetchone()[0], 199.5)
        for price in ("nan", "inf", "-1"):
            self.assertEqual(self.client.post("/rooms/edit/1", data={"room_price": price}).status_code, 400)

    def test_search_validation_returns_json_and_guests_cannot_edit_rooms(self):
        self.login_as()
        response = self.client.get("/rooms/search")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json["success"])
        self.assertEqual(self.client.post("/rooms/edit/1", data={"room_price": "1"}).status_code, 403)

    def test_temporary_password_cannot_bypass_the_change_page(self):
        self.login_as()
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET must_change_password = 1 WHERE id = 1")
            db.commit()
        self.assertEqual(self.client.get("/rooms/").location, "/change_password")
