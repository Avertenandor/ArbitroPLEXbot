"""
Referral notifications.

Handles notifications for referral events.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger


if TYPE_CHECKING:
    from aiogram import Bot


async def notify_new_referral(
    bot: "Bot",
    referrer_telegram_id: int,
    new_user_username: str | None,
    new_user_telegram_id: int,
) -> bool:
    """
    Notify referrer about new referral registration.

    Args:
        bot: Telegram bot instance
        referrer_telegram_id: Referrer's Telegram ID
        new_user_username: New user's username
        new_user_telegram_id: New user's Telegram ID

    Returns:
        True if notification sent successfully
    """
    try:
        if new_user_username:
            user_display = f"@{new_user_username}"
        else:
            user_display = f"ID:{new_user_telegram_id}"

        text = (
            "🎉 *Новый реферал!*\n\n"
            f"Пользователь {user_display} зарегистрировался "
            "по вашей реферальной ссылке.\n\n"
            "💰 Вы будете получать 5% от его депозитов и дохода!"
        )

        await bot.send_message(
            referrer_telegram_id,
            text,
            parse_mode="Markdown",
        )

        logger.info(
            "New referral notification sent",
            extra={
                "referrer_telegram_id": referrer_telegram_id,
                "new_user_telegram_id": new_user_telegram_id,
            },
        )
        return True

    except Exception as e:
        logger.warning(
            "Failed to send new referral notification",
            extra={
                "referrer_telegram_id": referrer_telegram_id,
                "error": str(e),
            },
        )
        return False


async def notify_referral_reward(
    bot: "Bot",
    referrer_telegram_id: int,
    reward_amount: Decimal,
    level: int,
    source_username: str | None,
    source_telegram_id: int,
    reward_type: str,  # "deposit" or "roi"
) -> bool:
    """
    Notify referrer about received referral reward.

    Args:
        bot: Telegram bot instance
        referrer_telegram_id: Referrer's Telegram ID
        reward_amount: Reward amount in USDT
        level: Referral level (1-3)
        source_username: Source user's username
        source_telegram_id: Source user's Telegram ID
        reward_type: Type of reward ("deposit" or "roi")

    Returns:
        True if notification sent successfully
    """
    try:
        if source_username:
            user_display = f"@{source_username}"
        else:
            user_display = f"ID:{source_telegram_id}"

        source_text = "депозита" if reward_type == "deposit" else "дохода"
        level_emoji = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣"}.get(level, "🔢")

        text = (
            f"💰 *Реферальный бонус!*\n\n"
            f"Вы получили *{reward_amount:.4f} USDT*\n"
            f"От {source_text} {user_display}\n"
            f"{level_emoji} Уровень: {level}\n\n"
            f"Баланс пополнен автоматически."
        )

        await bot.send_message(
            referrer_telegram_id,
            text,
            parse_mode="Markdown",
        )

        logger.debug(
            "Referral reward notification sent",
            extra={
                "referrer_telegram_id": referrer_telegram_id,
                "reward_amount": str(reward_amount),
                "level": level,
            },
        )
        return True

    except Exception as e:
        logger.warning(
            "Failed to send referral reward notification",
            extra={
                "referrer_telegram_id": referrer_telegram_id,
                "error": str(e),
            },
        )
        return False
