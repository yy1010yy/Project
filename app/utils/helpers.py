from flask import abort, redirect, request, session, url_for
from functools import wraps
import re
import string
import secrets

from app.db import get_db


def _login_redirect():
    """Validate the current account and enforce temporary-password replacement."""
    if session.get("user_id") is None:
        return redirect(url_for("auth.login"))

    user = get_db().execute(
        "SELECT user_role, must_change_password FROM users WHERE id = ? AND is_active = 1",
        (session["user_id"],),
    ).fetchone()
    if user is None:
        session.clear()
        return redirect(url_for("auth.login"))

    session["role"] = user["user_role"]
    if user["must_change_password"] and request.endpoint not in (
        "auth.change_password", "auth.logout"
    ):
        return redirect(url_for("auth.change_password"))
    return None


def login_required(base_func):
    """
    decorate routes to require login
    """
    @wraps(base_func)
    def enhanced_function(*args, **kwargs):
        response = _login_redirect()
        if response is not None:
            return response
        return base_func(*args, **kwargs)

    return enhanced_function


def role_required(*allowed_roles):
    """
    decorate routes to permit only users with specific roles
    """
    def decorator(base_func):
        @wraps(base_func)
        def enhanced_function(*args, **kwargs):

            response = _login_redirect()
            if response is not None:
                return response

            if session.get("role") not in allowed_roles:
                abort(403)

            return base_func(*args, **kwargs)

        return enhanced_function
    return decorator


def isValidEmail(email):

    # A standard regex pattern for basic email format
    regex_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    # fullmatch checks the entire string from start to finish
    if isinstance(email, str) and re.fullmatch(regex_pattern, email):
        return True
    return False



def generate_random_password(length=12):
    """ generate a cryptographically secure random temporary password"""

    characters = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )
