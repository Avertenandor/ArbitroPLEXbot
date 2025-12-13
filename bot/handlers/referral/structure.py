"""
Referral Structure Module - REPLY KEYBOARDS ONLY!

Handles referral chain and structure visualization.
This module contains:
- Handler for viewing who invited the user (referrer chain)
- Handler for viewing user's referral structure as a tree
"""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.referral_service import ReferralService
from bot.keyboards.reply import referral_keyboard
from bot.utils.formatters import format_balance


router = Router(name="referral_structure")


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
                f"   └ Вы принесли им: *{format_balance(earned, 2)} USDT*\n\n"
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
            text += f"{prefix} {status} @{ref_name} (+{format_balance(earned, 2)})\n"

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
    text += f"💰 *Заработано:* {format_balance(stats['total_earned'], 2)} USDT\n"
    text += "\n🟢 = активный (есть доход)  ⚪ = новый"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )
