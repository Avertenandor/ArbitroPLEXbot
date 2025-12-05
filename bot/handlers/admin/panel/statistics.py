"""
Admin Platform Statistics Handler

Provides comprehensive platform statistics including:
- User statistics (total, verified)
- Deposit statistics by level
- Detailed active deposit information
- Referral statistics by level
- Withdrawal statistics with transaction details
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deposit_service import DepositService
from app.services.referral_service import ReferralService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_keyboard
from bot.utils.formatters import format_usdt

router = Router(name="admin_panel_statistics")


@router.message(F.text == "📊 Статистика")
async def handle_admin_stats(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle platform statistics"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.services.withdrawal_service import WithdrawalService

    user_service = UserService(session)
    deposit_service = DepositService(session)
    referral_service = ReferralService(session)
    withdrawal_service = WithdrawalService(session)

    # Get statistics
    total_users = await user_service.get_total_users()
    verified_users = await user_service.get_verified_users()
    deposit_stats = await deposit_service.get_platform_stats()
    referral_stats = await referral_service.get_platform_referral_stats()
    withdrawal_stats = await withdrawal_service.get_platform_withdrawal_stats()

    # R4-X: Detailed deposit stats
    detailed_deposits = await deposit_service.get_detailed_stats()

    text = f"""
📊 **Статистика платформы**

**Пользователи:**
👥 Всего: {total_users}
✅ Верифицированы: {verified_users}
❌ Не верифицированы: {total_users - verified_users}

**Депозиты:**
💰 Всего депозитов: {deposit_stats["total_deposits"]}
💵 Общая сумма: {format_usdt(deposit_stats["total_amount"])} USDT
👤 Пользователей с депозитами: {deposit_stats["total_users"]}

**По уровням:**
• Уровень 1: {deposit_stats["deposits_by_level"].get(1, 0)} депозитов
• Уровень 2: {deposit_stats["deposits_by_level"].get(2, 0)} депозитов
• Уровень 3: {deposit_stats["deposits_by_level"].get(3, 0)} депозитов
• Уровень 4: {deposit_stats["deposits_by_level"].get(4, 0)} депозитов
• Уровень 5: {deposit_stats["deposits_by_level"].get(5, 0)} депозитов

**📋 Детализация активных депозитов:**
"""

    if not detailed_deposits:
        text += "Нет активных депозитов.\n"
    else:
        for d in detailed_deposits[:10]:  # Show top 10 recent
            next_accrual = d["next_accrual_at"].strftime("%d.%m %H:%M") if d["next_accrual_at"] else "Н/Д"

            # Escape username for Markdown
            username = str(d['username'])
            safe_username = username.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

            text += (
                f"👤 @{safe_username} (ID: {d['user_id']})\n"
                f"   💵 Деп: {format_usdt(d['amount'])} | Начислено: {format_usdt(d['roi_paid'])}\n"
                f"   ⏳ След. нач: {next_accrual}\n\n"
            )

        if len(detailed_deposits) > 10:
            text += f"... и еще {len(detailed_deposits) - 10} депозитов\n"

    # Get referral level stats
    lvl1 = referral_stats["by_level"].get(1, {})
    lvl2 = referral_stats["by_level"].get(2, {})
    lvl3 = referral_stats["by_level"].get(3, {})
    lvl1_count = lvl1.get("count", 0)
    lvl1_earn = format_usdt(lvl1.get("earnings", 0))
    lvl2_count = lvl2.get("count", 0)
    lvl2_earn = format_usdt(lvl2.get("earnings", 0))
    lvl3_count = lvl3.get("count", 0)
    lvl3_earn = format_usdt(lvl3.get("earnings", 0))

    text += f"""
**Рефералы:**
🤝 Всего связей: {referral_stats["total_referrals"]}
💰 Всего начислено: {format_usdt(referral_stats["total_earnings"])} USDT
✅ Выплачено: {format_usdt(referral_stats["paid_earnings"])} USDT
⏳ Ожидает выплаты: {format_usdt(referral_stats["pending_earnings"])} USDT

**По уровням:**
• Уровень 1: {lvl1_count} ({lvl1_earn} USDT)
• Уровень 2: {lvl2_count} ({lvl2_earn} USDT)
• Уровень 3: {lvl3_count} ({lvl3_earn} USDT)

**💸 Выводы на кошельки:**
✅ Выведено: {format_usdt(withdrawal_stats["total_confirmed_amount"])} USDT ({withdrawal_stats["total_confirmed"]} транз.)
❌ Неудачных: {withdrawal_stats["total_failed"]} ({format_usdt(withdrawal_stats["total_failed_amount"])} USDT)
"""

    # Add per-user withdrawal summary
    if withdrawal_stats["by_user"]:
        text += "\n**По пользователям:**\n"
        for wu in withdrawal_stats["by_user"][:5]:
            wu_username = str(wu["username"] or "Без имени")
            safe_wu_username = (
                wu_username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            text += f"• @{safe_wu_username}: {format_usdt(wu['total_withdrawn'])} USDT\n"

    # Add detailed withdrawals with tx_hash
    detailed_wd = await withdrawal_service.get_detailed_withdrawals(page=1, per_page=5)
    if detailed_wd["withdrawals"]:
        text += "\n**📋 Детализация (с хешами):**\n"
        for wd in detailed_wd["withdrawals"]:
            wd_username = str(wd["username"] or "Без имени")
            safe_wd_username = (
                wd_username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            tx_short = wd["tx_hash"][:10] + "..." if wd["tx_hash"] else "N/A"
            text += f"• @{safe_wd_username}: {format_usdt(wd['amount'])} | `{tx_short}`\n"

        if detailed_wd["total_pages"] > 1:
            text += f"\n_Стр. {detailed_wd['page']}/{detailed_wd['total_pages']}_ | Нажми 📋 для навигации"

    text = text.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(
            is_super_admin=admin.is_super_admin,
            is_extended_admin=admin.is_extended_admin
        ),
    )
