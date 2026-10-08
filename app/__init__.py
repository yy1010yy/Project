import os
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask
from flask_session import Session

from app.db import close_db, get_db


def create_app(test_config=None):
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    # The dashboard blueprint serves the shared static files at /assets.
    app = Flask(__name__, template_folder="../templates", static_folder=None)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE=str(project_root / "app" / "database" / "hotel.db"),
        SESSION_TYPE="filesystem",
        SESSION_FILE_DIR=str(Path(app.instance_path) / "sessions"),
        SESSION_PERMANENT=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE = True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config is not None:
        app.config.update(test_config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Set SECRET_KEY in the environment or the project .env file.")

    Session(app)
    app.teardown_appcontext(close_db)

    from app.auth import auth_bp
    from app.bookings import bookings_bp
    from app.dashboard import dashboard_bp
    from app.dashboard.routes import error_page
    from app.rooms import rooms_bp
    from app.staff import staff_bp

    for blueprint in (auth_bp, dashboard_bp, rooms_bp, bookings_bp, staff_bp):
        app.register_blueprint(blueprint)

    # The dashboard already registers the shared 403 and 404 pages.
    app.register_error_handler(500, error_page)

    @app.cli.command("init-db")
    def init_database_command():
        """Create missing tables and counters using the existing schema."""
        db = get_db()
        with app.open_resource("database/schema.sql", mode="r") as schema:
            db.executescript(schema.read())
        db.commit()
        click.echo("Database initialized.")

    return app
