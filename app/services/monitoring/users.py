"""
User Monitoring Service.

Provides user statistics, search, and full history for ARIA AI Assistant.
Optimized queries for better performance.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.admin_action import AdminAction
from app.models.deposit import Deposit
from app.models.transaction import Transaction
from app.models.user import User


# Try to import optional models
try:
    from app.models.user_inquiry import UserInquiry

    HAS_INQUIRIES = True
except ImportError:
    HAS_INQUIRIES = False


# ========== Helper Functions ==========


def validate_limit(value: Any, default: int = 20, max_limit: int = 100) -> int:
    """
    Validate a limit parameter.

    Args:
        value: Limit value to validate
        default: Default limit if value is invalid
        max_limit: Maximum allowed limit

    Returns:
        Validated limit value
    """
    if value is None:
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    if value > max_limit:
        return max_limit
    return value


class TimeHelper:
    """Helper for time calculations."""

    @staticmethod
    def now() -> datetime:
        """Get current UTC time."""
        return datetime.now(UTC)

    @staticmethod
    def hours_ago(hours: int) -> datetime:
        """Get datetime N hours ago."""
        return datetime.now(UTC) - timedelta(hours=hours)

    @staticmethod
    def days_ago(days: int) -> datetime:
        """Get datetime N days ago."""
        return datetime.now(UTC) - timedelta(days=days)

    @staticmethod
    def today_start() -> datetime:
        """Get start of today (00:00:00 UTC)."""
        return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


class FormatHelper:
    """Helper for formatting data."""

    @staticmethod
    def format_datetime(dt: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
        """Format datetime to string."""
        if not dt:
            return ""
        return dt.strftime(fmt)

    @staticmethod
    def format_date(dt: datetime | None) -> str:
        """Format datetime to date string."""
        return FormatHelper.format_datetime(dt, "%d.%m.%Y")

    @staticmethod
    def format_time(dt: datetime | None) -> str:
        """Format datetime to time string."""
        return FormatHelper.format_datetime(dt, "%H:%M")

    @staticmethod
    def truncate_string(text: str | None, max_length: int = 100) -> str:
        """Truncate string to max length."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."


