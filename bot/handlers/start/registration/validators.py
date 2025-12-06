"""
Validation utilities for registration flow.

Contains validators for:
- Wallet addresses
- Passwords
- Phone numbers
- Email addresses
"""

import re


def validate_password(password: str) -> tuple[bool, str | None]:
    """
    Validate financial password.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 6:
        return False, (
            "❌ Пароль слишком короткий!\n\n"
            "Минимальная длина: 6 символов.\n"
            "Попробуйте еще раз:"
        )
    return True, None


def validate_phone(phone: str) -> tuple[bool, str | None]:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return True, None  # Phone is optional

    # Remove spaces, dashes, parentheses
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)

    # Must start with + and contain only digits after
    phone_pattern = r'^\+\d{10,15}$'
    if not re.match(phone_pattern, phone_clean):
        return False, (
            "❌ **Неверный формат телефона!**\n\n"
            "Введите номер в международном формате:\n"
            "• `+7XXXXXXXXXX` (Россия)\n"
            "• `+380XXXXXXXXX` (Украина)\n"
            "• `+375XXXXXXXXX` (Беларусь)\n\n"
            "Или отправьте /skip чтобы пропустить:"
        )
    return True, None


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number by removing formatting characters.

    Args:
        phone: Phone number to normalize

    Returns:
        Normalized phone number
    """
    return re.sub(r'[\s\-\(\)]', '', phone)


def validate_email(email: str) -> tuple[bool, str | None]:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return True, None  # Email is optional

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, (
            "❌ **Неверный формат email!**\n\n"
            "Введите корректный адрес, например:\n"
            "• `user@gmail.com`\n"
            "• `name@mail.ru`\n"
            "• `example@yandex.ru`\n\n"
            "Или отправьте /skip чтобы пропустить:"
        )
    return True, None
