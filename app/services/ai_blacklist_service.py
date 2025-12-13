"""
AI Blacklist Service.

Provides blacklist management for AI assistant:
- View blacklist entries
- Add to blacklist
- Remove from blacklist
- Check if user is blacklisted

SECURITY: Add/remove require TRUSTED_ADMIN access.
"""

from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blacklist import Blacklist, BlacklistActionType
from app.repositories.blacklist_repository import BlacklistRepository
from app.repositories.user_repository import UserRepository
from app.services.ai.commons import verify_admin


"""NOTE: Access control

Per requirement: any active (non-blocked) admin can manage blacklist via ARYA.
"""


class AIBlacklistService:
    """
    AI-powered blacklist management service.
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
        self.blacklist_repo = BlacklistRepository(session)

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        return await verify_admin(self.session, self.admin_telegram_id)

    def _is_trusted_admin(self) -> bool:
        """All verified admins are trusted for ARYA blacklist tools."""
        return True

    async def get_blacklist(self, limit: int = 50) -> dict[str, Any]:
        """
        Get active blacklist entries.

        Args:
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Any verified admin can view blacklist
        if not self._is_trusted_admin():
            error_msg = "❌ Недостаточно прав для просмотра чёрного списка"
            return {"success": False, "error": error_msg}

        # Get active entries
        stmt = (
            select(Blacklist)
            .where(Blacklist.is_active == True)
            .order_by(Blacklist.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        entries = list(result.scalars().all())

        if not entries:
            return {
                "success": True,
                "count": 0,
                "entries": [],
                "message": "✅ Чёрный список пуст",
            }

        entries_list = []
        for e in entries:
            action_emoji = {
                BlacklistActionType.REGISTRATION_DENIED: "🚫",
                BlacklistActionType.BLOCKED: "⛔",
                BlacklistActionType.TERMINATED: "💀",
            }.get(e.action_type, "❓")

            identifier = None
            if e.telegram_id:
                identifier = f"TG: {e.telegram_id}"
            elif e.username:
                identifier = f"@{e.username}"
            elif e.wallet_address:
                identifier = f"Wallet: {e.wallet_address[:10]}..."

            action_type_value = (
                e.action_type.value if e.action_type else 'unknown'
            )
            action_type_str = f"{action_emoji} {action_type_value}"
            created_str = (
                e.created_at.strftime("%d.%m.%Y %H:%M")
                if e.created_at
                else None
            )

            entries_list.append(
                {
                    "id": e.id,
                    "identifier": identifier,
                    "telegram_id": e.telegram_id,
                    "username": e.username,
                    "wallet_address": e.wallet_address,
                    "action_type": action_type_str,
                    "reason": e.reason,
                    "created": created_str,
                }
            )

        # Count total
        count_stmt = (
            select(func.count(Blacklist.id))
            .where(Blacklist.is_active == True)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        return {
            "success": True,
            "count": len(entries_list),
            "total": total,
            "entries": entries_list,
            "message": f"🚫 Записей в чёрном списке: {total}",
        }

    async def check_blacklist(self, identifier: str) -> dict[str, Any]:
        """
        Check if user/wallet is blacklisted.

        Args:
            identifier: @username, telegram_id, or wallet address
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Any verified admin can check blacklist
        if not self._is_trusted_admin():
            error_msg = "❌ Недостаточно прав для проверки чёрного списка"
            return {"success": False, "error": error_msg}

        identifier = identifier.strip()

        # Build query based on identifier type
        stmt = select(Blacklist).where(Blacklist.is_active == True)

        if identifier.startswith("@"):
            username = identifier[1:]
            stmt = stmt.where(Blacklist.username == username)
        elif identifier.isdigit():
            telegram_id = int(identifier)
            stmt = stmt.where(Blacklist.telegram_id == telegram_id)
        elif identifier.startswith("0x") and len(identifier) == 42:
            stmt = stmt.where(Blacklist.wallet_address == identifier)
        else:
            error_msg = "❌ Укажите @username, telegram_id или wallet"
            return {"success": False, "error": error_msg}

        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry:
            action_type_val = (
                entry.action_type.value if entry.action_type else None
            )
            created_val = (
                entry.created_at.strftime("%d.%m.%Y %H:%M")
                if entry.created_at
                else None
            )
            return {
                "success": True,
                "is_blacklisted": True,
                "entry": {
                    "id": entry.id,
                    "reason": entry.reason,
                    "action_type": action_type_val,
                    "created": created_val,
                },
                "message": f"🚫 {identifier} В ЧЁРНОМ СПИСКЕ",
            }

        message = f"✅ {identifier} НЕ в чёрном списке"
        return {"success": True, "is_blacklisted": False, "message": message}

    async def add_to_blacklist(
        self,
        identifier: str,
        reason: str,
        action_type: str = "pre_block",
    ) -> dict[str, Any]:
        """
        Add user/wallet to blacklist.

        SECURITY: TRUSTED ADMIN only!

        Args:
            identifier: @username, telegram_id, or wallet
            reason: Reason for blacklisting
            action_type: pre_block, post_block, or termination
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_trusted_admin():
            log_msg = (
                f"AI BLACKLIST SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to add to blacklist"
            )
            logger.warning(log_msg)
            error_msg = "❌ Нет прав на добавление в чёрный список"
            return {"success": False, "error": error_msg}

        identifier = identifier.strip()

        if not reason or len(reason) < 5:
            error_msg = "❌ Укажите причину (минимум 5 символов)"
            return {"success": False, "error": error_msg}

        # Validate action type
        action_map = {
            "registration_denied": BlacklistActionType.REGISTRATION_DENIED,
            "blocked": BlacklistActionType.BLOCKED,
            "terminated": BlacklistActionType.TERMINATED,
        }
        if action_type not in action_map:
            allowed_types = ', '.join(action_map.keys())
            error_msg = f"❌ Неверный action_type. Допустимые: {allowed_types}"
            return {"success": False, "error": error_msg}

        # Determine identifier type
        telegram_id = None
        username = None
        wallet_address = None

        if identifier.startswith("@"):
            username = identifier[1:]
        elif identifier.isdigit():
            telegram_id = int(identifier)
        elif identifier.startswith("0x") and len(identifier) == 42:
            wallet_address = identifier
        else:
            error_msg = "❌ Укажите @username, telegram_id или wallet"
            return {"success": False, "error": error_msg}

        # Check if already blacklisted
        check_result = await self.check_blacklist(identifier)
        if check_result.get("is_blacklisted"):
            error_msg = f"❌ {identifier} уже в чёрном списке"
            return {"success": False, "error": error_msg}

        # Create entry
        entry = Blacklist(
            telegram_id=telegram_id,
            username=username,
            wallet_address=wallet_address,
            reason=f"[АРЬЯ] {reason}",
            action_type=action_map[action_type],
            is_active=True,
            added_by_admin_id=admin.id if admin else None,
        )
        self.session.add(entry)
        await self.session.commit()

        log_msg = (
            f"AI BLACKLIST: Admin {self.admin_telegram_id} added "
            f"{identifier} to blacklist. "
            f"Reason: {reason}, Action: {action_type}"
        )
        logger.warning(log_msg)

        return {
            "success": True,
            "identifier": identifier,
            "action_type": action_type,
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"🚫 {identifier} добавлен в чёрный список",
        }

    async def remove_from_blacklist(
        self,
        identifier: str,
        reason: str,
    ) -> dict[str, Any]:
        """
        Remove user/wallet from blacklist.

        SECURITY: TRUSTED ADMIN only!

        Args:
            identifier: @username, telegram_id, or wallet
            reason: Reason for removal
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_trusted_admin():
            log_msg = (
                f"AI BLACKLIST SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to remove from blacklist"
            )
            logger.warning(log_msg)
            error_msg = "❌ Нет прав на удаление из чёрного списка"
            return {"success": False, "error": error_msg}

        identifier = identifier.strip()

        if not reason or len(reason) < 5:
            error_msg = "❌ Укажите причину (минимум 5 символов)"
            return {"success": False, "error": error_msg}

        # Find entry
        stmt = select(Blacklist).where(Blacklist.is_active == True)

        if identifier.startswith("@"):
            username = identifier[1:]
            stmt = stmt.where(Blacklist.username == username)
        elif identifier.isdigit():
            telegram_id = int(identifier)
            stmt = stmt.where(Blacklist.telegram_id == telegram_id)
        elif identifier.startswith("0x") and len(identifier) == 42:
            stmt = stmt.where(Blacklist.wallet_address == identifier)
        else:
            error_msg = "❌ Укажите @username, telegram_id или wallet"
            return {"success": False, "error": error_msg}

        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry:
            error_msg = f"❌ {identifier} не найден в чёрном списке"
            return {"success": False, "error": error_msg}

        # Deactivate
        entry.is_active = False
        await self.session.commit()

        log_msg = (
            f"AI BLACKLIST: Admin {self.admin_telegram_id} removed "
            f"{identifier} from blacklist. Reason: {reason}"
        )
        logger.info(log_msg)

        return {
            "success": True,
            "identifier": identifier,
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"✅ {identifier} удалён из чёрного списка",
        }
