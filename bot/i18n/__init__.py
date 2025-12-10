"""
Internationalization (i18n) support.

Provides translation functions and language management.
"""

from .loader import get_translator, get_user_language, set_user_language
from .locales import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


__all__ = [
    "get_translator",
    "set_user_language",
    "get_user_language",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
]
