"""
AI Assistant utilities, states and keyboards.

Contains helper functions, FSM states and keyboard builders.
"""

from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.services.ai_assistant_service import UserRole
from app.services.monitoring_service import MonitoringService


async def clear_state_keep_session(state: FSMContext) -> None:
    """Clear FSM state but preserve admin session token."""
    state_data = await state.get_data()
    session_token = state_data.get("admin_session_token")
    await state.clear()
    if session_token:
        await state.update_data(admin_session_token=session_token)


class AIAssistantStates(StatesGroup):
    """States for AI assistant interaction."""

    chatting = State()
    action_flow = State()


def ai_assistant_keyboard() -> Any:
    """Create AI assistant keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Статус системы"),
        KeyboardButton(text="👥 Статистика"),
    )
    builder.row(
        KeyboardButton(text="❓ Помощь по админке"),
        KeyboardButton(text="📚 FAQ"),
    )
    builder.row(KeyboardButton(text="💬 Свободный диалог"))
    builder.row(KeyboardButton(text="◀️ Назад в админку"))
    return builder.as_markup(resize_keyboard=True)


def chat_keyboard() -> Any:
    """Keyboard for chat mode."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🛠 Действия"))
    builder.row(KeyboardButton(text="🧠 Запомнить это"))
    builder.row(KeyboardButton(text="💬 Написать Дарье"))
    builder.row(KeyboardButton(text="🔚 Завершить диалог"))
    return builder.as_markup(resize_keyboard=True)


def aria_actions_inline_keyboard() -> Any:
    """Inline actions keyboard for ARIA admin chat."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="💳 Изменить баланс",
        callback_data="aria:act:balance",
    )
    kb.button(
        text="➖ Списать депозит",
        callback_data="aria:act:cancel_deposit",
    )
    kb.button(
        text="➕ Ручной депозит",
        callback_data="aria:act:manual_deposit",
    )
    kb.button(
        text="🎁 Начислить бонус",
        callback_data="aria:act:bonus",
    )
    kb.adjust(2, 2)
    return kb.as_markup()


def aria_cancel_inline_keyboard() -> Any:
    """Cancel keyboard for ARIA actions."""
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="aria:act:cancel")
    return kb.as_markup()


def aria_balance_operation_keyboard() -> Any:
    """Balance operation keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Начислить", callback_data="aria:balance_op:add")
    kb.button(
        text="➖ Списать",
        callback_data="aria:balance_op:subtract",
    )
    kb.button(text="❌ Отмена", callback_data="aria:act:cancel")
    kb.adjust(2, 1)
    return kb.as_markup()


def aria_level_keyboard() -> Any:
    """Level selection keyboard."""
    kb = InlineKeyboardBuilder()
    for lvl in range(1, 6):
        kb.button(
            text=f"Уровень {lvl}",
            callback_data=f"aria:level:{lvl}",
        )
    kb.button(text="❌ Отмена", callback_data="aria:act:cancel")
    kb.adjust(3, 2, 1)
    return kb.as_markup()


def aria_deposits_pick_keyboard(
    deposit_rows: list[tuple[int, float]],
) -> Any:
    """
    Deposit picker keyboard.

    Args:
        deposit_rows: [(deposit_id, amount_usdt), ...]
    """
    kb = InlineKeyboardBuilder()
    for deposit_id, amount in deposit_rows[:8]:
        kb.button(
            text=f"#{deposit_id} · {amount:.2f} USDT",
            callback_data=f"aria:deposit:{deposit_id}",
        )
    kb.button(text="❌ Отмена", callback_data="aria:act:cancel")
    kb.adjust(1)
    return kb.as_markup()


def aria_confirm_keyboard(confirm_cb: str) -> Any:
    """Confirmation keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=confirm_cb)
    kb.button(text="❌ Отмена", callback_data="aria:act:cancel")
    kb.adjust(2)
    return kb.as_markup()


def aria_suggest_cancel_deposit_keyboard() -> Any:
    """Suggest cancel deposit keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="➖ Списать депозит",
        callback_data="aria:suggest:cancel_deposit",
    )
    kb.button(text="❌ Отмена", callback_data="aria:act:cancel")
    kb.adjust(2)
    return kb.as_markup()


def _build_admin_data(admin: Any) -> dict[str, Any]:
    """Build admin data dictionary."""
    return {
        "ID": getattr(admin, "telegram_id", None),
        "username": getattr(admin, "username", None),
        "Имя": getattr(admin, "display_name", None),
        "Роль": getattr(admin, "role_display", None),
    }


