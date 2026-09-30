from flask import Blueprint


dashboard_bp = Blueprint("dashbaord", __name__)


def register_routes():
    # import route modules to bind endpoints to dashboard_bp
    from app.dashboard import routes


register_routes()