"""
Admin Bonus View/Statistics Handlers.

Handlers for viewing bonus information:
- Detailed statistics
- Bonus history
- Admin's own bonuses
- Individual bonus details
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

from ..states import BonusStates
from ..keyboards import bonus_details_keyboard
from ..helpers import get_bonus_status, get_bonus_status_emoji, format_user_display, truncate_reason
from ..messages import BonusMessages
from ..constants import BONUS_HISTORY_LIMIT, BONUS_STATS_LIMIT, BONUS_FETCH_LIMIT, BONUS_DISPLAY_LIMIT


router = Router(name="bonus_view")


# ============ STATISTICS ============


@router.message(BonusStates.menu, F.text == "📊 Статистика")
async def show_detailed_stats(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Показать детальную статистику."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_service = BonusService(session)
    stats = await bonus_service.get_global_bonus_stats()

    # Получаем недавние бонусы для анализа
    recent = await bonus_service.get_recent_bonuses(limit=BONUS_STATS_LIMIT)

    # Считаем по статусам
    active_sum = sum(b.amount for b in recent if get_bonus_status(b) == "active")
    completed_sum = sum(b.amount for b in recent if get_bonus_status(b) == "completed")
    cancelled_sum = sum(b.amount for b in recent if get_bonus_status(b) == "cancelled")

    text = (
        f"📊 **Детальная статистика бонусов**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Общие суммы:**\n"
        f"├ Всего начислено: **{format_usdt(stats.get('total_granted', 0))}** USDT\n"
        f"├ За последние 24ч: **{format_usdt(stats.get('last_24h', 0))}** USDT\n"
        f"└ Всего записей: **{stats.get('total_count', 0)}**\n\n"
        f"📈 **По статусам (последние {BONUS_STATS_LIMIT}):**\n"
        f"├ 🟢 Активные: **{format_usdt(active_sum)}** USDT\n"
        f"├ ✅ Завершённые: **{format_usdt(completed_sum)}** USDT\n"
        f"└ ❌ Отменённые: **{format_usdt(cancelled_sum)}** USDT\n\n"
        f"ℹ️ _Бонус считается завершённым когда выплачен весь ROI Cap (500%)_"
    )

    await message.answer(text, parse_mode="Markdown")


# ============ HISTORY ============


@router.message(BonusStates.menu, F.text == "📋 История")
async def show_bonus_history(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Показать историю бонусов."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_service = BonusService(session)
    recent = await bonus_service.get_recent_bonuses(limit=BONUS_HISTORY_LIMIT)

    if not recent:
        await message.answer(
            "📋 **История бонусов пуста**\n\nЕщё не было начислено ни одного бонуса.",
            parse_mode="Markdown",
        )
        return

    text = f"📋 **Последние {BONUS_HISTORY_LIMIT} бонусов:**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for b in recent:
        # Статус
        status = get_bonus_status_emoji(b)

        # Данные
        admin_name = b.admin.username if b.admin else "система"
        user_name = b.user.username if b.user else f"ID:{b.user_id}"
        safe_user = escape_markdown(user_name) if user_name else str(b.user_id)
        safe_admin = escape_markdown(admin_name) if admin_name else "система"

        # ROI прогресс для активных
        progress = ""
        if get_bonus_status(b) == "active" and hasattr(b, "roi_progress_percent"):
            progress = f" ({b.roi_progress_percent:.0f}%)"

        reason_short = (b.reason or "")[:25]
        if len(b.reason or "") > 25:
            reason_short += "..."

        text += (
            f"{status} **{format_usdt(b.amount)}** → @{safe_user}{progress}\n"
            f"   📝 _{reason_short}_ | 👤 @{safe_admin}\n"
            f"   🆔 `bonus:{b.id}` для просмотра деталей\n\n"
        )

    text += "_Нажмите на ID чтобы увидеть детали бонуса_"

    await message.answer(text, parse_mode="Markdown")


# ============ MY BONUSES ============


@router.message(BonusStates.menu, F.text == "📑 Мои начисления")
async def show_my_bonuses(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Показать бонусы, начисленные этим админом."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_service = BonusService(session)
    recent = await bonus_service.get_recent_bonuses(limit=BONUS_FETCH_LIMIT)

    # Фильтруем по админу
    my_bonuses = [b for b in recent if b.admin_id == admin.id]

    if not my_bonuses:
        await message.answer(
            "📑 **Ваши начисления**\n\nВы ещё не начислили ни одного бонуса.",
            parse_mode="Markdown",
        )
        return

    # Статистика
    total = sum(b.amount for b in my_bonuses)
    active = [b for b in my_bonuses if get_bonus_status(b) == "active"]

    text = (
        f"📑 **Ваши начисления**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Всего: **{len(my_bonuses)}** бонусов на **{format_usdt(total)}** USDT\n"
        f"🟢 Активных: **{len(active)}**\n\n"
    )

    for b in my_bonuses[:BONUS_DISPLAY_LIMIT]:
        status = get_bonus_status_emoji(b)
        user_name = b.user.username if b.user else f"ID:{b.user_id}"
        safe_user = escape_markdown(user_name)

        text += f"{status} **{format_usdt(b.amount)}** → @{safe_user}\n"

    if len(my_bonuses) > BONUS_DISPLAY_LIMIT:
        text += f"\n_...и ещё {len(my_bonuses) - BONUS_DISPLAY_LIMIT} бонусов_"

    await message.answer(text, parse_mode="Markdown")


# ============ VIEW BONUS DETAILS ============


@router.message(BonusStates.menu, F.text.regexp(r"^bonus:\d+$"))
async def view_bonus_details(
    message: Message,
    session: AsyncSession,
    state: Any,
    **data: Any,
) -> None:
    """Показать детали бонуса по ID."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_id = int(message.text.split(":")[1])

    bonus_service = BonusService(session)
    bonuses = await bonus_service.get_recent_bonuses(limit=100)
    bonus = next((b for b in bonuses if b.id == bonus_id), None)

    if not bonus:
        await message.answer(f"❌ Бонус #{bonus_id} не найден.")
        return

    # Статус
    bonus_status = get_bonus_status(bonus)
    status_text = {
        "active": "🟢 Активен",
        "completed": "✅ Завершён (ROI выплачен)",
        "cancelled": "❌ Отменён",
    }.get(bonus_status, bonus_status)

    user_name = bonus.user.username if bonus.user else f"ID:{bonus.user_id}"
    admin_name = bonus.admin.username if bonus.admin else "система"
    safe_user = escape_markdown(user_name)
    safe_admin = escape_markdown(admin_name)

    progress = bonus.roi_progress_percent if hasattr(bonus, "roi_progress_percent") else 0
    remaining = bonus.roi_remaining if hasattr(bonus, "roi_remaining") else bonus.roi_cap_amount

    text = (
        f"🎁 **Бонус #{bonus.id}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Статус:** {status_text}\n\n"
        f"👤 **Получатель:** @{safe_user}\n"
        f"💰 **Сумма:** {format_usdt(bonus.amount)} USDT\n"
        f"🎯 **ROI Cap:** {format_usdt(bonus.roi_cap_amount)} USDT\n"
        f"📈 **ROI выплачено:** {format_usdt(bonus.roi_paid_amount)} USDT ({progress:.1f}%)\n"
        f"💵 **Осталось:** {format_usdt(remaining)} USDT\n\n"
        f"📝 **Причина:** _{escape_markdown(bonus.reason or 'не указана')}_\n"
        f"👤 **Начислил:** @{safe_admin}\n"
        f"📅 **Дата:** {bonus.created_at.strftime('%d.%m.%Y %H:%M') if bonus.created_at else 'н/д'}"
    )

    # Кнопка отмены только для супер-админа и активных бонусов
    can_cancel = admin.role == "super_admin" and get_bonus_status(bonus) == "active"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=bonus_details_keyboard(bonus.id, can_cancel),
    )