async def get_platform_stats(session: AsyncSession) -> dict[str, Any]:
    """Get platform statistics for AI context."""
    try:
        user_repo = UserRepository(session)
        total_users = await user_repo.count()
        verified_users = await user_repo.count_verified_users()

        return {
            "Всего пользователей": total_users,
            "Верифицированных пользователей": verified_users,
        }
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return {}


async def get_monitoring_data(session: AsyncSession) -> str:
    """Get real-time monitoring data for ARIA."""
    try:
        monitoring = MonitoringService(session)
        dashboard = await monitoring.get_full_dashboard()
        formatted = monitoring.format_dashboard_for_ai(dashboard)

        # Add activity analytics
        activity_report = await monitoring.format_activity_for_aria(24)
        if activity_report and "не активирована" not in activity_report:
            formatted += "\n\n" + activity_report

        # Add AI conversations if available
        ai_conversations = await monitoring.get_ai_conversations_report(24)
        if (
            ai_conversations
            and "не активировано" not in ai_conversations.lower()
        ):
            formatted += "\n\n" + ai_conversations

        logger.debug(f"ARIA context size: {len(formatted)} chars")
        return formatted
    except Exception as e:
        logger.error(f"Error getting monitoring data: {e}")
        return ""


def get_user_role_from_admin(admin: Any) -> UserRole:
    """Convert admin model to UserRole with reliable detection."""
    if admin.is_super_admin:
        return UserRole.SUPER_ADMIN
    elif admin.is_extended_admin:
        return UserRole.EXTENDED_ADMIN
    elif admin.role == "moderator":
        return UserRole.MODERATOR
    else:
        return UserRole.ADMIN


def _is_capabilities_question(text: str) -> bool:
    """
    Detect questions about ARIA admin capabilities.

    Recognizes phrases like:
    - "что ты можешь как админ" / "как администратор"
    - "что ты можешь по моему приказу"
    - любые варианты с "что ты можешь" + "приказ".
    """
    if not text:
        return False

    text_l = text.lower()

    if (
        "что ты можешь" not in text_l
        and "что ты умеешь" not in text_l
    ):
        return False

    if "как админ" in text_l or "как администратор" in text_l:
        return True

    if (
        "по моему приказ" in text_l
        or "по приказам" in text_l
        or "по приказу" in text_l
    ):
        return True

    return False


def _get_admin_capabilities_text(role: UserRole) -> str:
    """Return static description of ARIA admin capabilities."""
    if role == UserRole.SUPER_ADMIN:
        role_name = "👑 Владелец / Командир"
    elif role == UserRole.EXTENDED_ADMIN:
        role_name = "⭐ Расширенный админ"
    elif role == UserRole.MODERATOR:
        role_name = "📝 Модератор"
    else:
        role_name = "👤 Админ"

    return (
        f"🤖 Вот что я могу делать как AI-помощник "
        f"для админов ({role_name}):\n\n"
        "**1. Информация и аналитика**\n"
        "• Смотреть сводку по пользователям, депозитам, "
        "выводам и обращениям.\n"
        "• Анализировать логи и мониторинг, подсказывать "
        "возможные проблемы.\n\n"
        "**2. Работа с пользователями**\n"
        "• Находить пользователя по ID, нику, кошельку.\n"
        "• Подсказать, какие у него депозиты, выводы, "
        "статус верификации.\n\n"
        "**3. Депозиты и выводы**\n"
        "• Показывать очереди выводов и детали заявок.\n"
        "• Делать текстовые рекомендации по "
        "одобрению/отклонению "
        "(с учётом лимитов и правил).\n"
        "• Для доверенных админов — вызывать "
        "одобрение/отклонение через безопасные "
        "инструменты системы.\n\n"
        "**4. ROI, бонусы и PLEX**\n"
        "• Объяснять текущие уровни ROI и правила "
        "начислений.\n"
        "• Помогать проверять требования Pay-to-Use "
        "по PLEX перед выводами.\n\n"
        "**5. Безопасность и чёрный список**\n"
        "• Показывать, кто и за что в чёрном списке.\n"
        "• Давать рекомендации по блокировкам, но "
        "выполнять их только через утверждённые "
        "инструменты.\n\n"
        "**6. Системные действия**\n"
        "• Управлять аварийными стопами "
        "(депозиты, выводы, ROI).\n"
        "• Менять настройки системы через "
        "специальные команды.\n\n"
        "**Важно про безопасность**\n"
        "• Опасные операции доступны только "
        "администраторам (проверка по базе, "
        "заблокированные не допускаются).\n"
        "• Даже если внешний AI временно недоступен, "
        "я могу подсказать, что и где нажать вручную "
        "в админке.\n"
    )
