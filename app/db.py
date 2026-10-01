import sqlite3
import re
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        database_path = current_app.config.get(
            "DATABASE", Path(__file__).resolve().parent / "database" / "hotel.db"
        )
        g.db = sqlite3.connect(database_path)
        g.db.create_function(
            "regexp", 2,
            lambda pattern, value: int(
                isinstance(value, str) and re.fullmatch(pattern, value) is not None
            ),
        )

        # enable foreign key enforcement 
        g.db.execute("PRAGMA foreign_keys = ON")
        
        # access db columns by names like in dictionary
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    # remove db from g and store the connection, None if no connection is made
    db = g.pop("db", None)

    if db is not None:
        db.close()
