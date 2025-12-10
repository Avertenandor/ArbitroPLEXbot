"""
Сервис уведомлений о PLEX платежах.
Отправляет пользователям уведомления о статусе их PLEX платежей.
"""
import asyncio
from decimal import Decimal

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import TELEGRAM_TIMEOUT


class PlexPaymentNotifier:
    """Уведомления о PLEX платежах."""

    def __init__(self, bot: Bot, session: AsyncSession):
        """
        Initialize notifier.

        Args:
            bot: Bot instance
            session: Database session
        """
        self.bot = bot
        self.session = session

    async def notify_payment_required(
        self,
        user_telegram_id: int,
        deposit_id: int,
        amount: Decimal,
        level_name: str,
        deadline_hours: int = 24
    ) -> bool:
        """
        Уведомить о необходимости PLEX платежа.

        Args:
            user_telegram_id: Telegram ID пользователя
            deposit_id: ID депозита
            amount: Сумма PLEX для платежа
            level_name: Название уровня депозита
            deadline_hours: Срок оплаты в часах

        Returns:
            True если уведомление отправлено успешно
        """
        message = (
            f"📢 *Требуется оплата PLEX*\n\n"
            f"Депозит: *{level_name}*\n"
            f"Требуется: *{amount:.2f} PLEX*\n"
            f"Срок: *{deadline_hours} часов*\n\n"
            f"💡 Отправьте PLEX на системный кошелёк"
        )

        return await self._send_notification(user_telegram_id, message)

    async def notify_payment_received(
        self,
        user_telegram_id: int,
        deposit_id: int,
        amount: Decimal,
        tx_hash: str
    ) -> bool:
        """
        Уведомить о получении PLEX платежа.

        Args:
            user_telegram_id: Telegram ID пользователя
            deposit_id: ID депозита
            amount: Сумма полученного PLEX
            tx_hash: Хеш транзакции

        Returns:
            True если уведомление отправлено успешно
        """
        # Сокращаем хеш для отображения
        tx_hash_short = (
            f"{tx_hash[:8]}...{tx_hash[-6:]}"
            if len(tx_hash) > 20
            else tx_hash
        )

        message = (
            f"✅ *PLEX платёж получен!*\n\n"
            f"Получено: *{amount:.2f} PLEX*\n"
            f"TX: `{tx_hash_short}`\n\n"
            f"Следующий платёж через 24 часа"
        )

        return await self._send_notification(user_telegram_id, message)

    async def notify_warning(
        self,
        user_telegram_id: int,
        deposit_id: int,
        hours_left: int,
        required_amount: Decimal
    ) -> bool:
        """
        Предупреждение об истекающем сроке платежа.

        Args:
            user_telegram_id: Telegram ID пользователя
            deposit_id: ID депозита
            hours_left: Часов до блокировки
            required_amount: Требуемая сумма PLEX

        Returns:
            True если уведомление отправлено успешно
        """
        message = (
            f"⚠️ *Внимание! Требуется PLEX платёж*\n\n"
            f"Депозит будет заблокирован через *{hours_left} часов*\n"
            f"Требуется: *{required_amount:.2f} PLEX*\n\n"
            f"⏰ Отправьте платёж немедленно!"
        )

        return await self._send_notification(user_telegram_id, message)

    async def notify_deposit_blocked(
        self,
        user_telegram_id: int,
        deposit_id: int,
        reason: str = "Не получен PLEX платёж"
    ) -> bool:
        """
        Уведомить о блокировке депозита.

        Args:
            user_telegram_id: Telegram ID пользователя
            deposit_id: ID депозита
            reason: Причина блокировки

        Returns:
            True если уведомление отправлено успешно
        """
        message = (
            f"❌ *Депозит заблокирован*\n\n"
            f"Причина: {reason}\n\n"
            f"Для разблокировки обратитесь в поддержку"
        )

        return await self._send_notification(user_telegram_id, message)

    async def notify_deposit_activated(
        self,
        user_telegram_id: int,
        deposit_id: int,
        level_name: str,
        amount: Decimal,
        plex_daily: Decimal
    ) -> bool:
        """
        Уведомить об активации депозита.

        Args:
            user_telegram_id: Telegram ID пользователя
            deposit_id: ID депозита
            level_name: Название уровня депозита
            amount: Сумма депозита в USDT
            plex_daily: Ежедневное требование PLEX

        Returns:
            True если уведомление отправлено успешно
        """
        message = (
            f"🎉 *Депозит активирован!*\n\n"
            f"Уровень: *{level_name}*\n"
            f"Сумма: *${amount:.2f} USDT*\n"
            f"Ежедневный PLEX: *{plex_daily:.2f} токенов*\n\n"
            f"💰 ROI начисления начнутся после первого PLEX платежа"
        )

        return await self._send_notification(user_telegram_id, message)

    async def _send_notification(
        self,
        user_telegram_id: int,
        message: str
    ) -> bool:
        """
        Отправить уведомление пользователю.

        Args:
            user_telegram_id: Telegram ID пользователя
            message: Текст сообщения

        Returns:
            True если сообщение отправлено успешно
        """
        try:
            await asyncio.wait_for(
                self.bot.send_message(
                    chat_id=user_telegram_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            logger.info(
                f"PLEX notification sent to user {user_telegram_id}"
            )
            return True
        except TimeoutError:
            logger.warning(
                f"Timeout sending PLEX notification to user {user_telegram_id}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to send PLEX notification to user {user_telegram_id}: {e}",
                extra={"user_id": user_telegram_id},
            )
            return False
