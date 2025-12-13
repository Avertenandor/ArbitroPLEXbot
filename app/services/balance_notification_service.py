"""
Balance notification service.

Sends hourly notifications to active users about their arbitrage earnings.
Users receive notifications if they have:
- Active deposits (confirmed)
- Work status = "active" (PLEX payments are up to date)
- Balance > 0
- Not blocked the bot
"""

import random
from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.referral import Referral
from app.models.user import User
from app.services.base_service import BaseService


if TYPE_CHECKING:
    from aiogram import Bot


class BalanceNotificationService(BaseService):
    """
    Service for sending hourly balance notifications to active users.

    Sends information about:
    - Number of arbitrage operations (generated within 180-300 range)
    - Amount in work (total deposited)
    - User's earnings share
    - Partner earnings
    - Income from partners
    - Available for withdrawal
    """

    # Arbitrage operations corridor (per hour)
    MIN_OPERATIONS = 181  # Avoid round 180
    MAX_OPERATIONS = 299  # Avoid round 300
    OPERATIONS_MEAN_SHIFT = 0.7  # Shift towards 300 (0.5 = center, 1.0 = max)

    def __init__(self, session: AsyncSession) -> None:
        """Initialize balance notification service."""
        super().__init__(session)

    def _generate_operations_count(self) -> int:
        """
        Generate random number of operations in corridor 180-300.

        Uses weighted distribution shifted towards 300, avoiding round numbers.

        Returns:
            Number of operations (181-299, biased towards higher values)
        """
        # Use beta distribution to shift towards higher values
        # alpha=2, beta=5 gives left skew, we invert for right skew
        raw = random.betavariate(5, 2)  # Right-skewed distribution

        # Map to our range
        operations = int(self.MIN_OPERATIONS + raw * (self.MAX_OPERATIONS - self.MIN_OPERATIONS))

        # Ensure we're in range and avoid common round numbers
        operations = max(self.MIN_OPERATIONS, min(self.MAX_OPERATIONS, operations))

        # Avoid numbers ending in 0 or 5 (feel more "random")
        while operations % 10 == 0 or operations % 10 == 5:
            operations += random.choice([-1, 1, 2, -2])
            operations = max(self.MIN_OPERATIONS, min(self.MAX_OPERATIONS, operations))

        return operations

    async def get_eligible_users(self) -> list[User]:
        """
        Get users eligible for balance notifications.

        Criteria:
        - work_status = "active" (PLEX is paid, checked by plex_balance_monitor)
        - Has deposits OR bonus balance (participating in ROI)
        - bot_blocked = False
        - is_banned = False
        - is_active = True

        Returns:
            List of eligible users with deposits loaded
        """
        from app.config.business_constants import WorkStatus

        stmt = (
            select(User)
            .where(
                and_(
                    User.work_status == WorkStatus.ACTIVE,
                    or_(
                        User.total_deposited_usdt > Decimal("0"),  # Has confirmed deposits
                        User.bonus_balance > Decimal("0"),  # Or has bonus credits
                    ),
                    User.bot_blocked == False,  # noqa: E712
                    User.is_banned == False,  # noqa: E712
                    User.is_active == True,  # noqa: E712
                )
            )
            .options(selectinload(User.deposits))
        )

        result = await self.session.execute(stmt)
        users = list(result.scalars().all())

        logger.info(f"Found {len(users)} eligible users for balance notifications")
        return users

    async def get_user_statistics(self, user: User) -> dict:
        """
        Get statistics for a user's notification.

        Args:
            user: User to get statistics for

        Returns:
            Dict with:
            - operations_count: Random number of operations
            - amount_in_work: Total deposited amount
            - user_earnings: User's earnings share (last hour simulation)
            - partners_earnings: Total earnings of user's direct referrals
            - income_from_partners: User's income from partner earnings
            - available_for_withdrawal: Current balance
        """
        # Generate operations count
        operations_count = self._generate_operations_count()

        # Amount in work = total deposited + bonus balance (full working capital)
        total_deposited = user.total_deposited_usdt or Decimal("0")
        bonus_balance = user.bonus_balance or Decimal("0")
        amount_in_work = total_deposited + bonus_balance

        # Calculate simulated hourly earnings based on daily rate
        # Average daily ROI is ~1.117%, so hourly is ~0.0465%
        hourly_rate = Decimal("0.000465")  # ~1.117% / 24
        user_earnings = amount_in_work * hourly_rate

        # Round to reasonable precision
        user_earnings = user_earnings.quantize(Decimal("0.0001"))

        # Get partner statistics
        partners_stats = await self._get_partners_statistics(user.id)

        # PLEX statistics
        plex_balance = user.last_plex_balance or Decimal("0")
        required_daily_plex = user.required_daily_plex  # 10 PLEX per $1 of deposit
        plex_days_remaining = 0
        if required_daily_plex > 0:
            plex_days_remaining = int(plex_balance / required_daily_plex)

        return {
            "operations_count": operations_count,
            "amount_in_work": amount_in_work,
            "user_earnings": user_earnings,
            "partners_earnings": partners_stats["partners_earnings"],
            "income_from_partners": partners_stats["income_from_partners"],
            "available_for_withdrawal": user.balance,
            "plex_balance": plex_balance,
            "required_daily_plex": required_daily_plex,
            "plex_days_remaining": plex_days_remaining,
        }

    async def _get_partners_statistics(self, user_id: int) -> dict:
        """
        Get statistics about user's partners (referrals).

        Args:
            user_id: User ID to get partner stats for

        Returns:
            Dict with partners_earnings and income_from_partners
        """
        # Get total earned from direct referrals (level 1)
        stmt = select(
            func.coalesce(func.sum(Referral.total_earned), Decimal("0"))
        ).where(
            and_(
                Referral.referrer_id == user_id,
                Referral.level == 1,  # Only direct referrals
            )
        )
        result = await self.session.execute(stmt)
        income_from_partners = result.scalar() or Decimal("0")

        # Get IDs of direct referrals
        referral_ids_stmt = select(Referral.referral_id).where(
            and_(
                Referral.referrer_id == user_id,
                Referral.level == 1,
            )
        )
        referral_ids_result = await self.session.execute(referral_ids_stmt)
        referral_ids = list(referral_ids_result.scalars().all())

        # Calculate total earnings of partners
        partners_earnings = Decimal("0")
        if referral_ids:
            partners_stmt = select(
                func.coalesce(func.sum(User.total_earned), Decimal("0"))
            ).where(User.id.in_(referral_ids))
            partners_result = await self.session.execute(partners_stmt)
            partners_earnings = partners_result.scalar() or Decimal("0")

        return {
            "partners_earnings": partners_earnings,
            "income_from_partners": income_from_partners,
        }

    def format_notification_message(self, stats: dict) -> str:
        """
        Format the notification message with statistics.

        Args:
            stats: Statistics dictionary from get_user_statistics

        Returns:
            Formatted message string with Markdown
        """
        operations = stats["operations_count"]
        amount_in_work = stats["amount_in_work"]
        user_earnings = stats["user_earnings"]
        partners_earnings = stats["partners_earnings"]
        income_from_partners = stats["income_from_partners"]
        available = stats["available_for_withdrawal"]
        plex_balance = stats.get("plex_balance", 0)
        required_daily_plex = stats.get("required_daily_plex", 0)
        plex_days_remaining = stats.get("plex_days_remaining", 0)

        message = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 *АРБИТРОБОТ V.7.2*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            f"📊 Арбитражная система Арбитробот V.7.2\n"
            f"провела за последний час *{operations}* операций\n\n"

            "┌───────────────────────────┐\n"
            "│      💼 *ВАША РАБОТА*      │\n"
            "└───────────────────────────┘\n\n"

            f"💰 У вас в работе участвует сумма:\n"
            f"   *{amount_in_work:.2f} USDT*\n\n"

            f"📈 Ваша доля успеха составила:\n"
            f"   *{user_earnings:.4f} USDT*\n\n"

            "┌───────────────────────────┐\n"
            "│   👥 *ПАРТНЁРСКАЯ*        │\n"
            "│      *ПРОГРАММА*          │\n"
            "└───────────────────────────┘\n\n"

            f"💸 Ваши партнёры заработали:\n"
            f"   *{partners_earnings:.4f} USDT*\n\n"

            f"🎁 Ваш доход от дохода ваших партнёров\n"
            f"   составил: *{income_from_partners:.4f} USDT*\n\n"

            "┌───────────────────────────┐\n"
            "│      💎 *PLEX СТАТУС*      │\n"
            "└───────────────────────────┘\n\n"

            f"⚡ Баланс PLEX: *{int(plex_balance):,}* токенов\n"
            f"📋 Расход в сутки: *{int(required_daily_plex):,}* PLEX\n"
            f"⏱ Хватит на: *~{plex_days_remaining}* дней\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 У вас доступно к выводу:\n"
            f"   *{available:.4f} USDT*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "_Арбитробот благодарит вас за доверие_\n"
            "_и продолжает развиваться!_ 🚀"
        )

        return message

    async def send_notification_to_user(
        self,
        bot: "Bot",
        user: User,
    ) -> bool:
        """
        Send balance notification to a single user.

        Args:
            bot: Telegram bot instance
            user: User to send notification to

        Returns:
            True if sent successfully
        """
        try:
            # Get statistics
            stats = await self.get_user_statistics(user)

            # Format message
            message = self.format_notification_message(stats)

            # Send notification
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown",
            )

            logger.debug(
                f"Balance notification sent to user {user.telegram_id}",
                extra={
                    "user_id": user.id,
                    "telegram_id": user.telegram_id,
                    "operations": stats["operations_count"],
                },
            )
            return True

        except Exception as e:
            error_msg = str(e).lower()

            # Check if bot was blocked by user
            if "blocked" in error_msg or "403" in error_msg:
                logger.warning(
                    f"Bot blocked by user {user.telegram_id}, skipping notification"
                )
                # Mark user as bot_blocked
                try:
                    from datetime import UTC, datetime
                    user.bot_blocked = True
                    user.bot_blocked_at = datetime.now(UTC)
                    await self.session.flush()
                except Exception as update_error:
                    logger.error(f"Failed to mark user as bot_blocked: {update_error}")
            else:
                logger.error(
                    f"Failed to send balance notification to user {user.telegram_id}: {e}"
                )

            return False

    async def send_notifications_to_all_eligible(
        self,
        bot: "Bot",
    ) -> dict:
        """
        Send balance notifications to all eligible users.

        Implements rate limiting to respect Telegram API limits:
        - Max 30 messages per second
        - We use 25/sec to be safe with batches of 25 + 1.1 sec delay

        Args:
            bot: Telegram bot instance

        Returns:
            Dict with statistics:
            - total: Total eligible users
            - sent: Successfully sent
            - failed: Failed to send
            - blocked: Users who blocked the bot
        """
        import asyncio

        # Telegram rate limit safety: 25 messages per second
        BATCH_SIZE = 25
        BATCH_DELAY = 1.1  # seconds between batches

        stats = {
            "total": 0,
            "sent": 0,
            "failed": 0,
            "blocked": 0,
        }

        try:
            users = await self.get_eligible_users()
            stats["total"] = len(users)

            logger.info(f"Starting balance notifications for {len(users)} users with rate limiting")

            # Process in batches to respect rate limits
            for i, user in enumerate(users):
                try:
                    success = await self.send_notification_to_user(bot, user)
                    if success:
                        stats["sent"] += 1
                    else:
                        # Check if it was a block
                        if user.bot_blocked:
                            stats["blocked"] += 1
                        else:
                            stats["failed"] += 1

                    # Rate limiting: pause after each batch
                    if (i + 1) % BATCH_SIZE == 0:
                        logger.debug(f"Rate limit pause after {i + 1} messages, sleeping {BATCH_DELAY}s")
                        await asyncio.sleep(BATCH_DELAY)

                except Exception as e:
                    logger.error(f"Error processing user {user.id}: {e}")
                    stats["failed"] += 1

            # Commit any changes (bot_blocked flags)
            await self.session.commit()

            logger.info(
                f"Balance notifications complete: "
                f"total={stats['total']}, sent={stats['sent']}, "
                f"failed={stats['failed']}, blocked={stats['blocked']}"
            )

        except Exception as e:
            logger.error(f"Error in send_notifications_to_all_eligible: {e}")
            raise

        return stats
