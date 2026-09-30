from flask import flash, jsonify, redirect, render_template, request, session, url_for

from app.db import get_db
from app.utils.helpers import login_required, role_required

from . import bookings_bp

import sqlite3
from datetime import date


ALLOWED_GUEST_TYPES = ["existing", "new"]


@bookings_bp.route("/staff-start", methods=["GET", "POST"])
@role_required("receptionist", "manager")
def staff_start():

    room_id = request.args.get("room")
    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")

    # check for missing informatoin
    if not room_id or not checkin or not checkout:
        return "error: Missing information", 400

    # verify room id and check in out dates
    try:
        room_id = int(room_id)
        checkin_date = date.fromisoformat(checkin)
        checkout_date = date.fromisoformat(checkout)
    except (ValueError, TypeError):
        return "Invalid data format", 400

    if checkin_date < date.today():
        return "Check in cannot be in the past", 400
    if checkout_date <= checkin_date:
        return "Check out must be after check in", 400


    # staff choose either existing or new guest
    if request.method == "POST":
        guest_type = request.form.get("guest_type")

        if guest_type not in ALLOWED_GUEST_TYPES:
            flash("Must be either existing or new guest")
            return redirect(url_for("bookings.staff_start", room=room_id, checkin=checkin, checkout=checkout))

        if guest_type == "existing":
            return redirect(url_for("bookings.staff_existing_guest", room=room_id, checkin=checkin, checkout=checkout))

        if guest_type == "new":
            return redirect(url_for("bookings.staff_new_guest", room=room_id, checkin=checkin, checkout=checkout))


    if request.method == "GET":
        return render_template("bookings/staff_start.html", room=room_id, checkin=checkin, checkout=checkout)



@bookings_bp.route("/staff-new", methods=["GET"])
@role_required("receptionist", "manager")
def staff_new_guest():

    room_id = request.args.get("room")
    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")

    # check for missing informatoin
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


    return render_template("bookings/new_guest.html", room=room_id, checkin=checkin, checkout=checkout)



@bookings_bp.route("/staff-existing", methods=["GET", "POST"])
@role_required("receptionist", "manager")
def staff_existing_guest():

    room_id = request.args.get("room")
    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")

    # check for missing informatoin
    if not room_id or not checkin or not checkout:
        return "error: Missing information", 400

    # verify room id and check in out dates
    try:
        room_id = int(room_id)
        checkin_date = date.fromisoformat(checkin)
        checkout_date = date.fromisoformat(checkout)
    except (ValueError, TypeError):
        return "Invalid room or booking dates", 400

    if checkin_date < date.today():
        return "Check in cannot be in the past", 400
    if checkout_date <= checkin_date:
        return "Check out must be after check in", 400
        return redirect(url_for("rooms.search"))


    # POST: staff clicks search / select
    if request.method == "POST":
        action = request.form.get("action")
        db = get_db()

        # staff searching for guest
        if action == "search":
            query = request.form.get("query").strip()

            if not query or query == "":
                flash("Please enter an email or username")

            else:
                guests = db.execute(""""
                                    SELECT
                                    guests.id, users.username, users.email
                                    FROM guets
                                    JOIN users
                                    ON guests.user_id = users.id
                                    WHERE users.email LIKE ?
                                    OR users.username LIKE ?
                                    ORDER BY users.usernames
                                    LIMIT 20
                                    """,(query, query)
                                    ).fetchall()
                if not guests:
                    flash("No guest found")

        # staff selects guest
        elif action == "select":
            guest_id = request.form.get("guest_id")

            if guest_id is None:
                flash("Must select a guest")
                return redirect(url_for("bookings.staff_existing_guest", room=room_id, checkin=checkin, checkout=checkout))

            guest = db.execute("SELECT * FROM guests JOIN users ON guests.user_id = users.id WHERE guests.id = ?", (guest_id)).fetchone()

            if guest is None:
                flash("Guest not found")
                return redirect(url_for("bookings.staff_existing_guest", room=room_id, checkin=checkin, checkout=checkout))

            # store guest id in session
            session["staff_booking_guest_id"] = guest["id"]

            return redirect(url_for("bookings.staff_confirm", room=room_id, checkin=checkin, checkout=checkout))


    # GET: displays search bar & search results
    # if guests: display search results
    # if not guests: display search bar
    if request.method == "GET":
        return render_template("bookings/staff_existing_user.html", guests=guests)


