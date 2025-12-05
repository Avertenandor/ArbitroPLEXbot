"""
User-specific notification functionality.

Handles notifications for withdrawals, ROI accruals, and other user-specific events.
"""

import asyncio

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import TELEGRAM_TIMEOUT


class UserNotificationMixin:
    """
    Mixin for user-specific notification methods.

    Provides methods for notifying users about withdrawals, ROI, etc.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user notification mixin."""
        self.session = session

    async def notify_withdrawal_processed(
        self, telegram_id: int, amount: float, tx_hash: str
    ) -> bool:
        """
        Notify user about withdrawal being processed.

        Args:
            telegram_id: User telegram ID
            amount: Withdrawal amount
            tx_hash: Transaction hash

        Returns:
            True if notification sent successfully
        """
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        from app.config.settings import settings
        from bot.main import bot_instance

        bot = bot_instance
        should_close = False

        if not bot:
            try:
                bot = Bot(
                    token=settings.telegram_bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
                )
                should_close = True
            except Exception as e:
                logger.error(f"Failed to create fallback bot instance: {e}")
                return False

        message = (
            f"✅ **Выплата отправлена!**\n\n"
            f"💰 Сумма: {amount:.2f} USDT\n"
            f"🔗 TX: [Посмотреть транзакцию](https://bscscan.com/tx/{tx_hash})\n\n"
            f"🤝 Спасибо за ваше доверие к ArbitroPLEXbot!"
        )

        try:
            await asyncio.wait_for(
                bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            return True
        except TimeoutError:
            logger.warning(f"Timeout notifying user {telegram_id} about withdrawal")
            return False
        except Exception as e:
            logger.error(
                f"Failed to notify user about withdrawal: {e}",
                extra={"telegram_id": telegram_id},
            )
            return False
        finally:
            if should_close and bot:
                await bot.session.close()

    async def notify_withdrawal_rejected(
        self, telegram_id: int, amount: float
    ) -> bool:
        """
        Notify user about withdrawal being rejected.

        Args:
            telegram_id: User telegram ID
            amount: Withdrawal amount

        Returns:
            True if notification sent successfully
        """
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        from app.config.settings import settings
        from bot.main import bot_instance

        bot = bot_instance
        should_close = False

        if not bot:
            try:
                bot = Bot(
                    token=settings.telegram_bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
                )
                should_close = True
            except Exception as e:
                logger.error(f"Failed to create fallback bot instance: {e}")
                return False

        message = (
            f"❌ **Ваша заявка на вывод средств отклонена**\n\n"
            f"💰 Сумма: {amount:.2f} USDT\n\n"
            f"Для получения дополнительной информации обратитесь в поддержку."
        )

        try:
            await asyncio.wait_for(
                bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode="Markdown",
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            return True
        except TimeoutError:
            logger.warning(f"Timeout notifying user {telegram_id} about withdrawal rejection")
            return False
        except Exception as e:
            logger.error(
                f"Failed to notify user about withdrawal rejection: {e}",
                extra={"telegram_id": telegram_id},
            )
            return False
        finally:
            if should_close and bot:
                await bot.session.close()

    async def notify_roi_accrual(
        self,
        telegram_id: int,
        amount: float,
        deposit_level: int,
        roi_progress_percent: float,
    ) -> bool:
        """
        Notify user about ROI accrual.

        Args:
            telegram_id: User telegram ID
            amount: ROI amount accrued
            deposit_level: Deposit level
            roi_progress_percent: Current ROI progress (0-100%)

        Returns:
            True if notification sent successfully
        """
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        from app.config.settings import settings
        from bot.main import bot_instance

        bot = bot_instance
        should_close = False

        if not bot:
            try:
                bot = Bot(
                    token=settings.telegram_bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
                )
                should_close = True
            except Exception as e:
                logger.error(f"Failed to create fallback bot instance: {e}")
                return False

        # Progress bar (10 blocks for 100% progress)
        filled = int(roi_progress_percent / 10)  # 10 blocks for 100%
        empty = 10 - filled
        progress_bar = "█" * filled + "░" * empty

        message = (
            f"💰 *Начислен ROI*\n\n"
            f"📊 Уровень {deposit_level}: *+{amount:.2f} USDT*\n"
            f"📈 Прогресс: {progress_bar} {roi_progress_percent:.1f}%\n\n"
            f"_Баланс обновлён автоматически._"
        )

        try:
            await asyncio.wait_for(
                bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode="Markdown",
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            return True
        except TimeoutError:
            logger.warning(f"Timeout notifying user {telegram_id} about ROI accrual")
            return False
        except Exception as e:
            logger.error(
                f"Failed to notify user about ROI accrual: {e}",
                extra={"telegram_id": telegram_id},
            )
            return False
        finally:
            if should_close and bot:
                await bot.session.close()
