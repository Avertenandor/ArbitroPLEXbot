"""
PLEX Balance Monitor Task.

Monitors minimum PLEX balance requirement (5000 PLEX):
- Checks PLEX balance for all active users every hour
- If balance < 5000: suspends work, sends warning notification
- If balance >= 5000: sends confirmation notification

Runs every hour via scheduler.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import dramatiq
from aiogram import Bot
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.constants import TELEGRAM_MESSAGE_DELAY
from app.config.settings import settings
from app.models.user import User
from app.services.blockchain_service import get_blockchain_service
from bot.constants.rules import MINIMUM_PLEX_BALANCE, WorkStatus, SYSTEM_WALLET
from bot.utils.qr_generator import generate_payment_qr


@dramatiq.actor(max_retries=2, time_limit=600_000)  # 10 min timeout
def monitor_plex_balances() -> None:
    """
    Monitor PLEX balances for all active users.

    Checks minimum 5000 PLEX requirement.
    Sends hourly notifications about balance status.
    """
    logger.info("Starting PLEX balance monitoring...")

    try:
        asyncio.run(_monitor_plex_balances_async())
        logger.info("PLEX balance monitoring complete")
    except Exception as e:
        logger.exception(f"PLEX balance monitoring failed: {e}")


async def _monitor_plex_balances_async() -> None:
    """Async implementation of PLEX balance monitoring."""
    # Create local engine
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

    # FIXED: Use context manager for Bot to prevent session leak
    stats = {
        "total_checked": 0,
        "sufficient": 0,
        "insufficient": 0,
        "suspended": 0,
        "restored": 0,
        "errors": 0,
    }

    try:
        async with Bot(token=settings.telegram_bot_token) as bot:
            async with local_session_maker() as session:
                # Get all active depositors
                result = await session.execute(
                    select(User).where(
                        User.is_active == True,
                        User.is_banned == False,
                        User.is_active_depositor == True,
                        User.bot_blocked == False,
                    )
                )
                users = list(result.scalars().all())

                logger.info(f"Checking PLEX balance for {len(users)} active depositors")

                blockchain = get_blockchain_service()

                for user in users:
                    try:
                        await _check_user_plex_balance(
                            session, bot, blockchain, user, stats
                        )

                        # Rate limiting: delay between users
                        await asyncio.sleep(TELEGRAM_MESSAGE_DELAY)
                    except Exception as e:
                        logger.error(
                            f"Error checking PLEX balance for user {user.id}: {e}"
                        )
                        stats["errors"] += 1

                await session.commit()

                logger.info(
                    f"PLEX balance check complete: "
                    f"checked={stats['total_checked']}, "
                    f"sufficient={stats['sufficient']}, "
                    f"insufficient={stats['insufficient']}, "
                    f"suspended={stats['suspended']}, "
                    f"restored={stats['restored']}, "
                    f"errors={stats['errors']}"
                )

    except Exception as e:
        logger.exception(f"PLEX balance monitoring error: {e}")
        raise
    finally:
        await local_engine.dispose()


async def _check_user_plex_balance(
    session: AsyncSession,
    bot: Bot,
    blockchain,
    user: User,
    stats: dict,
) -> None:
    """
    Check PLEX balance for a single user.

    Args:
        session: Database session
        bot: Telegram bot instance
        blockchain: Blockchain service
        user: User to check
        stats: Statistics dict to update
    """
    stats["total_checked"] += 1
    now = datetime.now(UTC)

    # Get PLEX balance from blockchain
    plex_balance = await blockchain.get_plex_balance(user.wallet_address)

    if plex_balance is None:
        logger.warning(f"Failed to get PLEX balance for user {user.id}")
        return

    # Update last check info
    user.last_plex_check_at = now
    user.last_plex_balance = plex_balance

    balance_int = int(plex_balance)
    is_sufficient = balance_int >= MINIMUM_PLEX_BALANCE
    was_suspended = user.work_status == WorkStatus.SUSPENDED_NO_PLEX

    if is_sufficient:
        stats["sufficient"] += 1

        # Restore work if was suspended
        if was_suspended:
            user.work_status = WorkStatus.ACTIVE
            user.plex_insufficient_since = None
            stats["restored"] += 1

            # Send restoration notification
            message = (
                "✅ **РАБОТА ВОССТАНОВЛЕНА**\n\n"
                f"Ваш баланс PLEX: **{balance_int:,}** токенов\n"
                f"Минимум: **{MINIMUM_PLEX_BALANCE:,}** токенов\n\n"
                "🟢 Все системы работают в штатном режиме.\n"
                "Ваши депозиты продолжают приносить доход."
            )
            await _send_notification(bot, user.telegram_id, message)
            logger.info(f"Restored work for user {user.id}, balance: {balance_int}")
        else:
            # Send hourly confirmation
            message = (
                "✅ **Баланс PLEX в норме**\n\n"
                f"Ваш баланс: **{balance_int:,}** PLEX\n"
                f"Минимум: **{MINIMUM_PLEX_BALANCE:,}** PLEX\n\n"
                "🟢 Система работает нормально."
            )
            await _send_notification(bot, user.telegram_id, message)

    else:
        stats["insufficient"] += 1

        # Suspend work if not already suspended
        if not was_suspended:
            user.work_status = WorkStatus.SUSPENDED_NO_PLEX
            user.plex_insufficient_since = now
            stats["suspended"] += 1
            logger.warning(
                f"Suspended work for user {user.id}, "
                f"PLEX balance: {balance_int} < {MINIMUM_PLEX_BALANCE}"
            )

        shortage = MINIMUM_PLEX_BALANCE - balance_int

        # Generate QR code for PLEX purchase/top-up
        # QR will contain wallet address for PLEX transfer
        qr_data = f"ethereum:{settings.auth_system_wallet_address}"

        # Send warning notification
        message = (
            "🚫 **РАБОТА ПРИОСТАНОВЛЕНА**\n\n"
            f"❌ Ваш баланс PLEX: **{balance_int:,}** токенов\n"
            f"📋 Требуется минимум: **{MINIMUM_PLEX_BALANCE:,}** токенов\n"
            f"📉 Недостаток: **{shortage:,}** токенов\n\n"
            "⚠️ **Причина:**\n"
            "У вас на кошельке недостаточно монет PLEX.\n\n"
            "**Последствия:**\n"
            "• Начисления по депозитам остановлены\n"
            "• Вывод средств недоступен\n"
            "• Новые депозиты невозможны\n\n"
            "**Для восстановления:**\n"
            f"Пополните баланс PLEX до {MINIMUM_PLEX_BALANCE:,} токенов.\n\n"
            "Проверка баланса происходит каждый час.\n"
            "Работа будет восстановлена автоматически."
        )
        await _send_notification(bot, user.telegram_id, message)

    await session.flush()


async def _send_notification(bot: Bot, telegram_id: int, message: str) -> bool:
    """
    Send notification to user.

    Args:
        bot: Telegram bot
        telegram_id: User's Telegram ID
        message: Message text

    Returns:
        True if sent successfully
    """
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode="Markdown",
        )
        # Note: delay is handled in the calling loop
        return True
    except Exception as e:
        logger.warning(f"Failed to send notification to {telegram_id}: {e}")
        return False


@dramatiq.actor(max_retries=1, time_limit=60_000)
def check_single_user_plex_balance(user_id: int) -> None:
    """
    Check PLEX balance for a single user (on-demand).

    Can be called after deposit creation or user action.
    """
    logger.info(f"Checking PLEX balance for user {user_id}")

    try:
        asyncio.run(_check_single_user_balance_async(user_id))
    except Exception as e:
        logger.exception(f"PLEX balance check failed for user {user_id}: {e}")


async def _check_single_user_balance_async(user_id: int) -> dict:
    """Check PLEX balance for single user and return result."""
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

    # FIXED: Use context manager for Bot to prevent session leak
    result = {"user_id": user_id, "success": False}

    try:
        async with Bot(token=settings.telegram_bot_token) as bot:
            async with local_session_maker() as session:
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalars().first()

                if not user:
                    result["error"] = "User not found"
                    return result

                blockchain = get_blockchain_service()
                stats = {}

                await _check_user_plex_balance(session, bot, blockchain, user, stats)
                await session.commit()

                result["success"] = True
                result["plex_balance"] = float(user.last_plex_balance or 0)
                result["work_status"] = user.work_status

    except Exception as e:
        result["error"] = str(e)
        await local_engine.dispose()

    return result
