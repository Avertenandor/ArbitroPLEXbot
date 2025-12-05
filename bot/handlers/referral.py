"""
Referral Handler - ТОЛЬКО REPLY KEYBOARDS!

Handles referral program actions including stats, leaderboard, and earnings.
"""

import re
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.referral_service import ReferralService
from app.services.user_service import UserService
from bot.keyboards.reply import referral_keyboard, referral_list_keyboard
from bot.utils.constants import REFERRAL_RATES
from bot.utils.formatters import format_usdt

router = Router(name="referral")


async def _show_referral_list(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    level: int = 1,
    page: int = 1,
) -> None:
    """
    Show referral list for specific level and page.

    R4-3: Shows detailed list with dates and earnings.
    R4-4: Supports pagination.

    Args:
        message: Telegram message
        session: Database session
        user: Current user
        state: FSM context
        level: Referral level (1-3)
        page: Page number
    """
    referral_service = ReferralService(session)

    # Get referrals for the level
    result = await referral_service.get_referrals_by_level(
        user.id, level=level, page=page, limit=10
    )

    referrals = result["referrals"]
    total = result["total"]
    total_pages = result["pages"]

    # Save to FSM for navigation
    await state.update_data(
        referral_level=level,
        referral_page=page,
    )

    # Build message text
    text = f"👥 *Мои рефералы - Уровень {level}*\n\n"

    if not referrals:
        text += f"На уровне {level} у вас пока нет рефералов."
    else:
        text += f"*Всего рефералов уровня {level}: {total}*\n\n"

        for idx, ref in enumerate(referrals, start=1):
            ref_user = ref["user"]
            earned = ref["earned"]
            joined_at = ref["joined_at"]

            username = ref_user.username or "без username"
            # Escape Markdown chars in username
            username = (
                username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            date_str = joined_at.strftime("%d.%m.%Y")

            text += (
                f"*{idx + (page - 1) * 10}.* @{username}\n"
                f"📅 Дата регистрации: {date_str}\n"
                f"💰 Заработано: *{format_usdt(earned)} USDT*\n\n"
            )

        if total_pages > 1:
            text += f"*Страница {page} из {total_pages}*\n\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_list_keyboard(
            level=level,
            page=page,
            total_pages=total_pages,
        ),
    )


