"""
AI Users Service.

Provides comprehensive user management tools for AI assistant.
Includes: search, profile, balance changes, blocking, deposits.

SECURITY:
- Only accessible from authenticated admin session
- All admin roles can perform user operations (balance changes, etc.)
- All operations are logged for audit purposes
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bonus_credit import BonusCredit
from app.models.deposit import Deposit
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository
from app.utils.formatters import format_user_identifier


# Whitelist of admin telegram IDs who can perform dangerous operations
# (change balance, modify deposits, etc.)
# New admins won't have these permissions
TRUSTED_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Командир/super_admin)
    1691026253,  # @AI_XAN (Саша - Tech Deputy)
    241568583,   # @natder (Наташа)
    6540613027,  # @ded_vtapkax (Влад)
]


class AIUsersService:
    """
    AI-powered user management service.

    Provides full user management capabilities for ARIA.
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
        self.user_repo = UserRepository(session)

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin:
            return None, "❌ Администратор не найден"

        if admin.is_blocked:
            return None, "❌ Администратор заблокирован"

        return admin, None

    def _is_trusted_admin(self) -> bool:
        """Check if current admin is in trusted whitelist."""
        return self.admin_telegram_id in TRUSTED_ADMIN_IDS

    async def _find_user(self, identifier: str) -> tuple[User | None, str | None]:
        """Find user by @username, telegram_id, or wallet address."""
        identifier = identifier.strip()

        # By username
        if identifier.startswith("@"):
            username = identifier[1:]
            user = await self.user_repo.get_by_username(username)
            if user:
                return user, None
            return None, f"❌ Пользователь @{username} не найден"

        # By telegram ID
        if identifier.isdigit():
            telegram_id = int(identifier)
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if user:
                return user, None
            return None, f"❌ Пользователь с ID {telegram_id} не найден"

        # By wallet address
        if identifier.startswith("0x") and len(identifier) == 42:
            stmt = select(User).where(User.wallet_address == identifier)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                return user, None
            return None, f"❌ Пользователь с кошельком {identifier[:10]}... не найден"

        return None, "❌ Укажите @username, telegram_id или адрес кошелька"

    async def get_user_profile(self, user_identifier: str) -> dict[str, Any]:
        """
        Get detailed user profile.

        Args:
            user_identifier: @username, telegram_id, or wallet address

        Returns:
            Detailed user profile
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Get balance data
        balance = getattr(user, 'balance', Decimal("0")) or Decimal("0")
        bonus_balance = getattr(user, 'bonus_balance', Decimal("0")) or Decimal("0")
        bonus_roi = getattr(user, 'bonus_roi_earned', Decimal("0")) or Decimal("0")

        # Calculate total earnings from transactions
        tx_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.DEPOSIT_REWARD.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        tx_result = await self.session.execute(tx_stmt)
        total_earnings = tx_result.scalar() or Decimal("0")

        # Get pending withdrawals
        pending_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.PENDING.value,
        )
        pending_result = await self.session.execute(pending_stmt)
        pending_withdrawals = pending_result.scalar() or Decimal("0")

        # Get completed withdrawals
        completed_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        completed_result = await self.session.execute(completed_stmt)
        total_withdrawals = completed_result.scalar() or Decimal("0")

        # PLEX calculation
        total_investment = user.total_deposited_usdt + bonus_balance
        plex_daily = int(total_investment * 10)
        plex_balance = getattr(user, 'plex_balance', 0) or 0

        profile = {
            "success": True,
            "user": {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": f"@{user.username}" if user.username else None,
                "first_name": user.first_name,
                "phone": getattr(user, 'phone', None),
                "email": getattr(user, 'email', None),
                "wallet": user.masked_wallet if user.wallet_address else None,
                "is_banned": user.is_banned,
                "created_at": user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else None,
            },
            "finances": {
                "balance": float(balance),
                "deposit_usdt": float(user.total_deposited_usdt),
                "bonus_balance": float(bonus_balance),
                "bonus_roi": float(bonus_roi),
                "total_earnings": float(total_earnings),
                "pending_withdrawals": float(pending_withdrawals),
                "total_withdrawals": float(total_withdrawals),
            },
            "plex": {
                "balance": plex_balance,
                "daily_required": plex_daily,
                "days_remaining": int(plex_balance / plex_daily) if plex_daily > 0 else 0,
            },
            "activity": {
                "is_active_depositor": user.is_active_depositor,
                "deposit_tx_count": user.deposit_tx_count,
                "last_deposit_scan": (
                    user.last_deposit_scan_at.strftime("%d.%m.%Y %H:%M")
                    if user.last_deposit_scan_at else None
                ),
            },
        }

        return profile

    async def search_users(
        self,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Search users by username, telegram_id, or wallet.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching users
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        query = query.strip()
        users = []

        # Search by different criteria
        if query.startswith("@"):
            # Username search
            username = query[1:]
            stmt = select(User).where(
                User.username.ilike(f"%{username}%")
            ).limit(limit)
        elif query.isdigit():
            # Telegram ID
            stmt = select(User).where(
                User.telegram_id == int(query)
            ).limit(limit)
        elif query.startswith("0x"):
            # Wallet address
            stmt = select(User).where(
                User.wallet_address.ilike(f"%{query}%")
            ).limit(limit)
        else:
            # General search (name, username)
            stmt = select(User).where(
                (User.username.ilike(f"%{query}%")) |
                (User.first_name.ilike(f"%{query}%"))
            ).limit(limit)

        result = await self.session.execute(stmt)
        users = list(result.scalars().all())

        if not users:
            return {
                "success": True,
                "count": 0,
                "users": [],
                "message": f"❌ Пользователи по запросу '{query}' не найдены"
            }

        users_list = []
        for user in users:
            users_list.append({
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": format_user_identifier(user),
                "deposit": float(user.total_deposited_usdt),
                "bonus": float(getattr(user, 'bonus_balance', 0) or 0),
                "is_banned": user.is_banned,
            })

        return {
            "success": True,
            "count": len(users_list),
            "users": users_list,
            "message": f"✅ Найдено {len(users_list)} пользователей"
        }

    async def change_user_balance(
        self,
        user_identifier: str,
        amount: float,
        reason: str,
        operation: str = "add",
    ) -> dict[str, Any]:
        """
        Change user balance (add or subtract).

        All authenticated admins can use this function.
        Operations are logged for audit purposes.

        Args:
            user_identifier: @username or telegram_id
            amount: Amount to add/subtract
            reason: Reason for change
            operation: "add" or "subtract"
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Разрешаем изменение баланса всем администраторам (любой роли),
        # а не только whitelist. Это согласовано с изменениями в balance.py.
        # Логируем для аудита.
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
            tx_type = TransactionType.ADJUSTMENT
        else:
            if old_balance < Decimal(str(amount)):
                return {
                    "success": False,
                    "error": f"❌ Недостаточно средств. Баланс: {old_balance} USDT"
                }
            user.balance = old_balance - Decimal(str(amount))
            tx_type = TransactionType.ADJUSTMENT

        # Create transaction record
        tx = Transaction(
            user_id=user.id,
            type=tx_type.value,
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

        return {
            "success": True,
            "user": format_user_identifier(user),
            "operation": "➕ Пополнение" if operation == "add" else "➖ Списание",
            "amount": f"{amount} USDT",
            "old_balance": f"{float(old_balance):.2f} USDT",
            "new_balance": f"{float(user.balance):.2f} USDT",
            "reason": reason,
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": "✅ Баланс изменён"
        }

    async def block_user(
        self,
        user_identifier: str,
        reason: str,
    ) -> dict[str, Any]:
        """
        Block a user.

        Args:
            user_identifier: @username or telegram_id
            reason: Block reason
        """
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
        # Note: ban_reason, banned_at, banned_by_admin_id are logged but not stored in User model

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

    async def unblock_user(
        self,
        user_identifier: str,
    ) -> dict[str, Any]:
        """
        Unblock a user.

        Args:
            user_identifier: @username or telegram_id
        """
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

    async def get_user_deposits(
        self,
        user_identifier: str,
    ) -> dict[str, Any]:
        """
        Get user's deposits and bonuses.

        Args:
            user_identifier: @username or telegram_id
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Get blockchain deposits
        deposit_stmt = select(Deposit).where(
            Deposit.user_id == user.id
        ).order_by(Deposit.created_at.desc())
        deposit_result = await self.session.execute(deposit_stmt)
        deposits = list(deposit_result.scalars().all())

        deposits_list = []
        for deposit in deposits:
            deposits_list.append({
                "id": deposit.id,
                "level": deposit.level,
                "amount": float(deposit.amount),
                "status": deposit.status,
                "created": deposit.created_at.strftime("%d.%m.%Y") if deposit.created_at else None,
            })

        # Get bonus credits
        bonus_stmt = select(BonusCredit).where(
            BonusCredit.user_id == user.id
        ).order_by(BonusCredit.created_at.desc())
        bonus_result = await self.session.execute(bonus_stmt)
        bonuses = list(bonus_result.scalars().all())

        bonuses_list = []
        for bonus in bonuses:
            bonuses_list.append({
                "id": bonus.id,
                "amount": float(bonus.amount),
                "roi_paid": float(bonus.roi_paid_amount or 0),
                "roi_cap": float(bonus.roi_cap_amount or 0),
                "is_active": bonus.is_active,
                "reason": bonus.reason,
                "created": bonus.created_at.strftime("%d.%m.%Y") if bonus.created_at else None,
            })

        total_deposits = sum(deposit.amount for deposit in deposits if deposit.status == TransactionStatus.CONFIRMED.value)
        total_bonuses = sum(bonus.amount for bonus in bonuses if bonus.is_active)

        return {
            "success": True,
            "user": format_user_identifier(user),
            "summary": {
                "total_deposits": float(total_deposits),
                "total_bonuses": float(total_bonuses),
                "total_investment": float(total_deposits + total_bonuses),
                "plex_daily": int((total_deposits + total_bonuses) * 10),
            },
            "deposits": deposits_list,
            "bonuses": bonuses_list,
            "message": f"📊 Депозиты пользователя @{user.username or user.telegram_id}"
        }

    async def get_users_stats(self) -> dict[str, Any]:
        """
        Get overall users statistics.

        Returns:
            Users statistics
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total users
        total_stmt = select(func.count(User.id))
        total_result = await self.session.execute(total_stmt)
        total_users = total_result.scalar() or 0

        # Verified users (with wallet)
        verified_stmt = select(func.count(User.id)).where(
            User.wallet_address.isnot(None)
        )
        verified_result = await self.session.execute(verified_stmt)
        verified_users = verified_result.scalar() or 0

        # Active depositors
        active_stmt = select(func.count(User.id)).where(
            User.total_deposited_usdt >= 30
        )
        active_result = await self.session.execute(active_stmt)
        active_depositors = active_result.scalar() or 0

        # Banned users
        banned_stmt = select(func.count(User.id)).where(User.is_banned == True)
        banned_result = await self.session.execute(banned_stmt)
        banned_users = banned_result.scalar() or 0

        # Total deposits
        deposits_stmt = select(func.sum(User.total_deposited_usdt))
        deposits_result = await self.session.execute(deposits_stmt)
        total_deposits = deposits_result.scalar() or Decimal("0")

        # Total bonuses
        bonuses_stmt = select(func.sum(User.bonus_balance)).where(
            User.bonus_balance > 0
        )
        bonuses_result = await self.session.execute(bonuses_stmt)
        total_bonuses = bonuses_result.scalar() or Decimal("0")

        # Users with bonuses
        with_bonus_stmt = select(func.count(User.id)).where(
            User.bonus_balance > 0
        )
        with_bonus_result = await self.session.execute(with_bonus_stmt)
        users_with_bonus = with_bonus_result.scalar() or 0

        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "verified_users": verified_users,
                "active_depositors": active_depositors,
                "banned_users": banned_users,
                "users_with_bonus": users_with_bonus,
            },
            "finances": {
                "total_deposits": float(total_deposits),
                "total_bonuses": float(total_bonuses),
                "total_investment": float(total_deposits + total_bonuses),
            },
            "message": "📊 Статистика пользователей"
        }
