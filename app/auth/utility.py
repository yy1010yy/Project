import secrets
import string
import re


def generate_random_password(length=12):
    """ generate a cryptographically secure random temporary password"""

    characters = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(characters)
        for _ in length
    )


def isValidEmail(email):

    # A standard regex pattern for basic email format
    regex_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # fullmatch checks the entire string from start to finish
    if re.fullmatch(regex_pattern, email):
        return True
    return False
