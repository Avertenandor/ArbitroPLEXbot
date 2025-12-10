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
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blacklist import Blacklist, BlacklistActionType
from app.repositories.admin_repository import AdminRepository
from app.repositories.blacklist_repository import BlacklistRepository
from app.repositories.user_repository import UserRepository

# Only these admins can modify blacklist
TRUSTED_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Командир/super_admin)
    1691026253,  # @AI_XAN (Саша - Tech Deputy)
    241568583,   # @natder (Наташа)
    6540613027,  # @ded_vtapkax (Влад)
]


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
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"

        return admin, None

    def _is_trusted_admin(self) -> bool:
        """Check if current admin can modify blacklist."""
        return self.admin_telegram_id in TRUSTED_ADMIN_IDS

    async def get_blacklist(self, limit: int = 50) -> dict[str, Any]:
        """
        Get active blacklist entries.

        Args:
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Only trusted admins can view blacklist
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Недостаточно прав для просмотра чёрного списка"
            }

        # Get active entries
        stmt = select(Blacklist).where(
            Blacklist.is_active == True
        ).order_by(Blacklist.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        entries = list(result.scalars().all())

        if not entries:
            return {
                "success": True,
                "count": 0,
                "entries": [],
                "message": "✅ Чёрный список пуст"
            }

        entries_list = []
        for e in entries:
            action_emoji = {
                BlacklistActionType.PRE_BLOCK: "🚫",
                BlacklistActionType.POST_BLOCK: "⛔",
                BlacklistActionType.TERMINATION: "💀",
            }.get(e.action_type, "❓")

            identifier = None
            if e.telegram_id:
                identifier = f"TG: {e.telegram_id}"
            elif e.username:
                identifier = f"@{e.username}"
            elif e.wallet_address:
                identifier = f"Wallet: {e.wallet_address[:10]}..."

            entries_list.append({
                "id": e.id,
                "identifier": identifier,
                "telegram_id": e.telegram_id,
                "username": e.username,
                "wallet_address": e.wallet_address,
                "action_type": f"{action_emoji} {e.action_type.value if e.action_type else 'unknown'}",
                "reason": e.reason,
                "created": e.created_at.strftime("%d.%m.%Y %H:%M") if e.created_at else None,
            })

        # Count total
        count_stmt = select(func.count(Blacklist.id)).where(Blacklist.is_active == True)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        return {
            "success": True,
            "count": len(entries_list),
            "total": total,
            "entries": entries_list,
            "message": f"🚫 Записей в чёрном списке: {total}"
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

        # Only trusted admins can check blacklist
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Недостаточно прав для проверки чёрного списка"
            }

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
            return {"success": False, "error": "❌ Укажите @username, telegram_id или wallet"}

        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry:
            return {
                "success": True,
                "is_blacklisted": True,
                "entry": {
                    "id": entry.id,
                    "reason": entry.reason,
                    "action_type": entry.action_type.value if entry.action_type else None,
                    "created": entry.created_at.strftime("%d.%m.%Y %H:%M") if entry.created_at else None,
                },
                "message": f"🚫 {identifier} В ЧЁРНОМ СПИСКЕ"
            }

        return {
            "success": True,
            "is_blacklisted": False,
            "message": f"✅ {identifier} НЕ в чёрном списке"
        }

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
            logger.warning(
                f"AI BLACKLIST SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to add to blacklist"
            )
            return {"success": False, "error": "❌ Нет прав на добавление в чёрный список"}

        identifier = identifier.strip()

        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину (минимум 5 символов)"}

        # Validate action type
        action_map = {
            "pre_block": BlacklistActionType.PRE_BLOCK,
            "post_block": BlacklistActionType.POST_BLOCK,
            "termination": BlacklistActionType.TERMINATION,
        }
        if action_type not in action_map:
            return {
                "success": False,
                "error": f"❌ Неверный action_type. Допустимые: {', '.join(action_map.keys())}"
            }

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
            return {"success": False, "error": "❌ Укажите @username, telegram_id или wallet"}

        # Check if already blacklisted
        check_result = await self.check_blacklist(identifier)
        if check_result.get("is_blacklisted"):
            return {"success": False, "error": f"❌ {identifier} уже в чёрном списке"}

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

        logger.warning(
            f"AI BLACKLIST: Admin {self.admin_telegram_id} added {identifier} to blacklist. "
            f"Reason: {reason}, Action: {action_type}"
        )

        return {
            "success": True,
            "identifier": identifier,
            "action_type": action_type,
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"🚫 {identifier} добавлен в чёрный список"
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
            logger.warning(
                f"AI BLACKLIST SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to remove from blacklist"
            )
            return {"success": False, "error": "❌ Нет прав на удаление из чёрного списка"}

        identifier = identifier.strip()

        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину (минимум 5 символов)"}

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
            return {"success": False, "error": "❌ Укажите @username, telegram_id или wallet"}

        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry:
            return {"success": False, "error": f"❌ {identifier} не найден в чёрном списке"}

        # Deactivate
        entry.is_active = False
        await self.session.commit()

        logger.info(
            f"AI BLACKLIST: Admin {self.admin_telegram_id} removed {identifier} from blacklist. "
            f"Reason: {reason}"
        )

        return {
            "success": True,
            "identifier": identifier,
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"✅ {identifier} удалён из чёрного списка"
        }
