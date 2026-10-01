from datetime import date


class BookingValidationError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code                                                                                                                                                                                                                                                                          


def validate_booking_details(room_id, checkin, checkout):
    """Return a room ID and canonical ISO dates for the existing booking flow."""
    if not room_id or not checkin or not checkout:
        raise BookingValidationError("Missing booking information")
    try:
        room_id = int(room_id)
        checkin_date = date.fromisoformat(checkin)
        checkout_date = date.fromisoformat(checkout)
        if room_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise BookingValidationError("Invalid room or booking dates") from None
    if checkin_date < date.today():
        raise BookingValidationError("Check in cannot be in the past")
    if checkout_date <= checkin_date:
        raise BookingValidationError("Check out must be after check in")
    return room_id, checkin_date.isoformat(), checkout_date.isoformat()


def get_available_room(db, room_id, checkin, checkout):
    """Recheck room condition and overlapping stays, including inside a transaction."""
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room is None:
        raise BookingValidationError("Room not found", 404)
    if room["room_physical_status"] in ("maintenance", "out of service"):
        raise BookingValidationError("Room unavailable", 409)
    conflict = db.execute(
        """SELECT id FROM bookings
           WHERE room_id = ? AND check_in_date < ? AND check_out_date > ?
           AND booking_status IN ('pending', 'confirmed', 'checked in')
           LIMIT 1""",
        (room_id, checkout, checkin),
    ).fetchone()
    if conflict:
        raise BookingValidationError("Room was just booked by another guest", 409)
    return room


def get_active_guest(db, guest_id):
    return db.execute(
        """SELECT g.id, u.username, u.email FROM guests AS g
           JOIN users AS u ON g.user_id = u.id
           WHERE g.id = ? AND u.user_role = 'guest' AND u.is_active = 1""",
        (guest_id,),
    ).fetchone()