@bookings_bp.route("/staff-confirm", methods=["GET"])
@role_required("receptionist", "manager")
def staff_confirm():

    room_id = request.args.get("room")
    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")
    guest_id = session.get("staff_booking_guest_id")


    # makes DB connection
    db = get_db()


    # ensure no empty fields
    if not room_id or not checkin or not checkout:
        flash("error: Missing information")
        return redirect(url_for("rooms.search"))



    # verify room id and check in out dates
    try:
        room_id = int(room_id)
        guest_id = int(guest_id)
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



    # make sure room exists
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id, )).fetchone()

    if room is None:
        flash("Room not found!")
        return redirect(url_for("rooms.search"))

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



    # verify guest
    if guest_id is None:
        flash("No guest selected")
        session.pop("staff_booking_guest_id", None)
        return redirect(url_for("bookings.staff_existing_guest", room=room_id, checkin=checkin, checkout=checkout))

    guest = db.execute("SELECT * FROM guests WHERE id = ?", (guest_id, )).fetchone()

    if guest is None:
        flash("Guest does not exist")
        session.pop("staff_booking_guest_id", None)
        return redirect(url_for("bookings.staff_existing_guest", room=room_id, checkin=checkin, checkout=checkout))

    # returns guest name and email in confirm page
    guest_info = db.execute("SELECT users.username, users.email FROM users JOIN guests ON users.id = guests.user_id WHERE guests.id = ?", (guest_id, )).fetchone()
    guest_info = {"username": guest_info["username"], "email": guest_info["email"]}

    # renders page
    return render_template("bookings/staff_confirm.html", room=room_id, checkin=checkin, checkout=checkout, guest=guest_info)



@bookings_bp.route("/staff-create", methods=["POST"])
@role_required("receptionist", "manager")
def staff_create():

    room_id = request.form.get("room")
    checkin = request.form.get("checkin")
    checkout = request.form.get("checkout")
    guest_id = session.get("staff_booking_guest_id")


    # makes DB conn
    db = get_db()


    # check for empty fields
    if not room_id or not checkin or not checkout:
        return jsonify({
            "success": False,
            "error": "Missing information"
            }), 400


    # check guest id
    if not guest_id:
        session.pop("staff_booking_guest_id", None)
        return jsonify({
            "success": False,
            "error": "Guest id not found"
            }), 400



    # validify id and dates
    try:
        room_id = int(room_id)
        guest_id = int(guest_id)
        checkin_date = date.fromisoformat(checkin)
        checkout_date = date.fromisoformat(checkout)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid data format"
            }), 400


    # verify check in and out dates
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


    # ensure room exists
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id, )).fetchone()

    if not room:
        return jsonify({
            "success": False,
            "error": "Room not found"
            }), 400


    # ensure guest exists
    guest = db.execute("SELECT * FROM guests WHERE id = ?", (guest_id, )).fetchone()

    if guest is None:
        session.pop("staff_booking_guest_id", None)
        return jsonify({
            "success": False,
            "error": "Guest id not found"
            }), 400



    # handles race condition
    try:
        # Begin transaction
        db.execute("BEGIN IMMEDIATE")

        # check for conflict between bookings
        conflict = db.execute("""
                                SELECT * FROM bookings
                                WHERE bookings.room_id = ?
                                AND check_in_date < ?
                                AND check_out_date > ?
                                AND booking_status NOT IN ('checked out', 'cancelled')
                                LIMIT 1
                            """, (room_id, checkout, checkin)).fetchone()

        if conflict:
            db.rollback()
            return jsonify({
                "success": False,
                "error": "Room was just booked by another guest"
                }), 400

        # no conflict -> create booking
        db.execute("INSERT INTO bookings (guest_id, room_id, check_in_date, check_out_date, booking_status) VALUES (?, ?, ?, ?, ?)",
                    (guest_id, room_id, checkin, checkout, ('confirmed')))

        # success
        db.commit()
        session.pop("staff_booking_geust_id", None)
        return jsonify({
            "success": True,
            "message": "Booking created"
            }), 200

    # error
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({
            "success": False,
            "error": "Database constraint violated"
            }), 500

    except sqlite3.Error:
        db.rollback()
        return jsonify({
            "success": False,
            "error": "An error occured"
            }), 500
