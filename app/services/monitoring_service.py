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
from app.models.transaction import Transaction
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
            logger.debug(f"MonitoringService: Getting admin stats, since={since}")

            # Total admins
            total_result = await self.session.execute(
                select(func.count(Admin.id))
            )
            total_admins = total_result.scalar() or 0
            logger.debug(f"MonitoringService: total_admins={total_admins}")
            
            # Active admins (have session in last N hours)
            active_result = await self.session.execute(
                select(func.count(func.distinct(AdminSession.admin_id)))
                .where(AdminSession.last_activity >= since)
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
                .where(Transaction.type == "withdrawal")
                .where(Transaction.created_at >= since)
            )
            withdrawals = withdrawals_result.scalar() or Decimal("0")

            withdrawals_count_result = await self.session.execute(
                select(func.count(Transaction.id))
                .where(Transaction.type == "withdrawal")
                .where(Transaction.created_at >= since)
            )
            withdrawals_count = withdrawals_count_result.scalar() or 0

            # Pending withdrawals
            pending_result = await self.session.execute(
                select(func.count(Transaction.id), func.sum(Transaction.amount))
                .where(Transaction.type == "withdrawal")
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
                    AdminAction.details,
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
                # details is JSON, extract description if available
                details = row[1] or {}
                desc = ""
                if isinstance(details, dict):
                    desc = details.get("description", details.get("action", ""))
                elif details:
                    desc = str(details)[:100]
                actions.append({
                    "type": row[0],
                    "description": desc[:100] if desc else "",
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

    async def get_server_metrics(self) -> dict[str, Any]:
        """
        Get server resource metrics (CPU, RAM, disk).

        Returns:
            Dict with server metrics
        """
        try:
            import os
            import psutil

            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Memory
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            memory_percent = memory.percent

            # Disk
            disk = psutil.disk_usage("/")
            disk_total_gb = disk.total / (1024**3)
            disk_used_gb = disk.used / (1024**3)
            disk_percent = disk.percent

            # Process info
            process = psutil.Process(os.getpid())
            process_memory_mb = process.memory_info().rss / (1024**2)

            return {
                "cpu_percent": round(cpu_percent, 1),
                "cpu_cores": cpu_count,
                "memory_total_gb": round(memory_total_gb, 1),
                "memory_used_gb": round(memory_used_gb, 1),
                "memory_percent": round(memory_percent, 1),
                "disk_total_gb": round(disk_total_gb, 1),
                "disk_used_gb": round(disk_used_gb, 1),
                "disk_percent": round(disk_percent, 1),
                "bot_memory_mb": round(process_memory_mb, 1),
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            logger.error(f"Error getting server metrics: {e}")
            return {"error": str(e)}

    async def get_deposit_details(self, hours: int = 24) -> dict[str, Any]:
        """
        Get detailed deposit statistics.

        Args:
            hours: Lookback period

        Returns:
            Dict with deposit details
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            # Deposits by status
            status_result = await self.session.execute(
                select(Deposit.status, func.count(Deposit.id), func.sum(Deposit.amount))
                .group_by(Deposit.status)
            )
            by_status = {
                row[0]: {"count": row[1], "amount": float(row[2] or 0)}
                for row in status_result.fetchall()
            }

            # Recent deposits list
            recent_result = await self.session.execute(
                select(
                    Deposit.amount,
                    Deposit.status,
                    Deposit.created_at,
                    User.username,
                )
                .join(User, Deposit.user_id == User.id)
                .where(Deposit.created_at >= since)
                .order_by(Deposit.created_at.desc())
                .limit(10)
            )
            recent_deposits = [
                {
                    "amount": float(row[0]),
                    "status": row[1],
                    "time": row[2].strftime("%d.%m %H:%M") if row[2] else "",
                    "user": row[3] or "Unknown",
                }
                for row in recent_result.fetchall()
            ]

            # Today's deposits
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0)
            today_result = await self.session.execute(
                select(func.count(Deposit.id), func.sum(Deposit.amount))
                .where(Deposit.created_at >= today_start)
            )
            today_row = today_result.fetchone()

            return {
                "by_status": by_status,
                "recent": recent_deposits,
                "today_count": today_row[0] or 0,
                "today_amount": float(today_row[1] or 0),
            }
        except Exception as e:
            logger.error(f"Error getting deposit details: {e}")
            return {"error": str(e)}

    async def get_withdrawal_details(self, hours: int = 24) -> dict[str, Any]:
        """
        Get detailed withdrawal statistics.

        Args:
            hours: Lookback period

        Returns:
            Dict with withdrawal details
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            # Withdrawals by status
            status_result = await self.session.execute(
                select(Transaction.status, func.count(Transaction.id), func.sum(Transaction.amount))
                .where(Transaction.type == "withdrawal")
                .group_by(Transaction.status)
            )
            by_status = {
                row[0]: {"count": row[1], "amount": float(row[2] or 0)}
                for row in status_result.fetchall()
            }

            # Pending withdrawals (detailed)
            pending_result = await self.session.execute(
                select(
                    Transaction.amount,
                    Transaction.created_at,
                    User.username,
                )
                .join(User, Transaction.user_id == User.id)
                .where(Transaction.type == "withdrawal")
                .where(Transaction.status == "pending")
                .order_by(Transaction.created_at.asc())
                .limit(20)
            )
            pending_list = [
                {
                    "amount": float(row[0]),
                    "waiting_since": row[1].strftime("%d.%m %H:%M") if row[1] else "",
                    "user": row[2] or "Unknown",
                }
                for row in pending_result.fetchall()
            ]

            return {
                "by_status": by_status,
                "pending_list": pending_list,
                "pending_count": len(pending_list),
            }
        except Exception as e:
            logger.error(f"Error getting withdrawal details: {e}")
            return {"error": str(e)}

    async def get_transaction_summary(self, hours: int = 24) -> dict[str, Any]:
        """
        Get transaction summary by type.

        Args:
            hours: Lookback period

        Returns:
            Dict with transaction summary
        """
        try:
            since = datetime.now(UTC) - timedelta(hours=hours)

            result = await self.session.execute(
                select(
                    Transaction.type,
                    func.count(Transaction.id),
                    func.sum(Transaction.amount)
                )
                .where(Transaction.created_at >= since)
                .group_by(Transaction.type)
            )

            summary = {}
            for row in result.fetchall():
                summary[row[0]] = {
                    "count": row[1],
                    "total": float(row[2] or 0)
                }

            return summary
        except Exception as e:
            logger.error(f"Error getting transaction summary: {e}")
            return {"error": str(e)}

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
        server_metrics = await self.get_server_metrics()
        deposit_details = await self.get_deposit_details(hours=24)
        withdrawal_details = await self.get_withdrawal_details(hours=24)
        transaction_summary = await self.get_transaction_summary(hours=24)

        return {
            "admin": admin_stats,
            "users": user_stats,
            "financial": financial_stats,
            "recent_actions": recent_actions,
            "system": system_health,
            "server": server_metrics,
            "deposits": deposit_details,
            "withdrawals": withdrawal_details,
            "transactions": transaction_summary,
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

        # Server metrics
        server = data.get("server", {})
        if server and not server.get("error"):
            lines.append("🖥️ СЕРВЕР:")
            lines.append(
                f"  CPU: {server.get('cpu_percent', 0)}% "
                f"({server.get('cpu_cores', 0)} ядер)"
            )
            lines.append(
                f"  RAM: {server.get('memory_used_gb', 0)}/"
                f"{server.get('memory_total_gb', 0)} GB "
                f"({server.get('memory_percent', 0)}%)"
            )
            lines.append(
                f"  Диск: {server.get('disk_used_gb', 0)}/"
                f"{server.get('disk_total_gb', 0)} GB "
                f"({server.get('disk_percent', 0)}%)"
            )
            lines.append(f"  Память бота: {server.get('bot_memory_mb', 0)} MB")
            lines.append("")

        # Deposit details
        deposits = data.get("deposits", {})
        if deposits and not deposits.get("error"):
            lines.append("💵 ДЕПОЗИТЫ (детали):")
            lines.append(
                f"  Сегодня: {deposits.get('today_count', 0)} шт "
                f"(${deposits.get('today_amount', 0):,.2f})"
            )
            by_status = deposits.get("by_status", {})
            for status, info in by_status.items():
                lines.append(
                    f"  {status}: {info.get('count', 0)} шт "
                    f"(${info.get('amount', 0):,.2f})"
                )
            recent = deposits.get("recent", [])
            if recent:
                lines.append("  Последние депозиты:")
                for dep in recent[:5]:
                    lines.append(
                        f"    - ${dep.get('amount', 0):.2f} от @{dep.get('user')} "
                        f"({dep.get('time')})"
                    )
            lines.append("")

        # Withdrawal details
        withdrawals = data.get("withdrawals", {})
        if withdrawals and not withdrawals.get("error"):
            pending_list = withdrawals.get("pending_list", [])
            if pending_list:
                lines.append("⏳ ОЖИДАЮЩИЕ ВЫВОДА:")
                for w in pending_list[:10]:
                    lines.append(
                        f"  - ${w.get('amount', 0):.2f} @{w.get('user')} "
                        f"(ждёт с {w.get('waiting_since')})"
                    )
                lines.append("")

        # Transaction summary
        txns = data.get("transactions", {})
        if txns and not txns.get("error"):
            lines.append("📊 ТРАНЗАКЦИИ ЗА 24Ч:")
            for tx_type, info in txns.items():
                lines.append(
                    f"  {tx_type}: {info.get('count', 0)} шт "
                    f"(${info.get('total', 0):,.2f})"
                )
            lines.append("")

        # System health
        system = data.get("system", {})
        lines.append("✅ СТАТУС СИСТЕМЫ:")
        lines.append(f"  База данных: {system.get('database', 'N/A')}")
        lines.append(f"  Общий статус: {system.get('status', 'N/A')}")

        return "\n".join(lines)
