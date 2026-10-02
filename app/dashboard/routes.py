from flask import redirect, render_template, request, session, url_for

from app.utils.helpers import login_required, role_required
from app.db import get_db
from app.utils.presentation import reservation_rows, staff_dashboard_data

from . import dashboard_bp


@dashboard_bp.app_errorhandler(403)
@dashboard_bp.app_errorhandler(404)
def error_page(error):
    return render_template("errors/error.html", code=error.code), error.code


@dashboard_bp.route("/", methods=["GET"])
def index():
    if session.get("user_id") is None:
        return render_template("home.html")
    return authenticated_home()


@login_required
def authenticated_home():
    # redirect to corresponding homepages according to roles
    role = session.get("role")

    if role == "guest":
        return redirect(url_for("dashboard.guest_dashboard"))
    elif role == "receptionist":
        return redirect(url_for("dashboard.receptionist_dashboard"))
    elif role == "housekeeper":
        return redirect(url_for("dashboard.housekeeper_dashboard"))
    elif role == "manager":
        return redirect(url_for("dashboard.manager_dashboard"))
    else:
        return redirect(url_for("auth.login"))


@dashboard_bp.route("/home/guest", methods=["GET"])
@role_required("guest")
def guest_dashboard():
    return render_template("dashboard/guest.html", reservations=reservation_rows(session["user_id"]))


@dashboard_bp.route("/home/receptionist", methods=["GET"])
@role_required("receptionist")
def receptionist_dashboard():
    return render_template("dashboard/receptionist.html", **staff_dashboard_data())



@dashboard_bp.route("/home/housekeeper", methods=["GET"])
@role_required("housekeeper")
def housekeeper_dashboard():
    db = get_db()



@dashboard_bp.route("/home/manager", methods=["GET"])
@role_required("manager")
def manager_dashboard():
    return render_template("dashboard/manager.html", **staff_dashboard_data())
