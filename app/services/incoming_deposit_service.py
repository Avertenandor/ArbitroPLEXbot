"""
Incoming deposit service.

Handles processing of incoming transfers detected on blockchain.

After consolidation:
- Each new USDT transaction creates a separate deposit
- Maximum 5 deposits per user
- Deposit requires PLEX payment before activation
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.business_constants import MAX_DEPOSITS_PER_USER
from app.config.operational_constants import (
    BLOCKING_TIMEOUT_DEFAULT,
    BLOCKING_TIMEOUT_SHORT,
    LOCK_TIMEOUT_MEDIUM,
    LOCK_TIMEOUT_SHORT,
)
from app.config.settings import settings
from app.models.deposit import Deposit
from app.models.user import User
from app.services.deposit import DepositService
from app.services.deposit.transaction_notifier import TransactionNotifier
from app.services.notification_service import NotificationService
from app.utils.distributed_lock import get_distributed_lock
from app.utils.formatters import escape_md
from app.utils.security import mask_address, mask_tx_hash


if TYPE_CHECKING:
    pass


class IncomingDepositService:
    """
    Service for processing incoming blockchain transfers.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis_client: Any | None = None
    ) -> None:
        """
        Initialize service.

        Args:
            session: Database session
            redis_client: Redis client for distributed locks
        """
        self.session = session
        self.redis_client = redis_client
        self.deposit_service = DepositService(session)
        self.notification_service = NotificationService(session)
        self.distributed_lock = get_distributed_lock(
            redis_client=redis_client,
            session=session
        )

    async def process_incoming_transfer(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        block_number: int,
    ) -> None:
        """
        Process an incoming transfer event.

        After consolidation phase:
        - Each new USDT transaction = separate deposit
        - Maximum 5 deposits per user
        - Deposit requires PLEX payment before work activation

        Args:
            tx_hash: Transaction hash
            from_address: Sender address
            to_address: Recipient address (should be system wallet)
            amount: Amount in USDT
            block_number: Block number
        """
        logger.info(
            f"📥 Processing incoming transfer: {amount} USDT "
            f"from {mask_address(from_address)} (TX: {mask_tx_hash(tx_hash)})"
        )

        # Distributed lock for transaction processing to prevent duplicates
        lock_key = f"deposit_process:{tx_hash}"
        async with self.distributed_lock.lock(
            lock_key,
            timeout=LOCK_TIMEOUT_MEDIUM,
            blocking=True,
            blocking_timeout=BLOCKING_TIMEOUT_DEFAULT
        ) as acquired:
            if not acquired:
                logger.warning(
                    f"Could not acquire lock for processing deposit {tx_hash}. "
                    "Another process may be handling it."
                )
                return

            # 1. Idempotency Check (inside lock to prevent race conditions)
            existing_deposit = await self.session.execute(
                select(Deposit).where(Deposit.tx_hash == tx_hash)
            )
            if existing_deposit.scalars().first():
                logger.info(f"⏩ Deposit {tx_hash} already processed. Skipping.")
                return

            await self._process_deposit_internal(
                tx_hash, from_address, to_address, amount, block_number
            )

    async def _process_deposit_internal(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        block_number: int,
    ) -> None:
        """
        Internal method to process deposit after lock is acquired.

        Args:
            tx_hash: Transaction hash
            from_address: Sender address
            to_address: Recipient address
            amount: Amount in USDT
            block_number: Block number
        """

        # Verify Recipient
        if to_address.lower() != settings.system_wallet_address.lower():
            logger.warning(
                f"⚠️ Transfer recipient mismatch: "
                f"{to_address} != {settings.system_wallet_address}"
            )
            return

        # User Identification
        user_result = await self.session.execute(
            select(User).where(User.wallet_address.ilike(from_address))
        )
        user = user_result.scalars().first()

        if not user:
            # User NOT found
            logger.warning(f"⚠️ Unidentified deposit from {mask_address(from_address)}")
            await self.notification_service.notify_admins(
                f"⚠️ **НЕОПОЗНАННЫЙ ДЕПОЗИТ**\n\n"
                f"Сумма: `{amount} USDT`\n"
                f"От: `{from_address}`\n"
                f"TX: `{tx_hash}`\n\n"
                f"Кошелек не привязан ни к одному пользователю!\n"
                f"Требуется ручная проверка."
            )
            return

        logger.info(f"✅ Identified user {user.id} for wallet {mask_address(from_address)}")

        # User-level lock to prevent concurrent deposit creation for same user
        user_lock_key = f"user_deposit:{user.id}"
        async with self.distributed_lock.lock(
            user_lock_key,
            timeout=LOCK_TIMEOUT_SHORT,
            blocking=True,
            blocking_timeout=BLOCKING_TIMEOUT_SHORT
        ) as user_lock_acquired:
            if not user_lock_acquired:
                logger.warning(
                    f"Could not acquire user lock for user {user.id}. "
                    "Concurrent deposit operation in progress."
                )
                await self.notification_service.notify_admins(
                    f"⚠️ **Блокировка пользователя не получена**\n"
                    f"User: {user.id}\n"
                    f"TX: `{tx_hash}`\n"
                    f"Требуется повторная обработка."
                )
                return

            # Check deposit limit (max 5 deposits per user) - inside user lock
            active_deposits_count = await self._get_active_deposits_count(user.id)
            if active_deposits_count >= MAX_DEPOSITS_PER_USER:
                logger.warning(
                    f"⚠️ User {user.id} has reached deposit limit "
                    f"({active_deposits_count}/{MAX_DEPOSITS_PER_USER})"
                )
                await self.notification_service.notify_user(
                    user.id,
                    f"⚠️ **Депозит не может быть создан**\n\n"
                    f"Вы достигли лимита в {MAX_DEPOSITS_PER_USER} депозитов.\n"
                    f"Сумма: `{amount} USDT`\n"
                    f"TX: `{tx_hash}`\n\n"
                    "Дождитесь завершения одного из текущих депозитов "
                    "или обратитесь в поддержку."
                )
                await self.notification_service.notify_admins(
                    f"⚠️ **Депозит отклонен - лимит**\n"
                    f"User: {user.id}\n"
                    f"Amount: {amount} USDT\n"
                    f"Active deposits: {active_deposits_count}/{MAX_DEPOSITS_PER_USER}\n"
                    f"TX: `{tx_hash}`"
                )
                return

            await self._create_deposit_for_user(
                user, tx_hash, from_address, amount, block_number, active_deposits_count
            )

    async def _create_deposit_for_user(
        self,
        user: User,
        tx_hash: str,
        from_address: str,
        amount: Decimal,
        block_number: int,
        active_deposits_count: int,
    ) -> None:
        """
        Create deposit for user after all checks passed.

        Args:
            user: User object
            tx_hash: Transaction hash
            from_address: Sender address
            amount: Amount in USDT
            block_number: Block number
            active_deposits_count: Current active deposits count
        """

        try:
            # Create new deposit (each transaction = separate deposit)
            now = datetime.now(UTC)
            daily_plex_required = amount * Decimal(str(settings.plex_per_dollar_daily))

            # Determine level based on deposit count (1-5)
            level = active_deposits_count + 1

            deposit = await self.deposit_service.create_deposit(
                user_id=user.id,
                level=level,
                amount=amount,
                tx_hash=tx_hash,
                redis_client=self.redis_client  # Pass redis_client for distributed lock
            )

            # Update deposit with additional info
            deposit.block_number = block_number
            deposit.wallet_address = from_address
            deposit.plex_cycle_start = now  # Individual 24h cycle starts now
            await self.session.commit()

            # Confirm deposit
            await self.deposit_service.confirm_deposit(deposit.id, block_number)

            # Send transaction notification using TransactionNotifier
            try:
                # Create bot instance for notifications (app layer is independent of bot layer)
                bot = Bot(
                    token=settings.telegram_bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
                )

                notifier = TransactionNotifier(bot, self.session)
                await notifier.notify_usdt_received(
                    user_telegram_id=user.telegram_id,
                    amount=amount,
                    tx_hash=tx_hash,
                    deposit_id=deposit.id,
                    plex_daily=daily_plex_required,
                )
            except Exception as notif_error:
                logger.warning(f"Failed to send transaction notification: {notif_error}")
                # Fallback to old notification method
                await self.notification_service.notify_user(
                    user.id,
                    f"✅ **Новый депозит зарегистрирован!**\n\n"
                    f"💰 Сумма: `{amount} USDT`\n"
                    f"📊 Депозит #{deposit.id}\n"
                    f"🔗 TX: `{tx_hash[:16]}...`\n\n"
                    f"⚠️ **ВАЖНО: Для активации депозита**\n"
                    f"Необходимо оплатить: **{int(daily_plex_required):,} PLEX**\n\n"
                    f"💳 Кошелек для оплаты:\n"
                    f"`{settings.system_wallet_address}`\n\n"
                    f"После оплаты PLEX депозит начнет работать.\n"
                    f"Оплата требуется ежедневно (10 PLEX за каждый $1).\n"
                    f"Ваши индивидуальные сутки начнутся с момента первой оплаты."
                )

            # Notify admins
            username = escape_md(user.username) if user.username else "без юзернейма"
            await self.notification_service.notify_admins(
                f"💰 **Новый депозит создан**\n"
                f"User: {user.id} (@{username})\n"
                f"Amount: {amount} USDT\n"
                f"Deposit #{deposit.id}, Level {level}\n"
                f"Daily PLEX: {int(daily_plex_required):,}\n"
                f"TX: `{tx_hash}`"
            )

            logger.info(
                f"✅ Created new deposit #{deposit.id} for user {user.id}: "
                f"{amount} USDT, daily PLEX: {daily_plex_required}"
            )

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Failed to process deposit for user {user.id}: {e}")
            await self.notification_service.notify_admins(
                f"❌ **Ошибка обработки депозита**\n"
                f"User: {user.id}\n"
                f"TX: `{tx_hash}`\n"
                f"Error: {str(e)}"
            )

    async def _get_active_deposits_count(self, user_id: int) -> int:
        """
        Get count of active (non-completed) deposits for user.

        Args:
            user_id: User ID

        Returns:
            Number of active deposits
        """
        result = await self.session.execute(
            select(func.count(Deposit.id)).where(
                Deposit.user_id == user_id,
                Deposit.status == "confirmed",
                Deposit.is_roi_completed is False,
            )
        )
        return result.scalar() or 0
