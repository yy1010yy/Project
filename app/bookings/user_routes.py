from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for

from app.db import get_db
from app.utils.helpers import login_required, role_required

from . import bookings_bp

import sqlite3
from datetime import date


@bookings_bp.route("/start", methods=["POST"])
@login_required
def start():

    room_id = request.form.get("room_id")
    checkin = request.form.get("checkin_date")
    checkout = request.form.get("checkout_date")

    if not room_id or not checkin or not checkout:
        return jsonify({"error": "Missing booking information"}), 400

    role = session.get("role")

    if role == "guest":
        return redirect(url_for("bookings.guest_confirm", room=room_id, checkin=checkin, checkout=checkout))
    elif role in ["receptionist", "manager"]:
        return redirect(url_for("bookings.staff_start", room=room_id, checkin=checkin, checkout=checkout))
    else:
        abort(403)


@bookings_bp.route("/guest-confirm", methods=["GET"])
@role_required("guest")
def guest_confirm():

    room_id = request.args.get("room")
    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")

    # makes DB conn
    db = get_db()

    # check for empty fields
    if not room_id or not checkin or not checkout:
        return "error: missing information", 400

    # verify info
    if not room_id or not checkin or not checkout:
        flash("error: Missing information")
        return redirect(url_for("rooms.search"))

    # verify room id and check in out dates
    try:
        room_id = int(room_id)
        checkin_date = date.fromisoformat(checkin)
        checkout_date = date.fromisoformat(checkout)
    except (ValueError, TypeError):
        flash("Invalid data format")
        return redirect(url_for("rooms.search"))

    if checkin_date < date.today():
        flash("Check in cannot be in the past")
        return redirect(url_for("rooms.search"))
    if checkout_date <= checkin_date:
        flash("Check out must be after check in")
        return redirect(url_for("rooms.search"))


    # ensure room exists
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id, )).fetchone()

    if room is None:
        return "error: room not found", 404

    # ensure room is still available
    conflict = db.execute("""
                            SELECT * FROM bookings
                            WHERE room_id = ?
                            AND check_in_date < ?
                            AND check_out_date > ?
                            AND booking_status NOT IN ('checked out', 'cancelled')
                            LIMIT 1
                            """, (room_id, checkout, checkin)).fetchone()

    if conflict:
        flash("Room was just booked by another guest")
        return redirect(url_for("rooms.search"))

    return render_template("bookings/guest_confirm.html", room=room, checkin=checkin, checkout=checkout)


# api route so use jsonify for this
@bookings_bp.route("/guest-create", methods=["POST"])
@role_required("guest")
def guest_create():

    room_id = request.form.get("room_id", type=int)
    checkin = request.form.get("checkin")
    checkout = request.form.get("checkout")

    if not room_id or not checkin or not checkout:
        return jsonify({
            "success": False,
            "error": "Missing information"
            }), 400

    # verify room id, check in and check out dates
    try:
        room_id = int(room_id)
        checkin_date = date.fromisoformat(checkin)
        checkout_date = date.fromisoformat(checkout)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid data format"
            }), 400


    if checkin_date < date.today():
        return jsonify({
            "success": False,
            "error": "Check in cannot be in the past"
            }), 400
    if checkout_date <= checkin_date:
        return jsonify({
            "success": False,
            "error": "Check out must be after check in"
            }), 400


    # verify room exists
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id, )).fetchone()

    if room is None:
        return jsonify({
            "success": False,
            "error": "Room not found"
            }), 400


    db = get_db()
    guest_id = session["guest_id"]


    # handles race condition
    try:
        db.execute("BEGIN IMMEDIATE")

        # verify no conflict or collisions between bookings
        conflict = db.execute("""
                                SELECT * FROM bookings
                                WHERE room_id = ?
                                AND check_in_date < ?
                                AND check_out_date > ?
                                AND booking_status NOT IN ('checked out', 'cancelled')
                                LIMIT 1
                            """, (room_id, checkout, checkin)).fetchone()
        if conflict:
            db.rollback()
            return jsonify({
                "success": False,
                "error": "Room unavailable"
                }), 409

        # no conflict -> create booking
        db.execute("""
                    INSERT INTO bookings
                    (guest_id, room_id, check_in_date, check_out_date, booking_status)
                    VALUES (?, ?, ?, ?, ?)
                    """, (guest_id, room_id, checkin, checkout, "confirmed"))
        # success
        db.commit()
        return jsonify({
            "success": True,
            "message": "Booking created"
            }), 200

    # database error
    except sqlite3.Error:
        db.rollback()
        return jsonify({
            "success": False,
            "error": "An server error occured"
            }), 500
