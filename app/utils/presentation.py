from datetime import date

from flask import session

from app.db import get_db


# Replace filenames and alt text here; templates and room-search JS share this map.
SITE_IMAGES = {
    "courtyard": {"file": "images/courtyard.png", "alt": "A shaded courtyard with timber shutters, cane chairs and tropical plants"},
    "room": {"file": "images/room.png", "alt": "A sample bedroom with ivory linens, timber furnishings and soft window light"},
    "family": {"file": "images/family.png", "alt": "A sample family bedroom with a double bed and a single bed"},
}

ROOM_STORIES = {
    "standard": {"name": "Standard room", "image": "room", "description": "A simple, welcoming space to make your own."},
    "deluxe": {"name": "Deluxe room", "image": "room", "description": "A comfortable retreat for a slower stay."},
    "family": {"name": "Family room", "image": "family", "description": "A place to settle in together."},
    "business suite": {"name": "Business suite", "image": "room", "description": "A quiet base for days away from home."},
}


def site_context():
    user = None
    if session.get("user_id"):
        user = get_db().execute(
            "SELECT username, email FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
    return {"site_images": SITE_IMAGES, "room_stories": ROOM_STORIES, "current_user": user,
            "today": date.today().isoformat()}


def money(value):
    return f"RM {float(value):,.2f}"


def pretty_date(value):
    if not value:
        return "—"
    return date.fromisoformat(str(value)[:10]).strftime("%d %b %Y")


def stay_nights(checkin, checkout):
    return (date.fromisoformat(checkout) - date.fromisoformat(checkin)).days


def reservation_rows(guest_user_id=None):
    query = """SELECT b.*, r.room_number, r.room_type, r.room_price,
                      u.username AS guest_name, u.email AS guest_email
               FROM bookings AS b JOIN rooms AS r ON b.room_id = r.id
               JOIN guests AS g ON b.guest_id = g.id
               JOIN users AS u ON g.user_id = u.id"""
    params = []
    if guest_user_id is not None:
        query += " WHERE g.user_id = ?"
        params.append(guest_user_id)
    query += " ORDER BY b.check_in_date DESC, b.id DESC"
    return get_db().execute(query, params).fetchall()


def staff_dashboard_data():
    reservations = reservation_rows()
    today = date.today().isoformat()
    arrivals = [row for row in reservations if row["check_in_date"] == today
                and row["booking_status"] in ("pending", "confirmed", "checked in")]
    departures = [row for row in reservations if row["check_out_date"] == today
                  and row["booking_status"] in ("confirmed", "checked in", "checked out")]
    return {"reservations": reservations, "arrivals": arrivals, "departures": departures,
            "rooms": get_db().execute("SELECT * FROM rooms ORDER BY room_number").fetchall()}
