from flask import Blueprint


dashboard_bp = Blueprint("dashboard", __name__)


def register_routes():
    # import route modules to bind endpoints to dashboard_bp
    from app.dashboard import routes


register_routes()
