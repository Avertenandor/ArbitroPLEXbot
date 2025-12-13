"""Типы данных для обработчиков."""
from typing import TYPE_CHECKING, TypedDict

from aiogram.fsm.context import FSMContext

if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.user import User
    from sqlalchemy.ext.asyncio import AsyncSession


class UserHandlerData(TypedDict, total=False):
    """Данные пользовательского обработчика."""

    user: "User"
    session: "AsyncSession"
    state: FSMContext


class AdminHandlerData(TypedDict, total=False):
    """Данные административного обработчика."""

    admin: "Admin"
    user: "User"
    session: "AsyncSession"
    state: FSMContext
