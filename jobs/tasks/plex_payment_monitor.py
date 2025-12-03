"""
PLEX Payment Monitor Task.

Monitors PLEX payment requirements:
- Checks pending first payments (deposits waiting for activation)
- Checks overdue payments
- Sends warnings (after 25h)
- Blocks deposits (after 49h)
- Sends payment reminders with QR codes

Runs every hour via scheduler.
"""

import asyncio
import io
from datetime import UTC, datetime

import dramatiq
from aiogram import Bot
from aiogram.types import BufferedInputFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.constants import TELEGRAM_MESSAGE_DELAY
from app.config.settings import settings
from app.models.plex_payment import PlexPaymentRequirement, PlexPaymentStatus
from app.repositories.deposit_repository import DepositRepository
from app.repositories.plex_payment_repository import PlexPaymentRepository
from app.services.notification_service import NotificationService
from bot.constants.rules import SYSTEM_WALLET
from bot.utils.qr_generator import generate_payment_qr


@dramatiq.actor(max_retries=2, time_limit=300_000)  # 5 min timeout
def monitor_plex_payments() -> None:
    """
    Monitor PLEX payment requirements.
    
    Steps:
    1. Get payments needing warning (25h+ without payment)
    2. Send warnings
    3. Get payments needing block (49h+ without payment)
    4. Block deposits and notify users
    """
    logger.info("Starting PLEX payment monitoring...")
    
    try:
        asyncio.run(_monitor_plex_payments_async())
        logger.info("PLEX payment monitoring complete")
    except Exception as e:
        logger.exception(f"PLEX payment monitoring failed: {e}")


async def _monitor_plex_payments_async() -> None:
    """Async implementation of PLEX payment monitoring."""
    # Create local engine (for isolated task)
    local_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )

    local_session_maker = async_sessionmaker(
        local_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Initialize bot for notifications
    bot = Bot(token=settings.telegram_bot_token)

    try:
        async with local_session_maker() as session:
            plex_repo = PlexPaymentRepository(session)
            deposit_repo = DepositRepository(session)
            notification_service = NotificationService(session)

            # Step 1: Send reminders for pending first payments (inactive deposits)
            pending_reminders = await _process_pending_activation_reminders(
                session, plex_repo, bot
            )

            # Step 2: Process warnings
            warnings_sent = await _process_warnings(
                session, plex_repo, bot
            )

            # Step 3: Process blocks
            deposits_blocked = await _process_blocks(
                session, plex_repo, deposit_repo, bot
            )

            # Commit changes
            await session.commit()

            logger.info(
                f"PLEX monitoring complete: "
                f"pending_reminders={pending_reminders}, "
                f"warnings_sent={warnings_sent}, "
                f"deposits_blocked={deposits_blocked}"
            )

    except Exception as e:
        logger.exception(f"PLEX payment monitoring error: {e}")
        raise
    finally:
        await bot.session.close()
        await local_engine.dispose()


async def _process_pending_activation_reminders(
    session: AsyncSession,
    plex_repo: PlexPaymentRepository,
    bot: Bot,
) -> int:
    """
    Send reminders for deposits waiting for first PLEX payment.

    These deposits are not active until first payment is received.
    """
    reminders_sent = 0

    # Get payments that are not yet active (is_work_active = False)
    pending_payments = await plex_repo.get_pending_activation_payments(limit=50)

    for payment in pending_payments:
        try:
            user = payment.user
            deposit = payment.deposit
            if not user or not deposit:
                continue

            # Generate QR code for payment
            qr_bytes = generate_payment_qr(SYSTEM_WALLET)

            # Build reminder message
            message = (
                "⏳ **ДЕПОЗИТ ОЖИДАЕТ АКТИВАЦИИ**\n\n"
                f"💰 **Депозит #{deposit.id}** ({deposit.amount} USDT)\n"
                f"📋 **Для активации оплатите:** {int(payment.daily_plex_required):,} PLEX\n\n"
                "⚠️ **Депозит не работает** до получения оплаты PLEX.\n"
                "После оплаты начнутся начисления.\n\n"
                f"💳 **Кошелек для оплаты:**\n"
                f"`{SYSTEM_WALLET}`\n\n"
                "Отсканируйте QR-код для быстрой оплаты 👇"
            )

            try:
                if qr_bytes:
                    # Send message with QR code
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=BufferedInputFile(qr_bytes, filename="payment_qr.png"),
                        caption=message,
                        parse_mode="Markdown",
                    )
                else:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown",
                    )
                reminders_sent += 1

                # Rate limiting: delay between messages
                await asyncio.sleep(TELEGRAM_MESSAGE_DELAY)
            except Exception as e:
                logger.warning(
                    f"Failed to send activation reminder to user {user.telegram_id}: {e}"
                )

        except Exception as e:
            logger.error(f"Failed to process pending activation for payment {payment.id}: {e}")

    return reminders_sent