class UserMonitor:
    """
    User monitoring service for ARIA AI Assistant.

    Provides user statistics, search functionality, and complete user history.
    Uses optimized queries to minimize database load.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize user monitor.

        Args:
            session: Database session
        """
        self.session = session

    async def get_stats(self) -> dict[str, Any]:
        """
        Get user statistics.

        Optimized: Combines 6 separate queries into 1 using SQL CASE statements.

        Returns:
            Dict with user statistics including:
            - total_users: Total number of users
            - active_24h: Active users in last 24 hours
            - active_7d: Active users in last 7 days
            - new_today: New users today
            - new_last_hour: New users in last hour
            - verified_users: Number of verified users
            - verification_rate: Percentage of verified users
        """
        try:
            # Calculate time boundaries
            since_24h = TimeHelper.hours_ago(24)
            since_7d = TimeHelper.days_ago(7)
            today_start = TimeHelper.today_start()
            last_hour = TimeHelper.hours_ago(1)

            # OPTIMIZATION: Single query instead of 6 separate queries
            result = await self.session.execute(
                select(
                    func.count(User.id).label("total"),
                    func.sum(case((User.updated_at >= since_24h, 1), else_=0)).label("active_24h"),
                    func.sum(case((User.updated_at >= since_7d, 1), else_=0)).label("active_7d"),
                    func.sum(case((User.created_at >= today_start, 1), else_=0)).label("new_today"),
                    func.sum(case((User.created_at >= last_hour, 1), else_=0)).label("new_last_hour"),
                    func.sum(case((User.is_verified == True, 1), else_=0)).label("verified"),  # noqa: E712
                )
            )

            row = result.fetchone()
            if not row:
                return {"error": "No data available"}

            total_users = row.total or 0
            active_24h = row.active_24h or 0
            active_7d = row.active_7d or 0
            new_today = row.new_today or 0
            new_last_hour = row.new_last_hour or 0
            verified_users = row.verified or 0

            verification_rate = round(verified_users / total_users * 100, 1) if total_users > 0 else 0

            logger.debug(
                f"UserMonitor: get_stats - total={total_users}, "
                f"active_24h={active_24h}, verified={verified_users}"
            )

            return {
                "total_users": total_users,
                "active_24h": active_24h,
                "active_7d": active_7d,
                "new_today": new_today,
                "new_last_hour": new_last_hour,
                "verified_users": verified_users,
                "verification_rate": verification_rate,
            }
        except Exception as e:
            logger.error(f"UserMonitor: Error getting user stats: {e}")
            return {"error": str(e)}

    async def get_full_history(self, identifier: str | int) -> dict[str, Any]:
        """
        Get full history for a user by username, telegram_id, or user_id.

        Optimized: Combines 3 separate user lookup queries into 1 using OR conditions.

        Args:
            identifier: Username (with or without @), telegram_id, or user_id

        Returns:
            Dict with user's complete history including:
            - found: Whether user was found
            - user: User basic info (id, telegram_id, username, balance, etc.)
            - deposits: List of user deposits
            - transactions: List of user transactions (last 50)
            - inquiries: List of user inquiries (if available)
            - admin_actions: Admin actions on this user (last 20)
        """
        try:
            # Normalize identifier
            username = None
            if isinstance(identifier, str):
                identifier = identifier.strip()
                if identifier.startswith("@"):
                    identifier = identifier[1:]
                # Check if it's a username (not purely numeric)
                if not identifier.isdigit():
                    username = identifier

            # OPTIMIZATION: Single query with OR conditions instead of 3 sequential queries
            user = None
            if username:
                # Try username first
                result = await self.session.execute(select(User).where(User.username == username).limit(1))
                user = result.scalar_one_or_none()

            if not user and str(identifier).isdigit():
                # Try telegram_id or user_id
                identifier_int = int(identifier)
                result = await self.session.execute(
                    select(User)
                    .where(or_(User.telegram_id == identifier_int, User.id == identifier_int))
                    .limit(1)
                )
                user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"UserMonitor: User not found: {identifier}")
                return {"found": False, "message": f"User not found: {identifier}"}

            # Basic user info
            user_info = {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username or "Нет username",
                "balance": float(user.balance),
                "total_earned": float(user.total_earned),
                "is_verified": user.is_verified,
                "is_banned": user.is_banned,
                "created_at": FormatHelper.format_datetime(user.created_at),
            }

            # Get deposits
            deposits_result = await self.session.execute(
                select(Deposit).where(Deposit.user_id == user.id).order_by(Deposit.created_at.desc())
            )
            deposits = [
                {
                    "amount": float(d.amount),
                    "status": d.status,
                    "created": FormatHelper.format_date(d.created_at),
                }
                for d in deposits_result.scalars().all()
            ]

            # Get transactions (limit to last 50)
            txns_result = await self.session.execute(
                select(Transaction)
                .where(Transaction.user_id == user.id)
                .order_by(Transaction.created_at.desc())
                .limit(50)
            )
            transactions = [
                {
                    "type": t.type,
                    "amount": float(t.amount),
                    "status": t.status,
                    "created": FormatHelper.format_datetime(t.created_at),
                }
                for t in txns_result.scalars().all()
            ]

            # Get inquiries (if available)
            inquiries = []
            if HAS_INQUIRIES:
                try:
                    inq_result = await self.session.execute(
                        select(UserInquiry)
                        .where(UserInquiry.user_id == user.id)
                        .order_by(UserInquiry.created_at.desc())
                    )
                    inquiries = [
                        {
                            "question": FormatHelper.truncate_string(i.initial_question, 100),
                            "status": i.status,
                            "created": FormatHelper.format_date(i.created_at),
                        }
                        for i in inq_result.scalars().all()
                    ]
                except Exception as inq_error:
                    logger.warning(f"UserMonitor: Error getting inquiries: {inq_error}")

            # Get admin actions on this user (limit to last 20)
            actions_result = await self.session.execute(
                select(AdminAction, Admin.username)
                .join(Admin, AdminAction.admin_id == Admin.id)
                .where(AdminAction.target_user_id == user.id)
                .order_by(AdminAction.created_at.desc())
                .limit(20)
            )
            admin_actions = [
                {
                    "type": row[0].action_type,
                    "admin": row[1] or "Unknown",
                    "created": FormatHelper.format_datetime(row[0].created_at),
                    "details": row[0].details if isinstance(row[0].details, dict) else {},
                }
                for row in actions_result.fetchall()
            ]

            logger.info(
                f"UserMonitor: get_full_history - user_id={user.id}, "
                f"deposits={len(deposits)}, txns={len(transactions)}"
            )

            return {
                "found": True,
                "user": user_info,
                "deposits": deposits,
                "deposits_count": len(deposits),
                "deposits_total": sum(d["amount"] for d in deposits),
                "transactions": transactions,
                "transactions_count": len(transactions),
                "inquiries": inquiries,
                "inquiries_count": len(inquiries),
                "admin_actions": admin_actions,
                "admin_actions_count": len(admin_actions),
            }
        except Exception as e:
            logger.error(f"UserMonitor: Error getting user history for {identifier}: {e}")
            return {"found": False, "error": str(e)}

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search users by username, telegram_id, or wallet.

        Args:
            query: Search query (username with/without @, telegram_id, etc.)
            limit: Maximum number of results to return

        Returns:
            List of matching users with basic info:
            - id: User database ID
            - telegram_id: Telegram user ID
            - username: Telegram username
            - balance: Current balance
            - is_verified: Verification status
            - is_banned: Ban status
        """
        try:
            # Validate limit
            limit = validate_limit(limit, default=10, max_limit=50)

            # Normalize query
            query = query.strip()
            if not query:
                logger.warning("UserMonitor: Empty search query")
                return []

            results = []

            # Search by username
            search_term = query.replace("@", "")
            if search_term:
                username_result = await self.session.execute(
                    select(User).where(User.username.ilike(f"%{search_term}%")).limit(limit)
                )
                for user in username_result.scalars().all():
                    results.append(
                        {
                            "id": user.id,
                            "telegram_id": user.telegram_id,
                            "username": user.username,
                            "balance": float(user.balance),
                            "is_verified": user.is_verified,
                            "is_banned": user.is_banned,
                        }
                    )

            # If query is numeric, also search by telegram_id
            if query.isdigit() and len(results) < limit:
                tg_result = await self.session.execute(select(User).where(User.telegram_id == int(query)))
                user = tg_result.scalar_one_or_none()
                if user and user.id not in [r["id"] for r in results]:
                    results.append(
                        {
                            "id": user.id,
                            "telegram_id": user.telegram_id,
                            "username": user.username,
                            "balance": float(user.balance),
                            "is_verified": user.is_verified,
                            "is_banned": user.is_banned,
                        }
                    )

            logger.debug(f"UserMonitor: search - query='{query}', results={len(results)}")
            return results[:limit]
        except Exception as e:
            logger.error(f"UserMonitor: Error searching users with query '{query}': {e}")
            return []
