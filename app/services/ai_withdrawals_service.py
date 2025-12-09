"""
AI Withdrawals Service.

Provides withdrawal management for AI assistant.
SECURITY: Only trusted admins can approve/reject.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.admin_repository import AdminRepository

# Same whitelist as in ai_users_service
TRUSTED_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Boss/super_admin)
    1691026253,  # @AI_XAN (Tech Deputy)
    241568583,   # @natder (Наташа)
    6540613027,  # @ded_vtapkax
]


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
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"

        return admin, None

    def _is_trusted_admin(self) -> bool:
        """Check if current admin is in trusted whitelist."""
        return self.admin_telegram_id in TRUSTED_ADMIN_IDS

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
                "message": "✅ Нет ожидающих заявок на вывод"
            }

        withdrawals_list = []
        for w in withdrawals:
            # Get user info
            user_stmt = select(User).where(User.id == w.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            user_info = f"@{user.username}" if user and user.username else f"ID:{w.user_id}"

            withdrawals_list.append({
                "id": w.id,
                "user": user_info,
                "user_id": w.user_id,
                "amount": float(w.amount),
                "to_address": w.to_address[:10] + "..." + w.to_address[-8:] if w.to_address else None,
                "created": w.created_at.strftime("%d.%m.%Y %H:%M") if w.created_at else None,
            })

        return {
            "success": True,
            "count": len(withdrawals_list),
            "withdrawals": withdrawals_list,
            "message": f"💸 Ожидающих заявок: {len(withdrawals_list)}"
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

        return {
            "success": True,
            "withdrawal": {
                "id": withdrawal.id,
                "user": f"@{user.username}" if user and user.username else f"ID:{withdrawal.user_id}",
                "user_id": withdrawal.user_id,
                "user_balance": float(user.balance) if user else 0,
                "amount": float(withdrawal.amount),
                "to_address": withdrawal.to_address,
                "status": status_emoji.get(withdrawal.status, withdrawal.status),
                "created": withdrawal.created_at.strftime("%d.%m.%Y %H:%M") if withdrawal.created_at else None,
                "description": withdrawal.description,
            },
            "message": f"📋 Заявка на вывод #{withdrawal_id}"
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
                f"AI WITHDRAWALS SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to approve withdrawal {withdrawal_id}"
            )
            return {
                "success": False,
                "error": "❌ У вас нет прав на одобрение выводов. Обратитесь к владельцу."
            }

        # Get withdrawal
        stmt = select(Transaction).where(
            Transaction.id == withdrawal_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
        )
        result = await self.session.execute(stmt)
        withdrawal = result.scalar_one_or_none()

        if not withdrawal:
            return {"success": False, "error": f"❌ Заявка #{withdrawal_id} не найдена"}

        if withdrawal.status != TransactionStatus.PENDING.value:
            return {
                "success": False,
                "error": f"❌ Заявка уже обработана (статус: {withdrawal.status})"
            }

        # Approve
        withdrawal.status = TransactionStatus.CONFIRMED.value
        # Note: processed_at, processed_by_admin_id are not in Transaction model
        if tx_hash:
            withdrawal.tx_hash = tx_hash
        withdrawal.description = (withdrawal.description or "") + f" [АРЬЯ: Одобрено @{admin.username}]"

        await self.session.commit()

        # Get user info
        user_stmt = select(User).where(User.id == withdrawal.user_id)
        user_result = await self.session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        logger.info(
            f"AI WITHDRAWALS: Admin {admin.telegram_id} approved "
            f"withdrawal {withdrawal_id} ({withdrawal.amount} USDT)"
        )

        return {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "user": f"@{user.username}" if user and user.username else f"ID:{withdrawal.user_id}",
            "amount": float(withdrawal.amount),
            "tx_hash": tx_hash,
            "admin": f"@{admin.username}",
            "message": f"✅ Вывод #{withdrawal_id} одобрен"
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
                f"AI WITHDRAWALS SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to reject withdrawal {withdrawal_id}"
            )
            return {
                "success": False,
                "error": "❌ У вас нет прав на отклонение выводов."
            }

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
            return {"success": False, "error": f"❌ Заявка #{withdrawal_id} не найдена"}

        if withdrawal.status != TransactionStatus.PENDING.value:
            return {
                "success": False,
                "error": f"❌ Заявка уже обработана (статус: {withdrawal.status})"
            }

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
        withdrawal.description = (
            (withdrawal.description or "") +
            f" [АРЬЯ: Отклонено @{admin.username}: {reason}]"
        )

        await self.session.commit()

        logger.info(
            f"AI WITHDRAWALS: Admin {admin.telegram_id} rejected "
            f"withdrawal {withdrawal_id}: {reason}"
        )

        return {
            "success": True,
            "withdrawal_id": withdrawal_id,
            "user": f"@{user.username}" if user and user.username else f"ID:{withdrawal.user_id}",
            "amount": float(withdrawal.amount),
            "reason": reason,
            "refunded": True,
            "admin": f"@{admin.username}",
            "message": f"❌ Вывод #{withdrawal_id} отклонён, средства возвращены на баланс"
        }