async def _process_warnings(
    session: AsyncSession,
    plex_repo: PlexPaymentRepository,
    bot: Bot,
) -> int:
    """
    Process payment warnings.

    Sends warnings to users who haven't paid after 25h.
    Includes QR code for payment.
    """
    warnings_sent = 0

    # Get payments needing warning
    warning_due = await plex_repo.get_warning_due_payments(limit=50)

    for payment in warning_due:
        try:
            # Get user's telegram_id
            user = payment.user
            if not user:
                continue

            deposit = payment.deposit
            if not deposit:
                continue

            # Generate QR code for payment
            qr_bytes = generate_payment_qr(SYSTEM_WALLET)

            # Build warning message
            message = (
                "⚠️ **ПРЕДУПРЕЖДЕНИЕ: Оплата PLEX не получена!**\n\n"
                f"💰 **Депозит #{deposit.id}** ({deposit.amount} USDT)\n"
                f"📋 **Требуется:** {int(payment.daily_plex_required):,} PLEX в сутки\n\n"
                f"⏰ Оплата должна была поступить более 25 часов назад.\n\n"
                "❌ **Если оплата не поступит в течение 24 часов:**\n"
                "• Депозит будет заблокирован\n"
                "• Начисления остановлены\n"
                "• Средства будут возвращены\n\n"
                f"💳 **Кошелек для оплаты:**\n"
                f"`{SYSTEM_WALLET}`\n\n"
                "Отсканируйте QR-код для быстрой оплаты 👇"
            )

            try:
                if qr_bytes:
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=BufferedInputFile(qr_bytes, filename="payment_qr.png"),
                        caption=message,
                        parse_mode="Markdown",
                    )
                else:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown",
                    )

                # Rate limiting: delay between messages
                await asyncio.sleep(TELEGRAM_MESSAGE_DELAY)
            except Exception as e:
                logger.warning(
                    f"Failed to send PLEX warning to user {user.telegram_id}: {e}"
                )

            # Mark warning sent
            await plex_repo.mark_warning_sent(payment.id)
            warnings_sent += 1

            logger.warning(
                f"PLEX warning sent: user_id={user.id}, "
                f"deposit_id={deposit.id}"
            )

        except Exception as e:
            logger.error(f"Failed to process warning for payment {payment.id}: {e}")

    return warnings_sent


async def _process_blocks(
    session: AsyncSession,
    plex_repo: PlexPaymentRepository,
    deposit_repo: DepositRepository,
    bot: Bot,
) -> int:
    """
    Process deposit blocks.
    
    Blocks deposits for users who haven't paid after 49h.
    """
    deposits_blocked = 0
    
    # Get payments needing block
    block_due = await plex_repo.get_block_due_payments(limit=50)
    
    for payment in block_due:
        try:
            # Get user's telegram_id
            user = payment.user
            if not user:
                continue
            
            deposit = payment.deposit
            if not deposit:
                continue
            
            # Block deposit
            deposit.status = "blocked_plex"
            await session.flush()
            
            # Mark payment as blocked
            await plex_repo.mark_blocked(payment.id)
            
            # Build notification message
            message = (
                "🚫 **ДЕПОЗИТ ЗАБЛОКИРОВАН**\n\n"
                f"💰 **Депозит #{deposit.id}** ({deposit.amount} USDT)\n\n"
                "❌ Оплата PLEX не поступила в течение 49 часов.\n\n"
                "**Что происходит:**\n"
                "• Депозит заблокирован\n"
                "• Начисления остановлены\n"
                "• Средства будут возвращены администратором\n\n"
                "Для восстановления доступа обратитесь в поддержку."
            )
            
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode="Markdown",
                )

                # Rate limiting: delay between messages
                await asyncio.sleep(TELEGRAM_MESSAGE_DELAY)
            except Exception as e:
                logger.warning(
                    f"Failed to send block notification to user {user.telegram_id}: {e}"
                )

            deposits_blocked += 1
            
            logger.error(
                f"Deposit blocked for PLEX non-payment: "
                f"user_id={user.id}, deposit_id={deposit.id}"
            )
            
        except Exception as e:
            logger.error(f"Failed to process block for payment {payment.id}: {e}")
    
    return deposits_blocked


@dramatiq.actor(max_retries=1, time_limit=60_000)  # 1 min timeout
def check_single_user_plex(user_id: int) -> None:
    """
    Check PLEX balance for a single user.
    
    Can be called on-demand (e.g., after deposit creation).
    """
    logger.info(f"Checking PLEX for user {user_id}")
    
    try:
        asyncio.run(_check_single_user_async(user_id))
    except Exception as e:
        logger.exception(f"PLEX check failed for user {user_id}: {e}")


async def _check_single_user_async(user_id: int) -> None:
    """Check PLEX balance for single user."""
    local_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    
    local_session_maker = async_sessionmaker(
        local_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    try:
        async with local_session_maker() as session:
            from app.services.plex_payment_service import PlexPaymentService
            
            plex_service = PlexPaymentService(session)
            result = await plex_service.check_plex_balance_sufficient(user_id)
            
            if not result.get("sufficient"):
                logger.warning(
                    f"Insufficient PLEX for user {user_id}: {result}"
                )
    finally:
        await local_engine.dispose()

