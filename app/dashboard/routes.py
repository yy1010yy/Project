from flask import redirect, render_template, request, session, url_for

from app.utils.helpers import login_required, role_required
from app.db import get_db

from . import dashboard_bp


@dashboard_bp.route("/", methods=["GET"])
@login_required
def index():
    # redirect to corresponding homepages according to roles
    role = session.get("role")

    if role == "guest":
        return redirect(url_for("dashboard.guest_dashbaord"))
    elif role == "receptionist":
        return redirect(url_for("dashboard.receptionist_dashboard"))
    elif role == "housekeeper":
        return redirect(url_for("dashboard.housekeeper_dashboard"))
    elif role == "manager":
        return redirect(url_for("dashboard.manager_dashbaord"))
    else:
        return redirect(url_for("auth.login"))


@dashboard_bp.route("/home/guest", methods=["GET"])
@login_required
def guest_dashboard():
    db = get_db()


@dashboard_bp.route("/home/receptionist", methods=["GET"])
@role_required("receptionist")
def receptionist_dashboard():
    db = get_db()



@dashboard_bp.route("/home/housekeeper", methods=["GET"])
@role_required("housekeeper")
def housekeeper_dashboard():
    db = get_db()



@dashboard_bp.route("/home/manager", methods=["GET"])
@role_required("manager")
def manager_dashboard():
    db = get_db()