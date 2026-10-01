from flask import Blueprint


bookings_bp = Blueprint("bookings", __name__, url_prefix="/bookings")


def register_routes():
    from . import staff_routes, user_routes


register_routes()
