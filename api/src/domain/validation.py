"""Validation rules for domain entities"""
from typing import Tuple


class ValidationRules:
    """Validation constraints from spec"""

    # Recipe
    RECIPE_TITLE_MIN = 1
    RECIPE_TITLE_MAX = 200
    RECIPE_YIELD_MIN = 1
    RECIPE_YIELD_MAX = 100
    RECIPE_TIME_MIN = 0
    RECIPE_TIME_MAX = 1440  # 24 hours

    # Ingredient
    INGREDIENT_NAME_MIN = 1
    INGREDIENT_NAME_MAX = 100
    INGREDIENT_NAME_ALIASES_MAX = 10

    # Kitchen
    KITCHEN_NAME_MIN = 1
    KITCHEN_NAME_MAX = 100

    # User/Auth
    PASSWORD_MIN = 8
    PASSWORD_MAX = 256
    EMAIL_MAX = 255

    # Member/Invite
    INVITE_EXPIRY_HOURS = 7 * 24  # 7 days
    INVITE_TOKEN_LENGTH = 32

    # Shopping List
    SHOPPING_LIST_HEADCOUNT_MIN = 1
    SHOPPING_LIST_HEADCOUNT_MAX = 50

    @staticmethod
    def validate_recipe_title(title: str) -> Tuple[bool, str]:
        """Validate recipe title"""
        if not title:
            return False, "Recipe title is required"
        if len(title) < ValidationRules.RECIPE_TITLE_MIN:
            return False, "Recipe title is too short"
        if len(title) > ValidationRules.RECIPE_TITLE_MAX:
            return False, f"Recipe title must be {ValidationRules.RECIPE_TITLE_MAX} characters or less"
        return True, ""

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        if len(password) < ValidationRules.PASSWORD_MIN:
            return False, f"Password must be at least {ValidationRules.PASSWORD_MIN} characters"
        if len(password) > ValidationRules.PASSWORD_MAX:
            return False, f"Password must be {ValidationRules.PASSWORD_MAX} characters or less"
        return True, ""

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email format"""
        import re
        if not email:
            return False, "Email is required"
        if len(email) > ValidationRules.EMAIL_MAX:
            return False, f"Email must be {ValidationRules.EMAIL_MAX} characters or less"
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        return True, ""

    @staticmethod
    def validate_kitchen_name(name: str) -> Tuple[bool, str]:
        """Validate kitchen name"""
        if not name:
            return False, "Kitchen name is required"
        if len(name) < ValidationRules.KITCHEN_NAME_MIN:
            return False, "Kitchen name is too short"
        if len(name) > ValidationRules.KITCHEN_NAME_MAX:
            return False, f"Kitchen name must be {ValidationRules.KITCHEN_NAME_MAX} characters or less"
        return True, ""
