from flask import flash, jsonify, request

from app.db import get_db
from app.utils.helpers import login_required, role_required

from . import rooms_bp

from datetime import date
import sqlite3


ALLOWED_STATUSES = ["clean", "dirty", "maintenance", "outofservice"]
ALLOWED_TYPES = ["standard", "deluxe", "family", "businesssuite"]

@rooms_bp.route("/")
@login_required
def rooms():

    # homepage to search for rooms



@rooms_bp.route("/search", methods=["GET"])
@login_required
def search_roooms():

    # get details from guest's search
    room_type = request.args.get("roomType")
    requested_check_in_date = request.args.get("check_in")
    requested_check_out_date = request.args.get("check_out")

    # check if dates are provided
    if not requested_check_in_date or not requested_check_out_date:
        return "error: please provide check in and check out dates", 400

    # convert dates into python objects for comparison
    try:
        checkin_date = date.fromisoformat(requested_check_in_date)
        checkout_date = date.fromisoformat(requested_check_out_date)
    except ValueError:
        return "error: invalid date", 400

    # verify check in and check out dates
    if checkin_date < date.today():
        return "error: check in date cannot be in the past", 400
    if checkout_date <= checkin_date:
        return "error: check out date must be after check in date", 400

    # dates are valid -> use back original iso-strings to be stored in db
    # unavailable: (existing checkin < new check out) AND (existing check out > new check in)

    # preload query
    query = """
            SELECT * FROM rooms AS r WHERE r.room_physical_status NOT IN ('maintenance', 'out of service')
            AND r.id IN (
                SELECT id from rooms
                EXCEPT
                SELECT DISTINCT room_id FROM bookings
                WHERE booking_status IN ('pending', 'confirmed', 'checked in')
                AND check_in_date < ?
                AND check_out_date > ?)
            """

    # params to be inserted into query
    parameters = [requested_check_out_date, requested_check_in_date]

    # add room type into query and param if specified by user
    if room_type:
        query += " AND r.room_type = ?"
        parameters.append(room_type)

    # loads database
    db = get_db()

    # query database for roooms
    rooms = db.execute(query, parameters).fetchall()

    # returns json to frontend
    rooms = [dict(room) for room in rooms]
    return jsonify({
        "success": True,
        "rooms": rooms
        }), 200



@rooms_bp.route("/add", methods=["POST"])
@role_required("receptionist", "manager")
def add_rooms():

    # gather data
    room_number = request.form.get("room_number")
    room_status = request.form.get("room_status")
    room_type =  request.form.get("room_type")
    room_price = request.form.get("room_price")

    # check for empty fields
    if not (room_number and room_status and room_type and room_price):
        return jsonify({
            "success": False,
            "error": "All fields are required"
            }), 400

    # verify room status
    if room_status.strip().lower() not in ALLOWED_STATUSES:
        return jsonify({
            "success": False,
            "error": f"Invalid room status: {room_status}"
            }), 400

    # verify room type
    if room_type.strip().lower() not in ALLOWED_TYPES:
        return jsonify({
            "success": False,
            "error": f"Invalid room type: {room_type}"
            }), 400

    # verify room price
    try:
        room_price = float(room_price)
        if room_price < 0:
            raise ValueError
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Price must be a valid positive number"
            }), 400

    # makes DB connection
    db = get_db()


    # check if room already exists
    existing_room = db.execute("SELECT id FROM rooms WHERE room_number = ?", (room_number,)).fetchone()
    if existing_room:
        return jsonify({
            "success": False,
            "error": f"Room number {room_number} already exists"
            }), 400

    # safe insertion
    try:
        db.execute("INSERT INTO rooms (room_number, room_physical_status, room_type, room_price) VALUES (?, ?, ?, ?)", (room_number, room_status, room_type, room_price))
        db.commit()
        return jsonify({
            "success": False,
            "message": "Room succesfully added"
            }), 201

    except sqlite3.IntegrityError:
        # clean up connection and release locks
        db.rollback()
        return jsonify({
            "success": False,
            "error": "Room already exists"
            }), 400



@rooms_bp.route("/edit/<int: room_id>", methods=["POST"])
@role_required("receptionist", "manager")
def edit_rooms(room_id):
    # gather data
    room_status = request.form.get("room_status")
    room_price = request.form.get("room_price")

    # ensure at least one input field received
    if not room_status and not room_price:
        flash("Must submit at least one input field.")
        return jsonify({
            "success": False,
            "error": "Must submit at least one field to update"
            }), 400

    updates = []
    params = []

    # check for room status
    if room_status:

        # verify room status
        if room_status.strip().lower() not in ALLOWED_STATUSES:
            return jsonify({
                "success": False,
                "error": f"Invalid room status: {room_status}"
                }), 400

        # append to query and parameter
        updates.append("room_physical_status = ?")
        params.append(room_status)


    # check for room price
    if room_price:
        # ensure price is non-negative real number
        try:
            price = float(room_price)
            if price < 0:
                raise ValueError
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Price must be a valid positive number"
                }), 400

        # append to query and parameter
        updates.append("room_price = ?")
        params.append("price")

    # join final query
    query = f"UPDATE rooms SET {", ".join(updates)} WHERE id = ?"
    params.append(room_id)

    # makes DB connection
    db = get_db()

    # execute query and launch safety net for rare DB-level failures
    try:
        cursor = db.execute(query, params)
        db.commit()
    except sqlite3.IntegrityError:
        # clean up connection and release locks to prevent application deadlocks
        db.rollback()
        return jsonify({
            "success": False,
            "error": "Database constraint violation occurred during update."
            }), 400

    # verify if any row was matched and updated
    if cursor.rowcount == 0:
        return jsonify({
            "success": False,
            "error": f"Room with {room_id} does not exist"
            }), 404

    return jsonify({
        "success": True,
        "message": "Rooms details updated"
        }), 200
