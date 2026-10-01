from flask import abort, flash, jsonify, session, redirect, request, render_template, url_for

from app.db import get_db
from app.utils.helpers import generate_random_password, role_required, login_required, isValidEmail

from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

from . import auth_bp



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """ user logins """

    # clear session
    session.clear()

    # user submits login details via POST
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password")


        # check for empty input fields
        if not email:
            return "error: must provide email", 400
        if not password:
            return "error: must provide password", 401

        # validify email
        if not isValidEmail(email):
            return "error: invalid email format", 401

        # query database for user
        db = get_db()
        user_details = db.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,)).fetchall()

        # ensure user's email exists and password is correct
        if len(user_details) != 1 or not check_password_hash(user_details[0]["hashed_password"], password):
            return "error: invalid password or email", 403



        # separate id by role
        # store guest id
        if user_details[0]["user_role"] == "guest":
            guest = db.execute("SELECT id FROM guests WHERE user_id = ?", (user_details[0]["id"],)).fetchone()

            if guest is None:
                abort(403)

            session["guest_id"] = guest["id"]
        # store staff id
        elif user_details[0]["user_role"] in ["receptionist", "manager", "housekeeper"]:
            staff = db.execute("SELECT id FROM staff WHERE user_id = ?", (user_details[0]["id"],)).fetchone()

            if staff is None:
                abort(403)

            session["staff_id"] = staff["id"]

        # remember which user has logged in
        session["user_id"] = user_details[0]["id"]
        session["role"] = user_details[0]["user_role"]

        # Establish the session before entering the protected password-change page.
        if user_details[0]["must_change_password"] == 1:
            flash("Please change your temporary password before continuing.", "info")
            return redirect(url_for("auth.change_password"))

        # redirect to homepage after user successfully logs in
        return redirect(url_for("dashboard.index"))


    # user visits log in page
    elif request.method == "GET":
        return render_template("auth/login.html")



@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """ registers user """

    # user reaches via POST (by submitting a form)
    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")


        # check for empty input fields
        if not username or username.strip() == "":
            return "error: must provide username", 401
        if not email:
            return "error: must provide email", 401
        if not password:
            return "error: must provide password", 400
        if not confirm_password:
            return "error: must confirm password", 401

        # checks email validity
        if not isValidEmail(email):
            return "error: invalid email format", 401

        # ensure password matches:
        if password != confirm_password:
            return "error: passwords do not match", 400

        # makes DB connection
        db = get_db()

        # checks for duplicate email
        existing_user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("email already registered")
            return "error: email already registered", 400

        # hash submitted password
        hashed_password = generate_password_hash(password)

        # safe insertion
        try:
            cursor = db.execute("INSERT INTO users (username, email, hashed_password, user_role) VALUES (?, ?, ?, ?)", (username, email, hashed_password, "guest"))

            user_id = cursor.lastrowid

            db.execute("INSERT INTO guests (user_id) VALUES (?)", (user_id, ) )

            db.commit()
            flash("Account succesfully created. Proceed to log in", "success")
            return redirect(url_for("auth.login"))
        # database constraint violated
        except sqlite3.IntegrityError:
            db.rollback()
            flash("email already exists", "danger")
            return redirect(url_for("auth.register"))
        except sqlite3.Error:
            db.rollback()
            flash("Unexpected server error", "danger")
            return redirect(url_for("auth.register"))



    # user vists register page via GET
    elif request.method == "GET":
            return render_template("auth/register.html")


@auth_bp.route("/logout", methods=["GET"])
def logout():
    """ logs user out """

    # forget any user id
    session.clear()

    # redirect user back to log in
    return redirect(url_for("auth.login"))



@auth_bp.route("/quick-register", methods=["POST"])
@role_required("receptionist", "manager")
def quick_register():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()


    # check for empty input fields
    if not username or username.strip() == "":
        return jsonify({
            "success": False,
            "error": "Must provide username"
            }), 401
    if not email:
        return jsonify({
            "success": False,
            "error": "Must provide email"
            }), 401

    # checks email validity
    if not isValidEmail(email):
        return ({
            "success": False,
            "error": "Invalid email format"
            }), 401


    # generate and hash temporary password
    temporary_password = generate_random_password()
    temporary_password_hash = generate_password_hash(temporary_password)

    db = get_db()

    # handles race condition: both receptionists create account for new user
    try:
        db.execute("BEGIN IMMEDIATE")

        # checks if user already exists
        existing_guest = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if existing_guest:
            db.rollback()
            return jsonify({
                "success": False,
                "error": "An account with this email is already registered"
                }), 409

        # new user -> create account
        cursor = db.execute("""INSERT INTO users
                                (username, email, hashed_password, user_role, must_change_password)
                                VALUES (?, ?, ?, ?, 1)
                            """, (username, email, temporary_password_hash, "guest"))

        user_id = cursor.lastrowid

        # create guest profile linked to user id
        cursor = db.execute("INSERT INTO guests (user_id) VALUES (?)", (user_id,))

        guest_id = cursor.lastrowid

        # save changes
        db.commit()
        session["staff_booking_guest_id"] = guest_id

    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({
            "success": False,
            "error": "Could not create the guest. Check whether the email already exists."
        }), 409

    except sqlite3.Error:
        db.rollback()
        return jsonify({
            "success": False,
            "error": "A database error occurred."
        }), 500


    # return new guest ID and temporary password
    return jsonify({
        "success": True,
        "message": "Guest account successfully created",
        "guest_id": guest_id,
        "temporary_password": temporary_password
    }), 201



@auth_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():


    # user submits new password via POST
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")


        # Check empty fields
        if not current_password or not new_password or not confirm_password:
            return render_template(
                "auth/change_password.html",
                error="All fields are required."
            )

        # Check new password confirmation
        if new_password != confirm_password:
            return render_template(
                "auth/change_password.html",
                error="New passwords do not match."
            )

        # query database for user
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()


        if not user:
            session.clear()
            return redirect(url_for("auth.login"))


        # Check current password
        if not check_password_hash(user["hashed_password"], current_password):
            return render_template(
                "auth/change_password.html",
                error="Current password is incorrect."
            )


        # Don't allow the same password
        if check_password_hash(user["hashed_password"], new_password):
            return render_template(
                "auth/change_password.html",
                error="New password must be different from your current password."
            )

        # Hash new password
        new_password_hash = generate_password_hash(new_password)


        try:
            db.execute(
                """UPDATE users
                   SET hashed_password = ?, must_change_password = 0
                   WHERE id = ?""",
                (new_password_hash, session["user_id"]),
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()
            return render_template(
                "auth/change_password.html",
                error="Unable to change your password. Please try again.",
            ), 500

        session.clear()
        flash("Password changed. Please log in with your new password.", "success")
        return redirect(url_for("auth.login"))

    # user enters change password page via GET
    return render_template("auth/change_password.html")
