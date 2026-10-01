import sqlite3
from flask import g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("database/hotel.db")

        # enable foreign key enforcement 
        g.db.execute("PRAGMA foreign_keys = ON")
        
        # access db columns by names like in dictionary
        g.db.row_factory = sqlite3.ROW
    return g.db


def close_db(exception=None):
    # remove db from g and store the connection, None if no connection is made
    db = g.pop("db", None)

    if db is not None:
        db.close()