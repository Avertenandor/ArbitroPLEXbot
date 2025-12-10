"""
Уведомления о транзакциях на системный кошелёк.
"""
import asyncio
from decimal import Decimal

from aiogram import Bot
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import TELEGRAM_TIMEOUT
from app.models.deposit import Deposit
from bot.constants.rules import SYSTEM_WALLET


class TransactionNotifier:
    """Уведомления о входящих транзакциях."""

    def __init__(self, bot: Bot, session: AsyncSession):
        """
        Инициализация notifier.

        Args:
            bot: Bot instance
            session: Database session
        """
        self.bot = bot
        self.session = session

    async def notify_usdt_received(
        self,
        user_telegram_id: int,
        amount: Decimal,
        tx_hash: str,
        deposit_id: int,
        plex_daily: Decimal
    ) -> bool:
        """
        Уведомить о получении USDT.

        Args:
            user_telegram_id: Telegram ID пользователя
            amount: Сумма USDT
            tx_hash: Хэш транзакции
            deposit_id: ID депозита
            plex_daily: Требуемый ежедневный PLEX платёж

        Returns:
            True если уведомление отправлено успешно
        """
        tx_hash_short = f"{tx_hash[:8]}...{tx_hash[-6:]}" if len(tx_hash) > 20 else tx_hash

        message = (
            f"✅ *Получен USDT платёж!*\n\n"
            f"💰 Сумма: *{amount} USDT*\n"
            f"🔗 TX: `{tx_hash_short}`\n\n"
            f"📊 Ваш депозит активирован.\n"
            f"⚡️ Теперь требуется ежедневный PLEX платёж: *{int(plex_daily):,} токенов*\n\n"
            f"💳 Адрес для PLEX платежей:\n"
            f"`{SYSTEM_WALLET}`\n\n"
            f"💡 Депозит #{deposit_id} готов к работе!"
        )

        return await self._send_message(user_telegram_id, message)

    async def notify_plex_received(
        self,
        user_telegram_id: int,
        amount: Decimal,
        tx_hash: str,
        deposit_id: int,
        next_payment_hours: int = 24
    ) -> bool:
        """
        Уведомить о получении PLEX.

        Args:
            user_telegram_id: Telegram ID пользователя
            amount: Сумма PLEX
            tx_hash: Хэш транзакции
            deposit_id: ID депозита
            next_payment_hours: Часов до следующего платежа

        Returns:
            True если уведомление отправлено успешно
        """
        tx_hash_short = f"{tx_hash[:8]}...{tx_hash[-6:]}" if len(tx_hash) > 20 else tx_hash

        # Получить информацию о депозите для расчета требуемого PLEX
        deposit_info = await self._get_deposit_info(deposit_id)
        if not deposit_info:
            logger.warning(f"Deposit {deposit_id} not found for PLEX notification")
            return False

        daily_plex = deposit_info["plex_daily_required"]

        message = (
            f"✅ *PLEX платёж получен!*\n\n"
            f"💎 Получено: *{int(amount):,} PLEX*\n"
            f"🔗 TX: `{tx_hash_short}`\n\n"
            f"⏰ Следующий платёж через {next_payment_hours} часа.\n"
            f"💰 Требуется: *{int(daily_plex):,} PLEX*\n\n"
            f"📈 Депозит #{deposit_id} продолжает работать!"
        )

        return await self._send_message(user_telegram_id, message)

    async def notify_insufficient_amount(
        self,
        user_telegram_id: int,
        received: Decimal,
        expected_min: Decimal,
        token_type: str  # "USDT" or "PLEX"
    ) -> bool:
        """
        Уведомить о недостаточной сумме.

        Args:
            user_telegram_id: Telegram ID пользователя
            received: Полученная сумма
            expected_min: Минимально ожидаемая сумма
            token_type: Тип токена ("USDT" или "PLEX")

        Returns:
            True если уведомление отправлено успешно
        """
        emoji = "💰" if token_type == "USDT" else "💎"

        message = (
            f"⚠️ *Недостаточная сумма {token_type}*\n\n"
            f"{emoji} Получено: *{received} {token_type}*\n"
            f"❌ Требуется минимум: *{expected_min} {token_type}*\n\n"
            f"📍 Пожалуйста, отправьте недостающую сумму:\n"
            f"`{SYSTEM_WALLET}`\n\n"
            f"💡 После получения полной суммы депозит будет активирован."
        )

        return await self._send_message(user_telegram_id, message)

    async def _get_deposit_info(self, deposit_id: int) -> dict | None:
        """
        Получить информацию о депозите.

        Args:
            deposit_id: ID депозита

        Returns:
            Dict с информацией или None
        """
        stmt = select(Deposit).where(Deposit.id == deposit_id)
        result = await self.session.execute(stmt)
        deposit = result.scalar_one_or_none()

        if not deposit:
            return None

        return {
            "level": deposit.level,
            "amount": deposit.amount,
            "plex_daily_required": deposit.plex_daily_required,
        }

    async def _send_message(
        self,
        telegram_id: int,
        message: str,
    ) -> bool:
        """
        Отправить сообщение пользователю.

        Args:
            telegram_id: Telegram ID пользователя
            message: Текст сообщения

        Returns:
            True если сообщение отправлено успешно
        """
        try:
            await asyncio.wait_for(
                self.bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                ),
                timeout=TELEGRAM_TIMEOUT,
            )

            logger.debug(f"Transaction notification sent to user {telegram_id}")
            return True

        except TimeoutError:
            logger.warning(
                f"Timeout sending transaction notification to user {telegram_id}"
            )
            return False

        except Exception as e:
            logger.error(
                f"Failed to send transaction notification to user {telegram_id}: {e}"
            )
            return False
