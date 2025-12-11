"""
Bonus Management V2 Constants.

This module contains all constants used in the bonus management system including:
- Bonus templates and quick amounts
- Validation limits
- Role permissions and display names
- Status constants
- UI/display constants
"""

from decimal import Decimal

# ============ BONUS TEMPLATES ============

BONUS_REASON_TEMPLATES = [
    ("🎉 Приветственный", "Приветственный бонус за регистрацию"),
    ("🔧 Компенсация", "Компенсация за технические проблемы"),
    ("🏆 За активность", "Бонус за активное участие в проекте"),
    ("👥 Реферальный", "Бонус за привлечение рефералов"),
    ("🎁 Акция", "Бонус в рамках промо-акции"),
    ("⭐ VIP", "VIP-бонус для особого клиента"),
    ("📝 Другое", None),  # Ручной ввод
]

QUICK_AMOUNTS = [5, 10, 30, 50, 70, 100]

# ============ BONUS LIMITS AND VALIDATION ============

BONUS_ROI_CAP_MULTIPLIER = 5  # 500% ROI cap
BONUS_AMOUNT_MIN = Decimal('1')
BONUS_AMOUNT_MAX = Decimal('100000')

# Aliases for backwards compatibility
BONUS_MIN_AMOUNT = BONUS_AMOUNT_MIN
BONUS_MAX_AMOUNT = BONUS_AMOUNT_MAX

REASON_MIN_LENGTH = 5
REASON_MAX_LENGTH = 200
REASON_PREVIEW_LENGTH = 25

# ============ PAGINATION AND DISPLAY LIMITS ============

BONUS_HISTORY_LIMIT = 15
BONUS_STATS_LIMIT = 50
BONUS_CANCEL_LIST_LIMIT = 20
BONUS_FETCH_LIMIT = 100
BONUS_DISPLAY_LIMIT = 10

# ============ BONUS STATUS CONSTANTS ============

BONUS_STATUS_ACTIVE = "active"
BONUS_STATUS_COMPLETED = "completed"
BONUS_STATUS_CANCELLED = "cancelled"
BONUS_STATUS_INACTIVE = "inactive"

# ============ UI CONSTANTS ============

SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"

# ============ ROLE DISPLAY NAMES ============

ROLE_DISPLAY = {
    "super_admin": "👑 Босс",
    "extended_admin": "⭐ Старший админ",
    "admin": "👤 Админ",
    "moderator": "👁 Модератор",
}

# ============ ROLE PERMISSIONS ============

ROLE_PERMISSIONS = {
    "super_admin": {
        "can_grant": True,
        "can_view": True,
        "can_cancel_any": True,
        "can_cancel_own": True,
    },
    "extended_admin": {
        "can_grant": True,
        "can_view": True,
        "can_cancel_any": False,
        "can_cancel_own": True,
    },
    "admin": {
        "can_grant": True,
        "can_view": True,
        "can_cancel_any": False,
        "can_cancel_own": False,
    },
    "moderator": {
        "can_grant": False,
        "can_view": True,
        "can_cancel_any": False,
        "can_cancel_own": False,
    },
}

# Default permissions for unknown roles
DEFAULT_PERMISSIONS = {
    "can_grant": False,
    "can_view": False,
    "can_cancel_any": False,
    "can_cancel_own": False,
}
