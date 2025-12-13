"""
AI Users Service - User operations (search, balance, blocking).
"""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.ai.commons import find_user_by_identifier, verify_admin
from app.utils.formatters import format_user_identifier


class OperationsMixin:
    """Mixin for user operations (search, balance, blocking)."""

    session: AsyncSession
    admin_telegram_id: int | None
    admin_username: str | None
    user_repo: UserRepository

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        return await verify_admin(self.session, self.admin_telegram_id)

    async def _find_user(self, identifier: str) -> tuple[User | None, str | None]:
        return await find_user_by_identifier(self.session, identifier, self.user_repo)

    async def search_users(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Search users by username, telegram_id, or wallet."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        query = query.strip()

        if query.startswith("@"):
            stmt = select(User).where(User.username.ilike(f"%{query[1:]}%")).limit(limit)
        elif query.isdigit():
            stmt = select(User).where(User.telegram_id == int(query)).limit(limit)
        elif query.startswith("0x"):
            stmt = select(User).where(User.wallet_address.ilike(f"%{query}%")).limit(limit)
        else:
            stmt = select(User).where(User.username.ilike(f"%{query}%")).limit(limit)

        result = await self.session.execute(stmt)
        users = list(result.scalars().all())

        if not users:
            return {
                "success": True,
                "count": 0,
                "users": [],
                "message": f"❌ Пользователи по запросу '{query}' не найдены"
            }

        users_list = [{
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": format_user_identifier(u),
            "deposit": float(u.total_deposited_usdt),
            "bonus": float(getattr(u, 'bonus_balance', 0) or 0),
            "is_banned": u.is_banned,
        } for u in users]

        return {
            "success": True,
            "count": len(users_list),
            "users": users_list,
            "message": f"✅ Найдено {len(users_list)} пользователей"
        }

    async def change_user_balance(
        self, user_identifier: str, amount: float, reason: str, operation: str = "add"
    ) -> dict[str, Any]:
        """Change user balance (add/subtract/set)."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        logger.info(
            f"AI USERS: Admin {self.admin_telegram_id} ({self.admin_username}) "
            f"initiating balance change"
        )

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        if amount <= 0:
            return {"success": False, "error": "❌ Сумма должна быть положительной"}
        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину (минимум 5 символов)"}

        old_balance = user.balance or Decimal("0")

        if operation == "add":
            user.balance = old_balance + Decimal(str(amount))
        elif operation == "subtract":
            if old_balance < Decimal(str(amount)):
                return {
                    "success": False,
                    "error": f"❌ Недостаточно средств. Баланс: {old_balance} USDT"
                }
            user.balance = old_balance - Decimal(str(amount))
        elif operation == "set":
            user.balance = Decimal(str(amount))
        else:
            return {
                "success": False,
                "error": "❌ Неверная операция. Используйте add/subtract/set"
            }

        tx = Transaction(
            user_id=user.id,
            type=TransactionType.ADJUSTMENT.value,
            amount=Decimal(str(amount)),
            status=TransactionStatus.CONFIRMED.value,
            description=f"[АРЬЯ] {reason}",
            balance_before=old_balance,
            balance_after=user.balance,
            created_at=datetime.now(UTC),
        )
        self.session.add(tx)
        await self.session.commit()

        logger.info(
            f"AI USERS: Admin {admin.telegram_id} changed balance for "
            f"user {user.telegram_id}: {operation} {amount} USDT. Reason: {reason}"
        )

        operation_names = {
            "add": "➕ Пополнение",
            "subtract": "➖ Списание",
            "set": "🎯 Установка"
        }
        return {
            "success": True,
            "user": format_user_identifier(user),
            "operation": operation_names.get(operation, operation),
            "amount": f"{amount} USDT",
            "old_balance": f"{float(old_balance):.2f} USDT",
            "new_balance": f"{float(user.balance):.2f} USDT",
            "reason": reason,
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": "✅ Баланс изменён"
        }

    async def block_user(self, user_identifier: str, reason: str) -> dict[str, Any]:
        """Block a user."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        if user.is_banned:
            return {"success": False, "error": "❌ Пользователь уже заблокирован"}
        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину блокировки"}

        user.is_banned = True
        await self.session.commit()

        logger.info(
            f"AI USERS: Admin {admin.telegram_id} blocked user "
            f"{user.telegram_id} (@{user.username}): {reason}"
        )

        return {
            "success": True,
            "user": format_user_identifier(user),
            "reason": reason,
            "admin": f"@{admin.username}",
            "message": "🚫 Пользователь заблокирован"
        }

    async def unblock_user(self, user_identifier: str) -> dict[str, Any]:
        """Unblock a user."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        if not user.is_banned:
            return {"success": False, "error": "❌ Пользователь не заблокирован"}

        user.is_banned = False
        await self.session.commit()

        logger.info(
            f"AI USERS: Admin {admin.telegram_id} unblocked user "
            f"{user.telegram_id} (@{user.username})"
        )

        return {
            "success": True,
            "user": format_user_identifier(user),
            "admin": f"@{admin.username}",
            "message": "✅ Пользователь разблокирован"
        }
