"""
Admin Bonus Management V2 - Refactored Module

ПОЛНОСТЬЮ ПЕРЕРАБОТАННЫЙ модуль управления бонусами:
- Интуитивное меню с понятной навигацией
- Быстрые шаблоны причин
- Детальная статистика
- Управление по ролям
- Отмена бонусов с логированием

Permissions:
- super_admin: Полный доступ + отмена любых бонусов
- extended_admin: Начисление + просмотр + отмена своих бонусов
- admin: Начисление + просмотр
- moderator: Только просмотр
"""

from aiogram import Router

from .states import BonusStates
from .handlers import menu_router, grant_router, cancel_router, search_router, view_router

# Create main router
router = Router(name="admin_bonus_management_v2")

# Include all sub-routers
router.include_router(menu_router)
router.include_router(view_router)  # Statistics/history handlers
router.include_router(grant_router)
router.include_router(search_router)
router.include_router(cancel_router)

__all__ = ["router", "BonusStates"]
