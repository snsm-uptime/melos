"""Security and authentication utilities"""
import re


def validate_password(password: str) -> bool:
    """Validate password meets requirements"""
    from api.src.settings import settings

    if len(password) < settings.password_min_length:
        return False
    if len(password) > settings.password_max_length:
        return False
    return True


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
