from flask import Blueprint

rooms_bp = Blueprint("rooms", __name__, url_prefix="/rooms")


def register_routes():
    # import route modules to connect endpoints to rooms_bp
    from app.rooms import routes


register_routes()