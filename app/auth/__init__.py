from flask import Blueprint

auth_bp = Blueprint("auth", __name__, )


def register_routes():
    # import route modules to bind their endpoints to auth_bp
    from app.auth import routes


register_routes()