"""User statistics module for MonitoringService."""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.deposit import Deposit
from app.models.transaction import Transaction
from app.models.admin_action import AdminAction
from app.models.admin import Admin


# Try to import optional models
try:
    from app.models.user_inquiry import UserInquiry

    HAS_INQUIRIES = True
except ImportError:
    HAS_INQUIRIES = False


class UserStatsService:
    """Service for collecting user statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user stats service."""
        self.session = session

    async def get_user_stats(self) -> dict[str, Any]:
        """
        Get user statistics.

        Returns:
            Dict with user statistics
        """
        try:
            # Total users
            total_result = await self.session.execute(
                select(func.count(User.id))
            )
            total_users = total_result.scalar() or 0

            # Active users (last 24h)
            since_24h = datetime.now(UTC) - timedelta(hours=24)
            active_result = await self.session.execute(
                select(func.count(User.id))
                .where(User.updated_at >= since_24h)
            )
            active_24h = active_result.scalar() or 0

            # Active users (last 7d)
            since_7d = datetime.now(UTC) - timedelta(days=7)
            active_7d_result = await self.session.execute(
                select(func.count(User.id))
                .where(User.updated_at >= since_7d)
            )
            active_7d = active_7d_result.scalar() or 0

            # New users today
            today_start = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            new_today_result = await self.session.execute(
                select(func.count(User.id))
                .where(User.created_at >= today_start)
            )
            new_today = new_today_result.scalar() or 0

            # New users last hour
            last_hour = datetime.now(UTC) - timedelta(hours=1)
            new_hour_result = await self.session.execute(
                select(func.count(User.id))
                .where(User.created_at >= last_hour)
            )
            new_last_hour = new_hour_result.scalar() or 0

            # Verified users
            verified_result = await self.session.execute(
                select(func.count(User.id))
                .where(User.is_verified == True)  # noqa: E712
            )
            verified_users = verified_result.scalar() or 0

            verification_rate = (
                round(verified_users / total_users * 100, 1)
                if total_users > 0
                else 0
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
            logger.error(f"Error getting user stats: {e}")
            return {"error": str(e)}

    async def get_user_full_history(
        self, identifier: str | int
    ) -> dict[str, Any]:
        """
        Get full history for a user by username, telegram_id, or user_id.

        Args:
            identifier: Username (with @), telegram_id, or user_id

        Returns:
            Dict with user's complete history
        """
        try:
            # Find user
            user = None
            if isinstance(identifier, str):
                if identifier.startswith("@"):
                    identifier = identifier[1:]
                # Try as username
                result = await self.session.execute(
                    select(User).where(User.username == identifier)
                )
                user = result.scalar_one_or_none()
            if not user and str(identifier).isdigit():
                # Try as telegram_id
                result = await self.session.execute(
                    select(User).where(User.telegram_id == int(identifier))
                )
                user = result.scalar_one_or_none()
                if not user:
                    # Try as user_id
                    result = await self.session.execute(
                        select(User).where(User.id == int(identifier))
                    )
                    user = result.scalar_one_or_none()

            if not user:
                return {
                    "found": False,
                    "message": f"User not found: {identifier}",
                }

            # Basic info
            user_info = {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username or "Нет username",
                "balance": float(user.balance),
                "total_earned": float(user.total_earned),
                "is_verified": user.is_verified,
                "is_banned": user.is_banned,
                "created_at": (
                    user.created_at.strftime("%d.%m.%Y %H:%M")
                    if user.created_at
                    else ""
                ),
            }

            # Deposits
            deposits_result = await self.session.execute(
                select(Deposit)
                .where(Deposit.user_id == user.id)
                .order_by(Deposit.created_at.desc())
            )
            deposits = [
                {
                    "amount": float(d.amount),
                    "status": d.status,
                    "created": (
                        d.created_at.strftime("%d.%m.%Y")
                        if d.created_at
                        else ""
                    ),
                }
                for d in deposits_result.scalars().all()
            ]

            # Transactions
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
                    "created": (
                        t.created_at.strftime("%d.%m.%Y %H:%M")
                        if t.created_at
                        else ""
                    ),
                }
                for t in txns_result.scalars().all()
            ]

            # Inquiries (if available)
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
                            "question": (
                                i.initial_question[:100]
                                if i.initial_question
                                else ""
                            ),
                            "status": i.status,
                            "created": (
                                i.created_at.strftime("%d.%m.%Y")
                                if i.created_at
                                else ""
                            ),
                        }
                        for i in inq_result.scalars().all()
                    ]
                except Exception as e:
                    logger.error(
                        f"Error fetching inquiries for user "
                        f"{user.id}: {e}"
                    )

            # Admin actions on this user
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
                    "created": (
                        row[0].created_at.strftime("%d.%m.%Y %H:%M")
                        if row[0].created_at
                        else ""
                    ),
                    "details": (
                        row[0].details
                        if isinstance(row[0].details, dict)
                        else {}
                    ),
                }
                for row in actions_result.fetchall()
            ]

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
            logger.error(f"Error getting user history: {e}")
            return {"found": False, "error": str(e)}

    async def search_users(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search users by username, telegram_id, or wallet.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching users
        """
        try:
            results = []

            # Search by username
            if query:
                search_term = query.replace("@", "")
                username_result = await self.session.execute(
                    select(User)
                    .where(User.username.ilike(f"%{search_term}%"))
                    .limit(limit)
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
                tg_result = await self.session.execute(
                    select(User).where(User.telegram_id == int(query))
                )
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

            return results[:limit]
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
