import sqlite3

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for

from app.db import get_db
from app.utils.booking_helpers import BookingValidationError, get_available_room, validate_booking_details
from app.utils.helpers import login_required, role_required

from . import bookings_bp


@bookings_bp.route("/start", methods=["POST"])
@login_required
def start():
    try:
        room_id, checkin, checkout = validate_booking_details(
            request.form.get("room_id"), request.form.get("checkin_date"),
            request.form.get("checkout_date"),
        )
    except BookingValidationError as error:
        return jsonify(success=False, error=str(error)), error.status_code

    role = session.get("role")
    if role == "guest":
        return redirect(url_for("bookings.guest_confirm", room=room_id, checkin=checkin, checkout=checkout))
    if role in ("receptionist", "manager"):
        return redirect(url_for("bookings.staff_start", room=room_id, checkin=checkin, checkout=checkout))
    abort(403)


@bookings_bp.route("/guest-confirm", methods=["GET"])
@role_required("guest")
def guest_confirm():
    try:
        room_id, checkin, checkout = validate_booking_details(
            request.args.get("room"), request.args.get("checkin"), request.args.get("checkout"),
        )
        room = get_available_room(get_db(), room_id, checkin, checkout)
    except BookingValidationError as error:
        flash(str(error), "danger")
        return redirect(url_for("rooms.rooms"))
    return render_template("bookings/guest_confirm.html", room=room, checkin=checkin, checkout=checkout)


@bookings_bp.route("/guest-create", methods=["POST"])
@role_required("guest")
def guest_create():
    try:
        room_id, checkin, checkout = validate_booking_details(
            request.form.get("room_id"), request.form.get("checkin"), request.form.get("checkout"),
        )
    except BookingValidationError as error:
        return jsonify(success=False, error=str(error)), error.status_code

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        # Resolve the guest from the authenticated account, not a submitted ID.
        guest = db.execute("SELECT id FROM guests WHERE user_id = ?", (session["user_id"],)).fetchone()
        if guest is None:
            raise BookingValidationError("Guest profile not found", 403)
        get_available_room(db, room_id, checkin, checkout)
        db.execute(
            """INSERT INTO bookings
               (guest_id, room_id, check_in_date, check_out_date, booking_status)
               VALUES (?, ?, ?, ?, ?)""",
            (guest["id"], room_id, checkin, checkout, "confirmed"),
        )
        db.commit()
        return jsonify(success=True, message="Booking created"), 200
    except BookingValidationError as error:
        db.rollback()
        return jsonify(success=False, error=str(error)), error.status_code
    except sqlite3.Error:
        db.rollback()
        return jsonify(success=False, error="Unable to create the booking"), 500
