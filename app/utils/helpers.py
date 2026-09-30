from flask import redirect, session, url_for
from functools import wraps
import re
import string
import secrets


def login_required(base_func):
    """
    decorate routes to require login
    """
    @wraps(base_func)
    def enhanced_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("auth.login"))
        return base_func(*args, **kwargs)

    return enhanced_function


def role_required(*allowed_roles):
    """
    decorate routes to permit only users with specific roles
    """
    def decorator(base_func):
        @wraps(base_func)
        def enhanced_function(*args, **kwargs):

            if session.get("user_id") is None:
                return redirect(url_for("auth.login"))

            if session["role"] not in allowed_roles:
                return "Forbidden", 403

            return base_func(*args, **kwargs)

        return enhanced_function
    return decorator


def isValidEmail(email):

    # A standard regex pattern for basic email format
    regex_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # fullmatch checks the entire string from start to finish
    if re.fullmatch(regex_pattern, email):
        return True
    return False



def generate_random_password(length=12):
    """ generate a cryptographically secure random temporary password"""

    characters = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(characters)
        for _ in length
    )
