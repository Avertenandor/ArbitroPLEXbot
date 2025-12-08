"""
Monitoring Service for ARIA AI Assistant.

Provides real-time access to platform metrics, admin activity,
user statistics, financial data, and system health.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.admin_action import AdminAction
from app.models.admin_session import AdminSession
from app.models.deposit import Deposit
from app.models.transaction import Transaction, TransactionType
from app.models.user import User


class MonitoringService:
    """
    Service for collecting platform metrics and statistics.
    
    Provides data for ARIA AI assistant to give real-time insights.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize monitoring service."""
        self.session = session

    async def get_admin_stats(self, hours: int = 24) -> dict[str, Any]:
        """
        Get admin activity statistics.
        
        Args:
            hours: Lookback period in hours
            
        Returns:
            Dict with admin statistics
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)
            
            # Total admins
            total_result = await self.session.execute(
                select(func.count(Admin.id))
            )
            total_admins = total_result.scalar() or 0
            
            # Active admins (have session in last N hours)
            active_result = await self.session.execute(
                select(func.count(func.distinct(AdminSession.admin_id)))
                .where(AdminSession.last_activity_at >= since)
                .where(AdminSession.is_active == True)  # noqa: E712
            )
            active_admins = active_result.scalar() or 0
            
            # Admin actions count
            actions_result = await self.session.execute(
                select(func.count(AdminAction.id))
                .where(AdminAction.created_at >= since)
            )
            total_actions = actions_result.scalar() or 0
            
            # Top actions by type
            top_actions_result = await self.session.execute(
                select(
                    AdminAction.action_type,
                    func.count(AdminAction.id).label("count")
                )
                .where(AdminAction.created_at >= since)
                .group_by(AdminAction.action_type)
                .order_by(text("count DESC"))
                .limit(5)
            )
            top_actions = [
                {"type": row[0], "count": row[1]}
                for row in top_actions_result.fetchall()
            ]
            
            # Get admin list with their roles
            admins_result = await self.session.execute(
                select(Admin.username, Admin.role, Admin.is_blocked)
                .order_by(Admin.role)
            )
            admins_list = [
                {
                    "username": row[0] or "Unknown",
                    "role": row[1],
                    "blocked": row[2]
                }
                for row in admins_result.fetchall()
            ]
            
            return {
                "total_admins": total_admins,
                "active_admins_last_hours": active_admins,
                "hours_period": hours,
                "total_actions": total_actions,
                "top_action_types": top_actions,
                "admins_list": admins_list,
            }
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            return {"error": str(e)}

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
                .where(User.last_activity_at >= since_24h)
            )
            active_24h = active_result.scalar() or 0
            
            # Active users (last 7d)
            since_7d = datetime.now(UTC) - timedelta(days=7)
            active_7d_result = await self.session.execute(
                select(func.count(User.id))
                .where(User.last_activity_at >= since_7d)
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
            
            # Verified users
            verified_result = await self.session.execute(
                select(func.count(User.id))
                .where(User.is_verified == True)  # noqa: E712
            )
            verified_users = verified_result.scalar() or 0
            
            return {
                "total_users": total_users,
                "active_24h": active_24h,
                "active_7d": active_7d,
                "new_today": new_today,
                "verified_users": verified_users,
                "verification_rate": (
                    round(verified_users / total_users * 100, 1)
                    if total_users > 0 else 0
                ),
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"error": str(e)}

    async def get_financial_stats(self, hours: int = 24) -> dict[str, Any]:
        """
        Get financial statistics.
        
        Args:
            hours: Lookback period
            
        Returns:
            Dict with financial stats
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)
            
            # Total deposits (all time)
            total_deposits_result = await self.session.execute(
                select(func.sum(Deposit.amount))
                .where(Deposit.status == "active")
            )
            total_deposits = total_deposits_result.scalar() or Decimal("0")
            
            # Deposits count
            deposits_count_result = await self.session.execute(
                select(func.count(Deposit.id))
                .where(Deposit.status == "active")
            )
            deposits_count = deposits_count_result.scalar() or 0
            
            # Recent deposits (period)
            recent_deposits_result = await self.session.execute(
                select(func.sum(Deposit.amount))
                .where(Deposit.created_at >= since)
            )
            recent_deposits = recent_deposits_result.scalar() or Decimal("0")
            
            # Recent deposits count
            recent_count_result = await self.session.execute(
                select(func.count(Deposit.id))
                .where(Deposit.created_at >= since)
            )
            recent_deposits_count = recent_count_result.scalar() or 0
            
            # Withdrawals (period)
            withdrawals_result = await self.session.execute(
                select(func.sum(Transaction.amount))
                .where(Transaction.transaction_type == TransactionType.WITHDRAWAL)
                .where(Transaction.created_at >= since)
            )
            withdrawals = withdrawals_result.scalar() or Decimal("0")
            
            withdrawals_count_result = await self.session.execute(
                select(func.count(Transaction.id))
                .where(Transaction.transaction_type == TransactionType.WITHDRAWAL)
                .where(Transaction.created_at >= since)
            )
            withdrawals_count = withdrawals_count_result.scalar() or 0
            
            # Pending withdrawals
            pending_result = await self.session.execute(
                select(func.count(Transaction.id), func.sum(Transaction.amount))
                .where(Transaction.transaction_type == TransactionType.WITHDRAWAL)
                .where(Transaction.status == "pending")
            )
            pending_row = pending_result.fetchone()
            pending_count = pending_row[0] or 0
            pending_amount = pending_row[1] or Decimal("0")
            
            return {
                "hours_period": hours,
                "total_active_deposits": float(total_deposits),
                "total_deposits_count": deposits_count,
                "recent_deposits": float(recent_deposits),
                "recent_deposits_count": recent_deposits_count,
                "recent_withdrawals": float(withdrawals),
                "recent_withdrawals_count": withdrawals_count,
                "pending_withdrawals_count": pending_count,
                "pending_withdrawals_amount": float(pending_amount),
            }
        except Exception as e:
            logger.error(f"Error getting financial stats: {e}")
            return {"error": str(e)}

    async def get_recent_admin_actions(
        self, limit: int = 10, hours: int = 24
    ) -> list[dict[str, Any]]:
        """
        Get recent admin actions log.
        
        Args:
            limit: Max number of actions
            hours: Lookback period
            
        Returns:
            List of recent actions
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)
            
            result = await self.session.execute(
                select(
                    AdminAction.action_type,
                    AdminAction.description,
                    AdminAction.created_at,
                    Admin.username,
                )
                .join(Admin, AdminAction.admin_id == Admin.id)
                .where(AdminAction.created_at >= since)
                .order_by(AdminAction.created_at.desc())
                .limit(limit)
            )
            
            actions = []
            for row in result.fetchall():
                actions.append({
                    "type": row[0],
                    "description": row[1][:100] if row[1] else "",
                    "time": row[2].strftime("%H:%M") if row[2] else "",
                    "admin": row[3] or "Unknown",
                })
            
            return actions
        except Exception as e:
            logger.error(f"Error getting recent actions: {e}")
            return []

    async def get_system_health(self) -> dict[str, Any]:
        """
        Get system health indicators.
        
        Returns:
            Dict with health metrics
        """
        try:
            # Database check
            db_ok = True
            try:
                await self.session.execute(text("SELECT 1"))
            except Exception:
                db_ok = False
            
            # Get some basic metrics
            now = datetime.now(UTC)
            
            return {
                "database": "OK" if db_ok else "ERROR",
                "timestamp": now.isoformat(),
                "status": "healthy" if db_ok else "degraded",
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"status": "error", "error": str(e)}

    async def get_full_dashboard(self) -> dict[str, Any]:
        """
        Get complete dashboard data for ARIA.
        
        Returns:
            Complete monitoring data
        """
        admin_stats = await self.get_admin_stats(hours=24)
        user_stats = await self.get_user_stats()
        financial_stats = await self.get_financial_stats(hours=24)
        recent_actions = await self.get_recent_admin_actions(limit=10)
        system_health = await self.get_system_health()
        
        return {
            "admin": admin_stats,
            "users": user_stats,
            "financial": financial_stats,
            "recent_actions": recent_actions,
            "system": system_health,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def format_dashboard_for_ai(self, data: dict[str, Any]) -> str:
        """
        Format dashboard data as text for AI context.
        
        Args:
            data: Dashboard data dict
            
        Returns:
            Formatted text for AI prompt
        """
        lines = ["=== РЕАЛЬНЫЕ ДАННЫЕ ПЛАТФОРМЫ ==="]
        lines.append(f"Время: {data.get('generated_at', 'N/A')}")
        lines.append("")
        
        # Admin stats
        admin = data.get("admin", {})
        lines.append("📊 АДМИНИСТРАТОРЫ:")
        lines.append(f"  Всего админов: {admin.get('total_admins', 0)}")
        lines.append(
            f"  Активных за {admin.get('hours_period', 24)}ч: "
            f"{admin.get('active_admins_last_hours', 0)}"
        )
        lines.append(f"  Действий: {admin.get('total_actions', 0)}")
        
        # Admin list
        admins_list = admin.get("admins_list", [])
        if admins_list:
            lines.append("  Список админов:")
            for a in admins_list:
                status = "🚫" if a.get("blocked") else "✅"
                lines.append(f"    {status} @{a.get('username')} ({a.get('role')})")
        
        # Top actions
        top_actions = admin.get("top_action_types", [])
        if top_actions:
            lines.append("  Топ действий:")
            for action in top_actions[:3]:
                lines.append(f"    - {action['type']}: {action['count']}")
        
        lines.append("")
        
        # User stats
        users = data.get("users", {})
        lines.append("👥 ПОЛЬЗОВАТЕЛИ:")
        lines.append(f"  Всего: {users.get('total_users', 0)}")
        lines.append(f"  Активных за 24ч: {users.get('active_24h', 0)}")
        lines.append(f"  Активных за 7д: {users.get('active_7d', 0)}")
        lines.append(f"  Новых сегодня: {users.get('new_today', 0)}")
        lines.append(
            f"  Верифицированных: {users.get('verified_users', 0)} "
            f"({users.get('verification_rate', 0)}%)"
        )
        lines.append("")
        
        # Financial stats
        fin = data.get("financial", {})
        lines.append("💰 ФИНАНСЫ:")
        lines.append(
            f"  Активных депозитов: ${fin.get('total_active_deposits', 0):,.2f} "
            f"({fin.get('total_deposits_count', 0)} шт)"
        )
        lines.append(
            f"  Новых за {fin.get('hours_period', 24)}ч: "
            f"${fin.get('recent_deposits', 0):,.2f} "
            f"({fin.get('recent_deposits_count', 0)} шт)"
        )
        lines.append(
            f"  Выводов за {fin.get('hours_period', 24)}ч: "
            f"${fin.get('recent_withdrawals', 0):,.2f} "
            f"({fin.get('recent_withdrawals_count', 0)} шт)"
        )
        lines.append(
            f"  Ожидают вывод: {fin.get('pending_withdrawals_count', 0)} шт "
            f"(${fin.get('pending_withdrawals_amount', 0):,.2f})"
        )
        lines.append("")
        
        # Recent actions
        actions = data.get("recent_actions", [])
        if actions:
            lines.append("📋 ПОСЛЕДНИЕ ДЕЙСТВИЯ АДМИНОВ:")
            for action in actions[:5]:
                lines.append(
                    f"  [{action.get('time')}] @{action.get('admin')}: "
                    f"{action.get('type')}"
                )
        
        lines.append("")
        
        # System health
        system = data.get("system", {})
        lines.append("🖥️ СИСТЕМА:")
        lines.append(f"  База данных: {system.get('database', 'N/A')}")
        lines.append(f"  Статус: {system.get('status', 'N/A')}")
        
        return "\n".join(lines)
