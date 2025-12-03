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

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.models.user import User
from app.services.deposit_service import DepositService
from app.services.notification_service import NotificationService
from app.utils.security import mask_address, mask_tx_hash
from bot.constants.rules import (
    MAX_DEPOSITS_PER_USER,
    MINIMUM_PLEX_BALANCE,
    PLEX_PER_DOLLAR_DAILY,
    SYSTEM_WALLET,
    WorkStatus,
)
from bot.utils.formatters import escape_md

class IncomingDepositService:
    """
    Service for processing incoming blockchain transfers.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize service.

        Args:
            session: Database session
        """
        self.session = session
        self.deposit_service = DepositService(session)
        self.notification_service = NotificationService(session)

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

        # 1. Idempotency Check
        existing_deposit = await self.session.execute(
            select(Deposit).where(Deposit.tx_hash == tx_hash)
        )
        if existing_deposit.scalars().first():
            logger.info(f"⏩ Deposit {tx_hash} already processed. Skipping.")
            return

        # 2. Verify Recipient
        if to_address.lower() != settings.system_wallet_address.lower():
            logger.warning(
                f"⚠️ Transfer recipient mismatch: "
                f"{to_address} != {settings.system_wallet_address}"
            )
            return

        # 3. User Identification
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

        # 4. Check deposit limit (max 5 deposits per user)
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

        try:
            # 5. Create new deposit (each transaction = separate deposit)
            now = datetime.now(UTC)
            daily_plex_required = amount * Decimal(str(PLEX_PER_DOLLAR_DAILY))

            # Determine level based on deposit count (1-5)
            level = active_deposits_count + 1

            deposit = await self.deposit_service.create_deposit(
                user_id=user.id,
                level=level,
                amount=amount,
                tx_hash=tx_hash
            )

            # Update deposit with additional info
            deposit.block_number = block_number
            deposit.wallet_address = from_address
            deposit.plex_cycle_start = now  # Individual 24h cycle starts now
            await self.session.commit()

            # 6. Confirm deposit
            await self.deposit_service.confirm_deposit(deposit.id, block_number)

            # 7. Notify user about new deposit and payment requirement
            await self.notification_service.notify_user(
                user.id,
                f"✅ **Новый депозит зарегистрирован!**\n\n"
                f"💰 Сумма: `{amount} USDT`\n"
                f"📊 Депозит #{deposit.id}\n"
                f"🔗 TX: `{tx_hash[:16]}...`\n\n"
                f"⚠️ **ВАЖНО: Для активации депозита**\n"
                f"Необходимо оплатить: **{int(daily_plex_required):,} PLEX**\n\n"
                f"💳 Кошелек для оплаты:\n"
                f"`{SYSTEM_WALLET}`\n\n"
                f"После оплаты PLEX депозит начнет работать.\n"
                f"Оплата требуется ежедневно (10 PLEX за каждый $1).\n"
                f"Ваши индивидуальные сутки начнутся с момента первой оплаты."
            )

            # 8. Notify admins
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
                f"Created new deposit #{deposit.id} for user {user.id}: "
                f"{amount} USDT, daily PLEX: {daily_plex_required}"
            )

        except Exception as e:
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
                Deposit.is_roi_completed == False,
            )
        )
        return result.scalar() or 0

