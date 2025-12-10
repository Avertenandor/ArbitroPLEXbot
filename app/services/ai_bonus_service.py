"""
AI Bonus Service.

Provides bonus management tools for AI assistant with STRICT security:
- Only callable from admin AI assistant context
- Validates admin credentials before every operation
- Full audit logging

SECURITY: This service is ONLY accessible through the AI assistant
when a verified admin is in an authenticated admin session.
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository
from app.services.bonus_service import BonusService


class AIBonusService:
    """
    AI-powered bonus management service.
    
    SECURITY NOTES:
    - admin_data MUST come from authenticated admin session
    - All operations are logged with admin info
    - Amount limits enforced (1-10000 USDT)
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}

        # Extract admin info for security logging
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username") or self.admin_data.get("Имя")

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """
        Verify admin credentials from session data.
        
        Returns:
            Tuple of (admin_model, error_message)
        """
        if not self.admin_telegram_id:
            return None, "❌ ОШИБКА БЕЗОПАСНОСТИ: Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin:
            logger.warning(
                f"AI BONUS SECURITY: Unauthorized attempt from telegram_id={self.admin_telegram_id}"
            )
            return None, "❌ ОШИБКА БЕЗОПАСНОСТИ: Администратор не найден"

        if admin.is_blocked:
            logger.warning(
                f"AI BONUS SECURITY: Blocked admin attempt: {admin.telegram_id} (@{admin.username})"
            )
            return None, "❌ ОШИБКА: Администратор заблокирован"

        return admin, None

    async def _find_user(self, user_identifier: str) -> tuple[Any | None, str | None]:
        """
        Find user by identifier (@username or telegram_id).
        
        Args:
            user_identifier: @username or telegram_id
            
        Returns:
            Tuple of (user_model, error_message)
        """
        user_repo = UserRepository(self.session)

        # Try by username
        if user_identifier.startswith("@"):
            username = user_identifier[1:]
            user = await user_repo.get_by_username(username)
            if user:
                return user, None
            return None, f"❌ Пользователь @{username} не найден"

        # Try by telegram_id
        try:
            telegram_id = int(user_identifier)
            user = await user_repo.get_by_telegram_id(telegram_id)
            if user:
                return user, None
            return None, f"❌ Пользователь с ID {telegram_id} не найден"
        except ValueError:
            return None, "❌ Неверный формат: укажите @username или telegram_id"

    async def grant_bonus(
        self,
        user_identifier: str,
        amount: float,
        reason: str,
    ) -> dict[str, Any]:
        """
        Grant bonus to a user.
        
        SECURITY: Verifies admin credentials before execution.
        
        Args:
            user_identifier: @username or telegram_id
            amount: Bonus amount in USDT (1-10000)
            reason: Reason for granting bonus
            
        Returns:
            Result dict with status and details
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Validate amount
        if amount < 1:
            return {"success": False, "error": "❌ Минимальная сумма бонуса: 1 USDT"}
        if amount > 10000:
            return {"success": False, "error": "❌ Максимальная сумма бонуса: 10,000 USDT"}

        # Validate reason
        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину начисления (минимум 5 символов)"}

        # Find user
        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Grant bonus
        bonus_service = BonusService(self.session)
        bonus, error = await bonus_service.grant_bonus(
            user_id=user.id,
            amount=Decimal(str(amount)),
            reason=f"[АРЬЯ] {reason}",
            admin_id=admin.id,
        )

        if error:
            return {"success": False, "error": f"❌ Ошибка: {error}"}

        await self.session.commit()

        # Log action
        logger.info(
            f"AI BONUS GRANT: Admin {admin.telegram_id} (@{admin.username}) "
            f"granted {amount} USDT to user {user.id} (@{user.username}): {reason}"
        )

        return {
            "success": True,
            "bonus_id": bonus.id,
            "user": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
            "amount": f"{amount} USDT",
            "roi_cap": f"{amount * 5} USDT",
            "reason": reason,
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": f"✅ Бонус {amount} USDT успешно начислен пользователю @{user.username or user.telegram_id}!"
        }

    async def get_user_bonuses(
        self,
        user_identifier: str,
        active_only: bool = False,
    ) -> dict[str, Any]:
        """
        Get user's bonus list.
        
        Args:
            user_identifier: @username or telegram_id
            active_only: Only return active bonuses
            
        Returns:
            Result dict with bonuses list
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Find user
        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Get bonuses
        bonus_service = BonusService(self.session)
        bonuses = await bonus_service.get_user_bonuses(user.id, active_only=active_only)

        if not bonuses:
            status = "активных " if active_only else ""
            return {
                "success": True,
                "user": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
                "bonuses": [],
                "message": f"ℹ️ У пользователя нет {status}бонусов"
            }

        # Format bonuses
        bonuses_list = []
        for b in bonuses:
            status = "🟢 Активен" if b.is_active else ("✅ Завершён" if b.is_roi_completed else "❌ Отменён")
            bonuses_list.append({
                "id": b.id,
                "amount": float(b.amount),
                "status": status,
                "roi_progress": f"{b.roi_progress_percent:.1f}%",
                "roi_paid": float(b.roi_paid_amount),
                "roi_cap": float(b.roi_cap_amount),
                "reason": b.reason[:50] if b.reason else "—",
                "created": b.created_at.strftime("%d.%m.%Y") if b.created_at else "—",
            })

        return {
            "success": True,
            "user": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
            "total_count": len(bonuses_list),
            "active_count": sum(1 for b in bonuses if b.is_active),
            "bonuses": bonuses_list,
            "message": f"📋 Найдено {len(bonuses_list)} бонусов"
        }

    async def cancel_bonus(
        self,
        bonus_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """
        Cancel an active bonus.
        
        SECURITY: Verifies admin credentials before execution.
        
        Args:
            bonus_id: Bonus ID to cancel
            reason: Reason for cancellation
            
        Returns:
            Result dict with status
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Validate reason
        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину отмены (минимум 5 символов)"}

        # Cancel bonus
        bonus_service = BonusService(self.session)
        success, error = await bonus_service.cancel_bonus(
            bonus_id=bonus_id,
            admin_id=admin.id,
            reason=f"[АРЬЯ] {reason}",
        )

        if not success:
            return {"success": False, "error": f"❌ Ошибка: {error}"}

        await self.session.commit()

        # Log action
        logger.info(
            f"AI BONUS CANCEL: Admin {admin.telegram_id} (@{admin.username}) "
            f"cancelled bonus {bonus_id}: {reason}"
        )

        return {
            "success": True,
            "bonus_id": bonus_id,
            "reason": reason,
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": f"✅ Бонус ID {bonus_id} успешно отменён!"
        }
