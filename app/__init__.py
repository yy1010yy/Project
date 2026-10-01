from flask import Flask
from flask_session import Session
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():

    app = Flask(__name__)

    # configuration
    app.secret_key = os.environ["SECRET_KEY"]
    # database
    # blueprints
    # error handlers

    return app