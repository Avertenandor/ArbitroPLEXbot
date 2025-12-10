"""
AI FinPass Recovery Service.

Provides financial password recovery management for AI assistant:
- View pending recovery requests
- Approve/reject requests
- View request details

SECURITY: Approve/reject require TRUSTED_ADMIN access.
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_password_recovery import FinancialPasswordRecovery
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository
from app.services.finpass_recovery_service import (
    FinancialRecoveryStatus,
    FinpassRecoveryService,
)

# Only these admins can approve/reject
TRUSTED_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Командир/super_admin)
    1691026253,  # @AI_XAN (Саша - Tech Deputy)
    241568583,   # @natder (Наташа)
    6540613027,  # @ded_vtapkax (Влад)
]


class AIFinpassService:
    """
    AI-powered financial password recovery service.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")
        self.finpass_service = FinpassRecoveryService(session)
        self.user_repo = UserRepository(session)

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
        """Check if current admin can approve/reject."""
        return self.admin_telegram_id in TRUSTED_ADMIN_IDS

    async def get_pending_requests(self, limit: int = 20) -> dict[str, Any]:
        """
        Get pending finpass recovery requests.
        
        Args:
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        # Only trusted admins can view pending requests
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Недостаточно прав для просмотра заявок"
            }
        
        # Get pending + in_review
        stmt = select(FinancialPasswordRecovery).where(
            FinancialPasswordRecovery.status.in_([
                FinancialRecoveryStatus.PENDING.value,
                FinancialRecoveryStatus.IN_REVIEW.value,
            ])
        ).order_by(FinancialPasswordRecovery.created_at.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        requests = list(result.scalars().all())
        
        if not requests:
            return {
                "success": True,
                "count": 0,
                "requests": [],
                "message": "✅ Нет ожидающих заявок на восстановление"
            }
        
        requests_list = []
        for r in requests:
            user = await self.user_repo.get_by_id(r.user_id)
            user_info = f"@{user.username}" if user and user.username else f"ID:{r.user_id}"
            
            status_emoji = {
                FinancialRecoveryStatus.PENDING.value: "⏳",
                FinancialRecoveryStatus.IN_REVIEW.value: "🔍",
            }.get(r.status, "❓")
            
            requests_list.append({
                "id": r.id,
                "user": user_info,
                "user_id": r.user_id,
                "status": f"{status_emoji} {r.status}",
                "reason": r.reason[:100] + "..." if len(r.reason) > 100 else r.reason,
                "created": r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else None,
            })
        
        return {
            "success": True,
            "count": len(requests_list),
            "requests": requests_list,
            "message": f"🔐 Заявок на восстановление: {len(requests_list)}"
        }

    async def get_request_details(self, request_id: int) -> dict[str, Any]:
        """
        Get detailed info about a recovery request.
        
        Args:
            request_id: Request ID
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        # Only trusted admins can view request details
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Недостаточно прав для просмотра деталей заявки"
            }
        
        stmt = select(FinancialPasswordRecovery).where(
            FinancialPasswordRecovery.id == request_id
        )
        result = await self.session.execute(stmt)
        request = result.scalar_one_or_none()
        
        if not request:
            return {"success": False, "error": f"❌ Заявка #{request_id} не найдена"}
        
        user = await self.user_repo.get_by_id(request.user_id)
        user_info = f"@{user.username}" if user and user.username else f"ID:{request.user_id}"
        
        return {
            "success": True,
            "request": {
                "id": request.id,
                "user": user_info,
                "user_id": request.user_id,
                "status": request.status,
                "reason": request.reason,
                "video_file_id": request.video_file_id,
                "created_at": request.created_at.strftime("%d.%m.%Y %H:%M") if request.created_at else None,
                "updated_at": request.updated_at.strftime("%d.%m.%Y %H:%M") if request.updated_at else None,
                "reviewed_by_admin_id": request.reviewed_by_admin_id,
                "reject_reason": request.reject_reason,
            },
            "message": f"🔐 Детали заявки #{request_id}"
        }

    async def approve_request(
        self,
        request_id: int,
        notes: str = "",
    ) -> dict[str, Any]:
        """
        Approve a finpass recovery request.
        
        SECURITY: TRUSTED ADMIN only!
        
        Args:
            request_id: Request ID
            notes: Optional admin notes
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            logger.warning(
                f"AI FINPASS SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to approve finpass request"
            )
            return {"success": False, "error": "❌ Нет прав на одобрение заявок"}
        
        stmt = select(FinancialPasswordRecovery).where(
            FinancialPasswordRecovery.id == request_id
        )
        result = await self.session.execute(stmt)
        request = result.scalar_one_or_none()
        
        if not request:
            return {"success": False, "error": f"❌ Заявка #{request_id} не найдена"}
        
        if request.status not in [
            FinancialRecoveryStatus.PENDING.value,
            FinancialRecoveryStatus.IN_REVIEW.value,
        ]:
            return {
                "success": False,
                "error": f"❌ Заявка уже обработана (статус: {request.status})"
            }
        
        # Approve
        request.status = FinancialRecoveryStatus.APPROVED.value
        request.reviewed_by_admin_id = admin.id if admin else None
        request.updated_at = datetime.now(UTC)
        
        await self.session.commit()
        
        user = await self.user_repo.get_by_id(request.user_id)
        user_info = f"@{user.username}" if user and user.username else f"ID:{request.user_id}"
        
        logger.info(
            f"AI FINPASS: Admin {self.admin_telegram_id} approved request #{request_id} "
            f"for user {request.user_id}. Notes: {notes}"
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "user": user_info,
            "admin": f"@{self.admin_username}",
            "notes": notes,
            "message": f"✅ Заявка #{request_id} одобрена"
        }

    async def reject_request(
        self,
        request_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """
        Reject a finpass recovery request.
        
        SECURITY: TRUSTED ADMIN only!
        
        Args:
            request_id: Request ID
            reason: Rejection reason
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not self._is_trusted_admin():
            logger.warning(
                f"AI FINPASS SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to reject finpass request"
            )
            return {"success": False, "error": "❌ Нет прав на отклонение заявок"}
        
        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину отклонения"}
        
        stmt = select(FinancialPasswordRecovery).where(
            FinancialPasswordRecovery.id == request_id
        )
        result = await self.session.execute(stmt)
        request = result.scalar_one_or_none()
        
        if not request:
            return {"success": False, "error": f"❌ Заявка #{request_id} не найдена"}
        
        if request.status not in [
            FinancialRecoveryStatus.PENDING.value,
            FinancialRecoveryStatus.IN_REVIEW.value,
        ]:
            return {
                "success": False,
                "error": f"❌ Заявка уже обработана (статус: {request.status})"
            }
        
        # Reject
        request.status = FinancialRecoveryStatus.REJECTED.value
        request.reviewed_by_admin_id = admin.id if admin else None
        request.reject_reason = f"[АРЬЯ] {reason}"
        request.updated_at = datetime.now(UTC)
        
        await self.session.commit()
        
        user = await self.user_repo.get_by_id(request.user_id)
        user_info = f"@{user.username}" if user and user.username else f"ID:{request.user_id}"
        
        logger.info(
            f"AI FINPASS: Admin {self.admin_telegram_id} rejected request #{request_id} "
            f"for user {request.user_id}. Reason: {reason}"
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "user": user_info,
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"❌ Заявка #{request_id} отклонена"
        }

    async def get_finpass_stats(self) -> dict[str, Any]:
        """
        Get finpass recovery statistics.
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        # Count by status
        stats = {}
        for status in FinancialRecoveryStatus:
            stmt = select(func.count(FinancialPasswordRecovery.id)).where(
                FinancialPasswordRecovery.status == status.value
            )
            result = await self.session.execute(stmt)
            stats[status.value] = result.scalar() or 0
        
        return {
            "success": True,
            "stats": stats,
            "pending": stats.get(FinancialRecoveryStatus.PENDING.value, 0),
            "in_review": stats.get(FinancialRecoveryStatus.IN_REVIEW.value, 0),
            "approved": stats.get(FinancialRecoveryStatus.APPROVED.value, 0),
            "rejected": stats.get(FinancialRecoveryStatus.REJECTED.value, 0),
            "message": "🔐 Статистика восстановления финпаролей"
        }
