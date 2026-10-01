import sqlite3

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from app.db import get_db
from app.utils.booking_helpers import BookingValidationError, get_active_guest, get_available_room, validate_booking_details
from app.utils.helpers import role_required

from . import bookings_bp


ALLOWED_GUEST_TYPES = ["existing", "new"]


def _booking_from_query():
    return validate_booking_details(
        request.args.get("room"), request.args.get("checkin"), request.args.get("checkout"),
    )


@bookings_bp.route("/staff-start", methods=["GET", "POST"])
@role_required("receptionist", "manager")
def staff_start():
    try:
        room_id, checkin, checkout = _booking_from_query()
        get_available_room(get_db(), room_id, checkin, checkout)
    except BookingValidationError as error:
        flash(str(error), "danger")
        return redirect(url_for("rooms.rooms"))

    if request.method == "POST":
        guest_type = request.form.get("guest_type")
        if guest_type not in ALLOWED_GUEST_TYPES:
            flash("Choose an existing guest or a new guest", "danger")
            return redirect(url_for("bookings.staff_start", room=room_id, checkin=checkin, checkout=checkout))
        session.pop("staff_booking_guest_id", None)
        endpoint = "bookings.staff_existing_guest" if guest_type == "existing" else "bookings.staff_new_guest"
        return redirect(url_for(endpoint, room=room_id, checkin=checkin, checkout=checkout))
    return render_template("bookings/staff_start.html", room=room_id, checkin=checkin, checkout=checkout)


@bookings_bp.route("/staff-new", methods=["GET"])
@role_required("receptionist", "manager")
def staff_new_guest():
    try:
        room_id, checkin, checkout = _booking_from_query()
        get_available_room(get_db(), room_id, checkin, checkout)
    except BookingValidationError as error:
        flash(str(error), "danger")
        return redirect(url_for("rooms.rooms"))
    return render_template("bookings/new_guest.html", room=room_id, checkin=checkin, checkout=checkout)


@bookings_bp.route("/staff-existing", methods=["GET", "POST"])
@role_required("receptionist", "manager")
def staff_existing_guest():
    try:
        room_id, checkin, checkout = _booking_from_query()
        get_available_room(get_db(), room_id, checkin, checkout)
    except BookingValidationError as error:
        flash(str(error), "danger")
        return redirect(url_for("rooms.rooms"))

    guests = []
    query = ""
    if request.method == "POST":
        db = get_db()
        action = request.form.get("action")
        if action == "search":
            query = request.form.get("query", "").strip()
            if not query:
                flash("Please enter an email or username", "danger")
            else:
                # Treat SQL wildcard characters as literal search text.
                pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
                guests = db.execute(
                    """SELECT g.id, u.username, u.email
                       FROM guests AS g JOIN users AS u ON g.user_id = u.id
                       WHERE u.user_role = 'guest' AND u.is_active = 1
                       AND (u.email LIKE ? ESCAPE '\\' OR u.username LIKE ? ESCAPE '\\')
                       ORDER BY u.username LIMIT 20""",
                    (pattern, pattern),
                ).fetchall()
                if not guests:
                    flash("No guest found", "info")
        elif action == "select":
            guest_id = request.form.get("guest_id", type=int)
            guest = get_active_guest(db, guest_id) if guest_id else None
            if guest is None:
                flash("Select an active guest", "danger")
                return redirect(url_for("bookings.staff_existing_guest", room=room_id, checkin=checkin, checkout=checkout))
            session["staff_booking_guest_id"] = guest["id"]
            return redirect(url_for("bookings.staff_confirm", room=room_id, checkin=checkin, checkout=checkout))
        else:
            flash("Choose search or select", "danger")
    return render_template(
        "bookings/staff_existing_user.html", guests=guests, query=query,
        room=room_id, checkin=checkin, checkout=checkout,
    )


@bookings_bp.route("/staff-confirm", methods=["GET"])
@role_required("receptionist", "manager")
def staff_confirm():
    try:
        room_id, checkin, checkout = _booking_from_query()
        room = get_available_room(get_db(), room_id, checkin, checkout)
    except BookingValidationError as error:
        flash(str(error), "danger")
        return redirect(url_for("rooms.rooms"))

    guest = get_active_guest(get_db(), session.get("staff_booking_guest_id"))
    if guest is None:
        session.pop("staff_booking_guest_id", None)
        flash("Select an active guest before confirming", "danger")
        return redirect(url_for("bookings.staff_existing_guest", room=room_id, checkin=checkin, checkout=checkout))
    return render_template(
        "bookings/staff_confirm.html", room=room_id, room_details=room,
        checkin=checkin, checkout=checkout, guest=dict(guest),
    )


@bookings_bp.route("/staff-create", methods=["POST"])
@role_required("receptionist", "manager")
def staff_create():
    try:
        room_id, checkin, checkout = validate_booking_details(
            request.form.get("room"), request.form.get("checkin"), request.form.get("checkout"),
        )
    except BookingValidationError as error:
        return jsonify(success=False, error=str(error)), error.status_code

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        guest_id = session.get("staff_booking_guest_id")
        if get_active_guest(db, guest_id) is None:
            session.pop("staff_booking_guest_id", None)
            raise BookingValidationError("Select an active guest")
        get_available_room(db, room_id, checkin, checkout)
        db.execute(
            """INSERT INTO bookings
               (guest_id, room_id, check_in_date, check_out_date, booking_status)
               VALUES (?, ?, ?, ?, ?)""",
            (guest_id, room_id, checkin, checkout, "confirmed"),
        )
        db.commit()
        session.pop("staff_booking_guest_id", None)
        return jsonify(success=True, message="Booking created"), 200
    except BookingValidationError as error:
        db.rollback()
        return jsonify(success=False, error=str(error)), error.status_code
    except sqlite3.Error:
        db.rollback()
        return jsonify(success=False, error="Unable to create the booking"), 500
