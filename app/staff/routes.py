from flask import flash, jsonify, redirect, render_template, request, session

from werkzeug.security import generate_password_hash, check_password_hash

from app.db import get_db
from app.utils.helpers import login_required, role_required, generate_random_password, isValidEmail

from . import staff_bp
from .utility import assign_employee_id

import sqlite3


VALID_ROLES = ["receptionist", "manager", "housekeeper"]


@staff_bp.route("/", methods=["GET"])
@role_required("manager")
def staff_list():

    db = get_db()

    staff = db.execute("""
        SELECT
            s.employee_id,
            u.username,
            u.email,
            u.role,
            u.is_active
        FROM staff AS s
        JOIN users AS u
            ON s.user_id = u.id
        ORDER BY s.employee_id
    """).fetchall()

    return render_template(
        "staff/staff.html",
        staff=staff
    )



@staff_bp.route("/create", methods=["GET", "POST"])
@role_required("manager")
def create_staff():

    # manager submits staff info to be created
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "").strip().lower()

        # -------------------------
        # Validate input
        # -------------------------

        if not username:
            return jsonify({
                "success": False,
                "error": "Username is required."
                }), 400

        if not email:
            return jsonify({
                "success": False,
                "error": "Email is required."
                }), 400

        if role not in VALID_ROLES:
            return jsonify({
                "success": False,
                "error": "Invalid staff role."
                }), 400

        db = get_db()

        # -------------------------
        # Check username/email
        # -------------------------

        existing = db.execute("""
            SELECT id
            FROM users
            WHERE username = ?
            OR email = ?
        """, (username, email)).fetchone()

        if existing:
            return jsonify({
                "success": False,
                "error": "Username or email is already in use."
            }), 409

        # -------------------------
        # Generate credentials
        # -------------------------

        temporary_password = generate_random_password()
        password_hash = generate_password_hash(temporary_password)

        try:

            # Lock database for the entire operation.
            db.execute("BEGIN IMMEDIATE")

            # Assign employee ID.
            employee_id = assign_employee_id(db, role)

            # Create user account.
            cursor = db.execute("""
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    role,
                    must_change_password
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                username,
                email,
                password_hash,
                role,
                1
            ))

            user_id = cursor.lastrowid

            # Create staff record.
            db.execute("""
                INSERT INTO staff (
                    user_id,
                    employee_id
                )
                VALUES (?, ?)
            """, (
                user_id,
                employee_id
            ))

            db.commit()

        except sqlite3.IntegrityError:
            db.rollback()

            return jsonify({
                "success": False,
                "error": "Unable to create staff account."
            }), 409

        except Exception:
            db.rollback()
            raise

        return jsonify({
            "success": True,
            "employee_id": employee_id,
            "temporary_password": temporary_password
        }), 201


    # GET displays employees
    return render_template("staff/create.html")



@staff_bp.route("/edit/<string: employee_id>", methods=["GET", "POST"])
@role_required("manager")
def edit_staff(employee_id):

    db = get_db()

    # GET: show edit page
    if request.method == "GET":

        staff = db.execute("""
            SELECT
                s.employee_id,
                u.username,
                u.email,
                u.role
            FROM staff AS s
            JOIN users AS u
                ON s.user_id = u.id
            WHERE s.employee_id = ?
        """, (employee_id,)).fetchone()

        if not staff:
            return "Staff member not found.", 404

        return render_template(
            "staff/edit.html",
            staff=staff
        )


    # POST: update staff
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        role = request.form.get("role")

        # Make sure the employee exists first.
        staff = db.execute("""
            SELECT user_id
            FROM staff
            WHERE employee_id = ?
        """, (employee_id,)).fetchone()

        if not staff:
            return jsonify({
                "success": False,
                "error": "Staff member not found."
            }), 404

        updates = []
        values = []

        # Username
        if username is not None:

            username = username.strip()

            if not username:
                return jsonify({
                    "success": False,
                    "error": "Username cannot be empty."
                }), 400

            updates.append("username = ?")
            values.append(username)

        # Email
        if email is not None:

            if not isValidEmail(email):
                return jsonify({
                    "success": False,
                    "error": "Invalid email."
                }), 400

            updates.append("email = ?")
            values.append(email)

        # Role
        if role is not None:

            role = role.strip().lower()

            if role not in VALID_ROLES:
                return jsonify({
                    "success": False,
                    "error": "Invalid staff role."
                }), 400

            updates.append("role = ?")
            values.append(role)

        # Nothing was provided
        if not updates:
            return jsonify({
                "success": False,
                "error": "No changes provided."
            }), 400

        # Check email conflicts
        if email is not None:

            existing = db.execute("""
                SELECT id
                FROM users
                WHERE email = ?
                AND id != ?
            """, (
                email,
                staff["user_id"]
            )).fetchone()

            if existing:
                return jsonify({
                    "success": False,
                    "error": "Username or email is already in use."
                }), 409

        values.append(staff["user_id"])

        try:

            db.execute(f"""
                UPDATE users
                SET {", ".join(updates)}
                WHERE id = ?
            """, values)

            db.commit()

            return jsonify({
                "success": True,
                "message": "Staff details successfully updated."
            })

        except sqlite3.IntegrityError:
            db.rollback()
            return jsonify({
                "success": False,
                "error": "Email already in use."
            }), 409

        except sqlite3.Error:
            db.rollback()
            return jsonify({
                "success": False,
                "error": "An unexpected server error occured."
            }), 400



@staff_bp.route("/deactivate/<string: employee_id>", methods=["POST"])
@role_required("manager")
def deactivate_staff(employee_id):

    if not employee_id:
        return jsonify({
            "success": False,
            "error": "Employee ID is required."
        }), 400

    db = get_db()

    staff = db.execute("""
        SELECT user_id
        FROM staff
        WHERE employee_id = ?
    """, (employee_id,)).fetchone()

    if not staff:
        return jsonify({
            "success": False,
            "error": "Staff member not found."
        }), 404

    user = db.execute("""
        SELECT is_active
        FROM users
        WHERE id = ?
    """, (staff["user_id"],)).fetchone()

    if not user:
        return jsonify({
            "success": False,
            "error": "Associated user account not found."
        }), 404

    if not user["is_active"]:
        return jsonify({
            "success": False,
            "error": "Staff member is already inactive."
        }), 409

    db.execute("""
        UPDATE users
        SET is_active = 0
        WHERE id = ?
    """, (staff["user_id"],))

    db.commit()

    return jsonify({
        "success": True,
        "message": "Employee deactivated."
    }), 200
