"""AI Withdrawals Service.

Provides withdrawal management for AI assistant.

SECURITY NOTE:
- Any active (non-blocked) admin is allowed to approve/reject via ARYA.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.services.ai.commons import verify_admin


class AIWithdrawalsService:
    """
    AI-powered withdrawals management service.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        return await verify_admin(self.session, self.admin_telegram_id)

    def _is_trusted_admin(self) -> bool:
        """All verified admins are trusted for ARYA withdrawals tools."""
        return True

    async def get_pending_withdrawals(
        self,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get list of pending withdrawal requests.

        Args:
            limit: Maximum number of results

        Returns:
            List of pending withdrawals
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Get pending withdrawals with user info
        stmt = (
            select(Transaction)
            .where(
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status == TransactionStatus.PENDING.value,
            )
            .order_by(Transaction.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        withdrawals = list(result.scalars().all())

        if not withdrawals:
            return {
                "success": True,
                "count": 0,
                "withdrawals": [],
                "message": "✅ Нет ожидающих заявок на вывод",
            }

        withdrawals_list = []
        for w in withdrawals:
            user_stmt = select(User).where(User.id == w.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            user_info = (
                f"@{user.username}"
                if user and user.username
                else f"ID:{w.user_id}"
            )

            # Format address
            to_address = None
            if w.to_address:
                to_address = (
                    w.to_address[:10] + "..." + w.to_address[-8:]
                )

            # Format created date
            created = None
            if w.created_at:
                created = w.created_at.strftime("%d.%m.%Y %H:%M")

            withdrawals_list.append(
                {
                    "id": w.id,
                    "user": user_info,
                    "user_id": w.user_id,
                    "amount": float(w.amount),
                    "to_address": to_address,
                    "created": created,
                }
            )

        return {
            "success": True,
            "count": len(withdrawals_list),
            "withdrawals": withdrawals_list,
            "message": f"💸 Ожидающих заявок: {len(withdrawals_list)}",
        }

    async def get_withdrawal_details(
        self,
        withdrawal_id: int,
    ) -> dict[str, Any]:
        """
        Get detailed info about a withdrawal.

        Args:
            withdrawal_id: Transaction ID

        Returns:
            Withdrawal details
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = select(Transaction).where(
            Transaction.id == withdrawal_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
        )
        result = await self.session.execute(stmt)
        withdrawal = result.scalar_one_or_none()

        if not withdrawal:
            return {"success": False, "error": f"❌ Заявка #{withdrawal_id} не найдена"}

        # Get user info
        user_stmt = select(User).where(User.id == withdrawal.user_id)
        user_result = await self.session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        status_emoji = {
            TransactionStatus.PENDING.value: "⏳ Ожидает",
            TransactionStatus.CONFIRMED.value: "✅ Выполнена",
            TransactionStatus.FAILED.value: "❌ Отклонена",
        }

        # Mask wallet address for security
        masked_address = withdrawal.to_address
        if masked_address and len(masked_address) > 20:
            masked_address = masked_address[:10] + "..." + masked_address[-8:]

        # Format user info
        user_info = (
            f"@{user.username}"
            if user and user.username
            else f"ID:{withdrawal.user_id}"
        )

        # Format created date
        created = None
        if withdrawal.created_at:
            created = withdrawal.created_at.strftime("%d.%m.%Y %H:%M")

        return {
            "success": True,
            "withdrawal": {
                "id": withdrawal.id,
                "user": user_info,
                "user_id": withdrawal.user_id,
                "user_balance": float(user.balance) if user else 0,
                "amount": float(withdrawal.amount),
                "to_address": masked_address,  # MASKED for security
                "status": status_emoji.get(
                    withdrawal.status, withdrawal.status
                ),
                "created": created,
                "description": withdrawal.description,
            },
            "message": f"📋 Заявка на вывод #{withdrawal_id}",
        }

    async def approve_withdrawal(
        self,
        withdrawal_id: int,
        tx_hash: str | None = None,
    ) -> dict[str, Any]:
        """
        Approve a withdrawal request.

        SECURITY: Only trusted admins can approve!

        Args:
            withdrawal_id: Transaction ID
            tx_hash: Optional blockchain transaction hash

        Returns:
            Result
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Security check
        if not self._is_trusted_admin():
            logger.warning(
                f"AI WITHDRAWALS SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to approve "
                f"withdrawal {withdrawal_id}"
            )
            error_msg = (
                "❌ У вас нет прав на одобрение выводов. "
                "Обратитесь к владельцу."
            )
            return {"success": False, "error": error_msg}

        # Get withdrawal
        stmt = select(Transaction).where(
            Transaction.id == withdrawal_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
        )
        result = await self.session.execute(stmt)
        withdrawal = result.scalar_one_or_none()

        if not withdrawal:
            return {
                "success": False,
                "error": f"❌ Заявка #{withdrawal_id} не найдена",
            }

        if withdrawal.status != TransactionStatus.PENDING.value:
            error_msg = (
                f"❌ Заявка уже обработана "
                f"(статус: {withdrawal.status})"
            )
            return {"success": False, "error": error_msg}

        # Approve
        withdrawal.status = TransactionStatus.CONFIRMED.value
        # Note: processed_at, processed_by_admin_id are not in Transaction model
        if tx_hash:
            withdrawal.tx_hash = tx_hash
        approval_note = f" [АРЬЯ: Одобрено @{admin.username}]"
        withdrawal.description = (
            (withdrawal.description or "") + approval_note
        )

        await self.session.commit()

        # Get user info
        user_stmt = select(User).where(User.id == withdrawal.user_id)
        user_result = await self.session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        logger.info(
            f"AI WITHDRAWALS: Admin {admin.telegram_id} "
            f"approved withdrawal {withdrawal_id} "
            f"({withdrawal.amount} USDT)"
        )

        user_info = (
            f"@{user.username}"
            if user and user.username
            else f"ID:{withdrawal.user_id}"
        )

        return {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "user": user_info,
            "amount": float(withdrawal.amount),
            "tx_hash": tx_hash,
            "admin": f"@{admin.username}",
            "message": f"✅ Вывод #{withdrawal_id} одобрен",
        }

    async def reject_withdrawal(
        self,
        withdrawal_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """
        Reject a withdrawal request.

        SECURITY: Only trusted admins can reject!

        Args:
            withdrawal_id: Transaction ID
            reason: Rejection reason

        Returns:
            Result
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Security check
        if not self._is_trusted_admin():
            logger.warning(
                f"AI WITHDRAWALS SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to reject "
                f"withdrawal {withdrawal_id}"
            )
            error_msg = "❌ У вас нет прав на отклонение выводов."
            return {"success": False, "error": error_msg}

        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину отклонения"}

        # Get withdrawal
        stmt = select(Transaction).where(
            Transaction.id == withdrawal_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
        )
        result = await self.session.execute(stmt)
        withdrawal = result.scalar_one_or_none()

        if not withdrawal:
            return {
                "success": False,
                "error": f"❌ Заявка #{withdrawal_id} не найдена",
            }

        if withdrawal.status != TransactionStatus.PENDING.value:
            error_msg = (
                f"❌ Заявка уже обработана "
                f"(статус: {withdrawal.status})"
            )
            return {"success": False, "error": error_msg}

        # Get user to refund balance
        user_stmt = select(User).where(User.id == withdrawal.user_id)
        user_result = await self.session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        # Refund balance
        if user:
            user.balance = (user.balance or Decimal("0")) + withdrawal.amount

        # Reject
        withdrawal.status = TransactionStatus.FAILED.value
        # Note: processed_at, processed_by_admin_id are not in Transaction model
        rejection_note = (
            f" [АРЬЯ: Отклонено @{admin.username}: {reason}]"
        )
        withdrawal.description = (
            (withdrawal.description or "") + rejection_note
        )

        await self.session.commit()

        logger.info(
            f"AI WITHDRAWALS: Admin {admin.telegram_id} "
            f"rejected withdrawal {withdrawal_id}: {reason}"
        )

        user_info = (
            f"@{user.username}"
            if user and user.username
            else f"ID:{withdrawal.user_id}"
        )

        message = (
            f"❌ Вывод #{withdrawal_id} отклонён, "
            "средства возвращены на баланс"
        )

        return {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "user": user_info,
            "amount": float(withdrawal.amount),
            "reason": reason,
            "refunded": True,
            "admin": f"@{admin.username}",
            "message": message,
        }

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive withdrawal statistics.

        Returns:
            Statistics including totals, counts by status, averages
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        status_stmt = (
            select(
                Transaction.status,
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total"),
            )
            .where(Transaction.type == TransactionType.WITHDRAWAL.value)
            .group_by(Transaction.status)
        )
        status_result = await self.session.execute(status_stmt)
        status_rows = status_result.all()

        status_stats: dict[str, dict[str, float]] = {}
        for row in status_rows:
            status_stats[row.status] = {
                "count": float(row.count or 0),
                "total": float(row.total or 0),
            }

        total_count = int(sum(s["count"] for s in status_stats.values()))
        total_amount = float(
            sum(s["total"] for s in status_stats.values())
        )

        default_stats = {"count": 0.0, "total": 0.0}
        pending = status_stats.get(
            TransactionStatus.PENDING.value, default_stats
        )
        processing = status_stats.get(
            TransactionStatus.PROCESSING.value, default_stats
        )
        confirmed = status_stats.get(
            TransactionStatus.CONFIRMED.value, default_stats
        )
        failed = status_stats.get(
            TransactionStatus.FAILED.value, default_stats
        )

        avg_stmt = (
            select(func.avg(Transaction.amount))
            .where(Transaction.type == TransactionType.WITHDRAWAL.value)
            .where(Transaction.status == TransactionStatus.CONFIRMED.value)
        )
        avg_result = await self.session.execute(avg_stmt)
        avg_amount = float(avg_result.scalar() or 0)

        return {
            "success": True,
            "statistics": {
                "total_withdrawals": total_count,
                "total_amount": round(total_amount, 2),
                "pending": {
                    "count": int(pending["count"] + processing["count"]),
                    "amount": round(pending["total"] + processing["total"], 2),
                },
                "completed": {
                    "count": int(confirmed["count"]),
                    "amount": round(confirmed["total"], 2),
                },
                "rejected": {
                    "count": int(failed["count"]),
                    "amount": round(failed["total"], 2),
                },
                "average_amount": round(avg_amount, 2),
            },
            "message": "📊 Статистика выводов",
        }
