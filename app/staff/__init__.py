from flask import Blueprint


staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


def register_routes():
    # import modules to connect their endpoints to staff_bp
    from . import routes


register_routes()