@router.message(F.text == "👥 Мои рефералы")
async def handle_my_referrals(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """
    Show user's referrals list.

    R4-2: Checks if user has any referrals, shows message if none.
    R4-3: Shows detailed list by levels.
    """
    referral_service = ReferralService(session)

    # R4-2: Check if user has any referrals across all levels
    total_referrals = 0
    for level in [1, 2, 3]:
        result = await referral_service.get_referrals_by_level(
            user.id, level=level, page=1, limit=1
        )
        total_referrals += result["total"]

    # R4-2: If no referrals at all, show message
    if total_referrals == 0:
        text = (
            "👥 *Мои рефералы*\n\n"
            "У вас пока нет рефералов.\n\n"
            "Приглашайте друзей и получайте бонусы с *3-х уровней*!\n"
            f"• Уровень 1: *{int(REFERRAL_RATES[1] * 100)}%* "
            "от депозитов и дохода\n"
            f"• Уровень 2: *{int(REFERRAL_RATES[2] * 100)}%* "
            "от депозитов и дохода\n"
            f"• Уровень 3: *{int(REFERRAL_RATES[3] * 100)}%* "
            "от депозитов и дохода\n\n"
            "Вашу реферальную ссылку можно найти в разделе "
            "\"📊 Статистика рефералов\"."
        )
        await message.answer(
            text, parse_mode="Markdown", reply_markup=referral_keyboard()
        )
        return

    # R4-3: Show detailed list for Level 1 by default
    await _show_referral_list(message, session, user, state, level=1, page=1)


@router.message(F.text.regexp(r"^📊 Уровень (\d+)$"))
async def handle_referral_level_selection(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Handle referral level selection button."""
    match = re.match(r"^📊 Уровень (\d+)$", message.text)
    if not match:
        return

    level = int(match.group(1))
    if level not in [1, 2, 3]:
        await message.answer("❌ Неверный уровень рефералов.")
        return

    await _show_referral_list(
        message, session, user, state, level=level, page=1
    )


@router.message(F.text.in_(["⬅ Предыдущая страница", "➡ Следующая страница"]))
async def handle_referral_pagination(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Handle referral list pagination."""
    data = await state.get_data()
    level = data.get("referral_level", 1)
    current_page = data.get("referral_page", 1)

    if message.text == "⬅ Предыдущая страница":
        page = max(1, current_page - 1)
    else:
        page = current_page + 1

    await _show_referral_list(
        message, session, user, state, level=level, page=page
    )


@router.message(F.text == "💰 Мой заработок")
async def handle_my_earnings(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show user's referral earnings."""
    referral_service = ReferralService(session)

    # Get referral stats
    stats = await referral_service.get_referral_stats(user.id)

    # R4-6: Check for zero earnings
    total_earned = stats.get('total_earned', 0)
    if total_earned == 0:
        text = (
            "💰 *Мой заработок*\n\n"
            "У вас пока нет реферальных начислений.\n\n"
            "💡 *Совет:* Начните строить свою команду! "
            "Ссылку можно найти в разделе "
            "\"📊 Статистика рефералов\"."
        )
        await message.answer(
            text, parse_mode="Markdown", reply_markup=referral_keyboard()
        )
        return

    # Get pending earnings
    result = await referral_service.get_pending_earnings(
        user.id, page=1, limit=10
    )
    earnings = result["earnings"]
    total_amount = result["total_amount"]

    text = (
        f"💰 *Мой заработок*\n\n"
        f"*Доходы:*\n"
        f"💵 Всего заработано: *{format_usdt(stats['total_earned'])} USDT*\n"
        f"⏳ Ожидает выплаты: "
        f"*{format_usdt(stats['pending_earnings'])} USDT*\n"
        f"✅ Выплачено: *{format_usdt(stats['paid_earnings'])} USDT*\n\n"
    )

    if earnings:
        text += "*Последние выплаты:*\n"
        for earning in earnings[:5]:
            date = earning["created_at"].strftime("%d.%m.%Y")
            emoji = "✅" if earning["paid"] else "⏳"
            status = 'Выплачено' if earning['paid'] else 'Ожидает'
            text += (
                f"{emoji} {format_usdt(earning['amount'])} USDT\n"
                f"   Дата: {date}\n"
                f"   Статус: {status}\n\n"
            )

        if total_amount > 0:
            text += f"💰 Всего ожидает: *{format_usdt(total_amount)} USDT*\n"
    else:
        text += "У вас пока нет ожидающих выплат."

    await message.answer(
        text, parse_mode="Markdown", reply_markup=referral_keyboard()
    )


@router.message(F.text == "📊 Статистика рефералов")
async def handle_referral_stats(
    message: Message,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Show comprehensive referral statistics."""
    from urllib.parse import quote

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    referral_service = ReferralService(session)
    user_service = UserService(session)

    # Get referral stats
    stats = await referral_service.get_referral_stats(user.id)

    # Get today's earnings
    daily_stats = await referral_service.get_daily_earnings_stats(user.id, days=1)
    today_earned = daily_stats.get("today_earned", 0)

    # Get bot info for referral link
    from aiogram import Bot

    from app.config.settings import settings

    bot_username = settings.telegram_bot_username
    # Fallback: get from bot if not in settings
    if not bot_username:
        bot: Bot = data.get("bot")
        if bot:
            bot_info = await bot.get_me()
            bot_username = bot_info.username

    # Generate referral link (method now handles referral_code internally)
    referral_link = user_service.generate_referral_link(user, bot_username)

    # Get user position in leaderboard
    user_position = await referral_service.get_user_leaderboard_position(
        user.id
    )

    text = (
        f"📊 *Статистика рефералов*\n\n"
        f"*Ваша реферальная ссылка:*\n"
        f"`{referral_link}`\n\n"
        f"*Статистика:*\n"
        f"👥 Прямые партнеры: *{stats['direct_referrals']}*\n"
        f"👥 Уровень 2: *{stats['level2_referrals']}*\n"
        f"👥 Уровень 3: *{stats['level3_referrals']}*\n\n"
        f"*Доходы:*\n"
        f"🌟 *Сегодня: {format_usdt(today_earned)} USDT*\n"
        f"💵 Всего заработано: *{format_usdt(stats['total_earned'])} USDT*\n"
        f"⏳ Ожидает выплаты: "
        f"*{format_usdt(stats['pending_earnings'])} USDT*\n"
        f"✅ Выплачено: *{format_usdt(stats['paid_earnings'])} USDT*\n\n"
    )

    # Add leaderboard position if available
    referral_rank = user_position.get("referral_rank")
    earnings_rank = user_position.get("earnings_rank")
    total_users = user_position.get("total_users", 0)

    if referral_rank or earnings_rank:
        text += "*Ваша позиция в рейтинге:*\n"
        if referral_rank:
            text += f"📊 По рефералам: *{referral_rank}* из {total_users}\n"
        if earnings_rank:
            text += f"💰 По заработку: *{earnings_rank}* из {total_users}\n"
        text += "\n"

    text += (
        f"*Комиссии (от депозитов и дохода):*\n"
        f"• Уровень 1: *{int(REFERRAL_RATES[1] * 100)}%* "
        f"от прямых партнеров\n"
        f"• Уровень 2: *{int(REFERRAL_RATES[2] * 100)}%* "
        f"от партнеров 2-го уровня\n"
        f"• Уровень 3: *{int(REFERRAL_RATES[3] * 100)}%* "
        f"от партнеров 3-го уровня\n\n"
        f"💡 Приглашайте больше друзей и увеличивайте доход!"
    )

    # Create inline keyboard with share button
    share_text = (
        "🚀 Присоединяйся к ArbitroPLEX!\n\n"
        "💰 Зарабатывай от 0.8% до 1.2% в день\n"
        "👥 3-уровневая реферальная программа\n\n"
        f"Регистрируйся по ссылке: {referral_link}"
    )
    share_url = (
        f"https://t.me/share/url?url={quote(referral_link)}"
        f"&text={quote(share_text)}"
    )

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📤 Поделиться ссылкой",
                url=share_url,
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Копировать ссылку",
                callback_data="copy_ref_link",
            )
        ],
    ])

    await message.answer(
        text, parse_mode="Markdown", reply_markup=referral_keyboard()
    )

    # Send inline keyboard separately for share functionality
    await message.answer(
        "📤 *Поделитесь своей ссылкой:*",
        parse_mode="Markdown",
        reply_markup=inline_kb,
    )


@router.callback_query(F.data == "copy_ref_link")
async def handle_copy_ref_link(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Handle copy referral link button - send link as copyable message."""
    from aiogram import Bot

    from app.config.settings import settings

    user_service = UserService(session)

    bot_username = settings.telegram_bot_username
    if not bot_username:
        bot: Bot = data.get("bot")
        if bot:
            bot_info = await bot.get_me()
            bot_username = bot_info.username

    referral_link = user_service.generate_referral_link(user, bot_username)

    await callback.answer()
    await callback.message.answer(
        f"📋 *Ваша реферальная ссылка:*\n\n"
        f"`{referral_link}`\n\n"
        f"👆 Нажмите на ссылку чтобы скопировать",
        parse_mode="Markdown",
    )


@router.message(F.text == "📋 Скопировать ссылку")
async def handle_copy_link_button(
    message: Message,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Handle copy referral link reply button - instant copy."""
    from aiogram import Bot

    from app.config.settings import settings

    user_service = UserService(session)

    bot_username = settings.telegram_bot_username
    if not bot_username:
        bot: Bot = data.get("bot")
        if bot:
            bot_info = await bot.get_me()
            bot_username = bot_info.username

    referral_link = user_service.generate_referral_link(user, bot_username)

    await message.answer(
        f"📋 *Ваша реферальная ссылка:*\n\n"
        f"`{referral_link}`\n\n"
        f"👆 *Нажмите на ссылку чтобы скопировать*\n\n"
        f"💡 Отправьте её друзьям и получайте *5%* с их депозитов и дохода!",
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )


@router.message(F.text == "👤 Кто меня пригласил")
async def handle_who_invited_me(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show who invited this user (their referrer chain)."""
    referral_service = ReferralService(session)

    referrers_info = await referral_service.get_my_referrers(user.id)

    if not referrers_info["has_referrer"]:
        text = (
            "👤 *Кто меня пригласил*\n\n"
            "Вы зарегистрировались самостоятельно, без реферальной ссылки.\n\n"
            "💡 Вы тоже можете приглашать друзей и получать бонусы!"
        )
    else:
        text = "👤 *Ваша позиция в реферальной структуре*\n\n"

        for ref in referrers_info["referrers"]:
            level = ref["level"]
            username = ref["username"] or "без username"
            # Escape Markdown
            username = (
                username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
            )
            earned = ref["you_earned_them"]

            level_desc = {
                1: "Вас пригласил (прямой)",
                2: "Пригласивший вашего пригласившего",
                3: "Уровень 3",
            }.get(level, f"Уровень {level}")

            text += (
                f"*Уровень {level}:* @{username}\n"
                f"   └ {level_desc}\n"
                f"   └ Вы принесли им: *{format_usdt(earned)} USDT*\n\n"
            )

        text += (
            "💡 Чем больше вы зарабатываете и делаете депозитов, "
            "тем больше получают ваши пригласившие!"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )


@router.message(F.text == "📈 Аналитика")
async def handle_referral_analytics(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show detailed referral analytics."""
    referral_service = ReferralService(session)

    # Get all analytics data
    daily_stats = await referral_service.get_daily_earnings_stats(user.id, days=7)
    conversion_stats = await referral_service.get_referral_conversion_stats(user.id)
    activity_stats = await referral_service.get_referral_activity_stats(user.id)

    # Build text
    text = "📈 *Аналитика партнёрской программы*\n\n"

    # === Daily earnings chart ===
    text += "📊 *Заработок за последние 7 дней:*\n"

    if daily_stats["daily_stats"]:
        # Simple ASCII bar chart
        max_amount = max(
            (d["amount"] for d in daily_stats["daily_stats"]),
            default=0
        )

        for day_stat in daily_stats["daily_stats"][:7]:
            date_str = day_stat["date"].strftime("%d.%m")
            amount = day_stat["amount"]
            count = day_stat["count"]

            # Create bar
            if max_amount > 0:
                bar_len = int((float(amount) / float(max_amount)) * 8)
            else:
                bar_len = 0
            bar = "█" * bar_len + "░" * (8 - bar_len)

            text += f"`{date_str}` {bar} *{format_usdt(amount)}* ({count})\n"

        text += (
            f"\n💰 Итого за период: *{format_usdt(daily_stats['total_period'])} USDT*\n"
            f"📅 Сегодня: *{format_usdt(daily_stats['today_earned'])} USDT*\n"
            f"📊 В среднем/день: *{format_usdt(daily_stats['average_daily'])} USDT*\n"
        )
    else:
        text += "_Нет данных за этот период_\n"

    text += "\n"

    # === Conversion stats ===
    text += "🎯 *Конверсия рефералов:*\n"
    text += f"👥 Всего прямых рефералов: *{conversion_stats['total_referrals']}*\n"
    text += (
        f"✅ С депозитами: *{conversion_stats['referrals_with_deposits']}* "
        f"({conversion_stats['conversion_rate']:.1f}%)\n"
    )
    if conversion_stats['deposit_count'] > 0:
        total_dep = format_usdt(conversion_stats['total_deposits_amount'])
        avg_dep = format_usdt(conversion_stats['average_deposit'])
        text += (
            f"💵 Общий объём депозитов: *{total_dep} USDT*\n"
            f"📊 Средний депозит: *{avg_dep} USDT*\n"
        )
    text += "\n"

    # === Activity stats ===
    text += "🔥 *Активность рефералов (30 дней):*\n"
    text += f"🟢 Активных: *{activity_stats['active_referrals']}*\n"
    text += f"🔴 Неактивных: *{activity_stats['inactive_referrals']}*\n"
    text += f"📊 Активность: *{activity_stats['activity_rate']:.1f}%*\n\n"

    # By level breakdown
    text += "*По уровням:*\n"
    for level in [1, 2, 3]:
        level_data = activity_stats["by_level"].get(level, {"total": 0, "active": 0})
        total = level_data["total"]
        active = level_data["active"]
        text += f"   Ур.{level}: {active}/{total} активных\n"

    text += (
        "\n💡 *Совет:* Приглашайте активных пользователей - "
        "они приносят больше дохода!"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )


@router.message(F.text == "🌳 Моя структура")
async def handle_my_structure(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show beautiful referral structure tree."""
    referral_service = ReferralService(session)

    # Get stats for all levels
    stats = await referral_service.get_referral_stats(user.id)

    # Build visual tree
    text = "🌳 *Ваша реферальная структура*\n\n"

    # Main user (root)
    username = user.username or "Вы"
    username_escaped = (
        username.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
    )
    text += f"👤 *@{username_escaped}* (Вы)\n"

    # Level 1
    l1_count = stats['direct_referrals']
    text += "│\n"
    text += f"├─── 1️⃣ *Уровень 1* ({l1_count} чел.)\n"

    if l1_count > 0:
        # Get top 5 direct referrals
        result = await referral_service.get_referrals_by_level(
            user.id, level=1, page=1, limit=5
        )
        for i, ref in enumerate(result["referrals"]):
            ref_user = ref["user"]
            earned = ref["earned"]
            ref_name = ref_user.username or f"ID:{ref_user.telegram_id}"
            ref_name = (
                ref_name.replace("_", "\\_")
                .replace("*", "\\*")
            )
            is_last = (i == len(result["referrals"]) - 1) and l1_count <= 5
            prefix = "│   └──" if is_last else "│   ├──"
            status = "🟢" if earned > 0 else "⚪"
            text += f"{prefix} {status} @{ref_name} (+{format_usdt(earned)})\n"

        if l1_count > 5:
            text += f"│   └── _...и ещё {l1_count - 5} чел._\n"
    else:
        text += "│   └── _пока нет партнёров_\n"

    # Level 2
    l2_count = stats['level2_referrals']
    text += "│\n"
    text += f"├─── 2️⃣ *Уровень 2* ({l2_count} чел.)\n"

    if l2_count > 0:
        result = await referral_service.get_referrals_by_level(
            user.id, level=2, page=1, limit=3
        )
        for i, ref in enumerate(result["referrals"]):
            ref_user = ref["user"]
            earned = ref["earned"]
            ref_name = ref_user.username or f"ID:{ref_user.telegram_id}"
            ref_name = ref_name.replace("_", "\\_").replace("*", "\\*")
            is_last = (i == len(result["referrals"]) - 1) and l2_count <= 3
            prefix = "│   └──" if is_last else "│   ├──"
            status = "🟢" if earned > 0 else "⚪"
            text += f"{prefix} {status} @{ref_name}\n"

        if l2_count > 3:
            text += f"│   └── _...и ещё {l2_count - 3} чел._\n"
    else:
        text += "│   └── _пока нет партнёров_\n"

    # Level 3
    l3_count = stats['level3_referrals']
    text += "│\n"
    text += f"└─── 3️⃣ *Уровень 3* ({l3_count} чел.)\n"

    if l3_count > 0:
        result = await referral_service.get_referrals_by_level(
            user.id, level=3, page=1, limit=3
        )
        for i, ref in enumerate(result["referrals"]):
            ref_user = ref["user"]
            ref_name = ref_user.username or f"ID:{ref_user.telegram_id}"
            ref_name = ref_name.replace("_", "\\_").replace("*", "\\*")
            is_last = (i == len(result["referrals"]) - 1) and l3_count <= 3
            prefix = "    └──" if is_last else "    ├──"
            text += f"{prefix} ⚪ @{ref_name}\n"

        if l3_count > 3:
            text += f"    └── _...и ещё {l3_count - 3} чел._\n"
    else:
        text += "    └── _пока нет партнёров_\n"

    # Summary
    total = l1_count + l2_count + l3_count
    text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 *Итого:* {total} партнёров\n"
    text += f"💰 *Заработано:* {format_usdt(stats['total_earned'])} USDT\n"
    text += "\n🟢 = активный (есть доход)  ⚪ = новый"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )


@router.message(F.text == "🏆 ТОП партнёров")
async def handle_top_partners(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show public leaderboard of top partners."""
    referral_service = ReferralService(session)

    # Get leaderboard
    leaderboard = await referral_service.get_referral_leaderboard(limit=10)

    # Get platform stats
    platform_stats = await referral_service.get_platform_referral_stats()

    text = "🏆 *ТОП-10 партнёров ArbitroPLEX*\n\n"

    # Platform stats header
    total_earned = platform_stats.get('total_earnings', 0)
    total_refs = platform_stats.get('total_referrals', 0)
    text += f"📊 _Всего заработано партнёрами: {format_usdt(total_earned)} USDT_\n"
    text += f"👥 _Всего реферальных связей: {total_refs}_\n\n"

    # By referrals
    text += "📈 *По количеству рефералов:*\n"
    for entry in leaderboard["by_referrals"][:5]:
        rank = entry["rank"]
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        username = entry["username"] or f"ID:{entry['telegram_id']}"
        username = username.replace("_", "\\_").replace("*", "\\*")[:15]
        count = entry["referral_count"]
        text += f"{medal} @{username} — *{count}* реф.\n"

    text += "\n💰 *По заработку:*\n"
    for entry in leaderboard["by_earnings"][:5]:
        rank = entry["rank"]
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        username = entry["username"] or f"ID:{entry['telegram_id']}"
        username = username.replace("_", "\\_").replace("*", "\\*")[:15]
        earned = entry["total_earnings"]
        text += f"{medal} @{username} — *{format_usdt(earned)}* USDT\n"

    # User's position
    user_pos = await referral_service.get_user_leaderboard_position(user.id)
    if user_pos.get("referral_rank"):
        text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📍 *Ваша позиция:*\n"
        text += f"По рефералам: #{user_pos['referral_rank']}\n"
        text += f"По заработку: #{user_pos['earnings_rank']}\n"

    text += "\n💡 _Приглашайте друзей и поднимайтесь в рейтинге!_"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )


@router.message(F.text == "📢 Промо-материалы")
async def handle_promo_materials(
    message: Message,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Show promo materials including QR code and ready texts."""
    from aiogram import Bot
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from app.config.settings import settings

    user_service = UserService(session)

    bot_username = settings.telegram_bot_username
    if not bot_username:
        bot: Bot = data.get("bot")
        if bot:
            bot_info = await bot.get_me()
            bot_username = bot_info.username

    referral_link = user_service.generate_referral_link(user, bot_username)

    text = (
        "📢 *Промо-материалы*\n\n"
        "Используйте готовые тексты для привлечения партнёров:\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # Ready-made texts
    promo1 = (
        "📱 *Для Telegram/WhatsApp:*\n"
        "```\n"
        "🚀 Зарабатывай с ArbitroPLEX!\n\n"
        "💰 Доход 0.8-1.2% в ДЕНЬ\n"
        "👥 3-уровневая партнёрка (5%+5%+5%)\n"
        "🔒 Безопасно и прозрачно\n\n"
        f"Регистрируйся: {referral_link}\n"
        "```"
    )

    promo2 = (
        "📸 *Для Instagram/Stories:*\n"
        "```\n"
        "💎 Пассивный доход каждый день!\n\n"
        "Арбитраж криптовалют с ArbitroPLEX\n"
        "До 36% в месяц 📈\n\n"
        "Ссылка в профиле 👆\n"
        "```"
    )

    promo3 = (
        "🐦 *Короткий текст:*\n"
        f"```\n"
        f"ArbitroPLEX — зарабатывай на крипте!\n"
        f"Регистрация: {referral_link}\n"
        "```"
    )

    text += promo1 + "\n\n" + promo2 + "\n\n" + promo3 + "\n\n"

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 *Ваша ссылка:*\n`{referral_link}`\n\n"
        "💡 _Нажмите на текст чтобы скопировать_"
    )

    # QR code button (generates QR via external service)
    qr_url = (
        f"https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={referral_link}"
    )

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📱 Получить QR-код",
                url=qr_url,
            ),
        ],
        [
            InlineKeyboardButton(
                text="📋 Копировать ссылку",
                callback_data="copy_ref_link",
            ),
        ],
    ])

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )

    await message.answer(
        "⬇️ *Дополнительно:*",
        parse_mode="Markdown",
        reply_markup=inline_kb,
    )
