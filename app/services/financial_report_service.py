"""
Financial Report Service.

Provides detailed financial analytics and reporting for the admin panel.
Includes DTOs for type-safe data transfer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User


@dataclass
class UserFinancialDTO:
    """Data transfer object for user financial summary list."""
    id: int
    telegram_id: int
    username: str | None
    total_deposited: Decimal
    total_withdrawn: Decimal
    total_earned: Decimal

    @property
    def net_profit(self) -> Decimal:
        """Calculate net profit (Withdrawn - Deposited)."""
        return self.total_withdrawn - self.total_deposited


@dataclass
class UserFinancialDetailDTO:
    """Detailed financial profile for a single user."""
    user: User
    total_deposited: Decimal
    total_withdrawn: Decimal
    total_earned: Decimal
    active_deposits_count: int
    last_deposit_date: datetime | None
    last_withdrawal_date: datetime | None


@dataclass
class DepositDetailDTO:
    """Detailed deposit information."""
    id: int
    created_at: datetime
    level: int
    amount: Decimal
    roi_cap: Decimal
    roi_paid: Decimal
    is_completed: bool
    tx_hash: str | None
    roi_percent: Decimal | None
    status: str


@dataclass
class WithdrawalDetailDTO:
    """Detailed withdrawal information."""
    id: int
    created_at: datetime
    amount: Decimal
    status: str
    tx_hash: str | None
    wallet_address: str


@dataclass
class WalletChangeDTO:
    """Wallet change history entry."""
    changed_at: datetime
    old_wallet: str
    new_wallet: str


@dataclass
class UserDetailedFinancialDTO:
    """Complete detailed financial report for a user."""
    user_id: int
    telegram_id: int
    username: str | None
    current_wallet: str

    # Общая статистика
    total_deposited: Decimal
    total_earned: Decimal
    total_withdrawn: Decimal
    balance: Decimal
    pending_earnings: Decimal

    # Детальные списки
    deposits: list[DepositDetailDTO]
    withdrawals: list[WithdrawalDetailDTO]
    wallet_history: list[WalletChangeDTO]


@dataclass
class PlatformFinancialStatsDTO:
    """Platform-wide financial statistics."""
    total_users: int
    verified_users: int
    users_with_deposits: int

    # Deposit stats
    total_deposits_count: int
    total_deposited_amount: Decimal
    active_deposits_count: int
    active_deposits_amount: Decimal

    # Withdrawal stats
    total_withdrawals_count: int
    total_withdrawn_amount: Decimal
    pending_withdrawals_count: int
    pending_withdrawals_amount: Decimal

    # Earnings stats
    total_roi_paid: Decimal
    total_pending_balance: Decimal


class FinancialReportService:
    """Service for generating financial reports and summaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_platform_financial_stats(self) -> PlatformFinancialStatsDTO:
        """
        Get platform-wide financial statistics.

        Returns comprehensive financial overview including:
        - User counts (total, verified, with deposits)
        - Deposit statistics (count, amounts, active)
        - Withdrawal statistics (count, amounts, pending)
        - ROI earnings statistics
        """
        # User statistics
        total_users_stmt = select(func.count(User.id))
        total_users = (await self.session.execute(total_users_stmt)).scalar() or 0

        verified_users_stmt = select(func.count(User.id)).where(User.is_verified.is_(True))
        verified_users = (await self.session.execute(verified_users_stmt)).scalar() or 0

        # Users with deposits
        users_with_deposits_stmt = select(func.count(func.distinct(Deposit.user_id)))
        users_with_deposits = (await self.session.execute(users_with_deposits_stmt)).scalar() or 0

        # Deposit statistics
        deposit_stats_stmt = select(
            func.count(Deposit.id).label('total_count'),
            func.coalesce(func.sum(Deposit.amount), 0).label('total_amount'),
            func.coalesce(func.sum(Deposit.roi_paid_amount), 0).label('total_roi_paid'),
        )
        deposit_stats = (await self.session.execute(deposit_stats_stmt)).one()

        # Active deposits (not completed)
        active_deposits_stmt = select(
            func.count(Deposit.id).label('count'),
            func.coalesce(func.sum(Deposit.amount), 0).label('amount'),
        ).where(Deposit.is_roi_completed.is_(False))
        active_deposits = (await self.session.execute(active_deposits_stmt)).one()

        # Withdrawal statistics - confirmed
        confirmed_wd_stmt = select(
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('amount'),
        ).where(
            (Transaction.type == TransactionType.WITHDRAWAL) &
            (Transaction.status == TransactionStatus.CONFIRMED)
        )
        confirmed_wd = (await self.session.execute(confirmed_wd_stmt)).one()

        # Pending withdrawals
        pending_wd_stmt = select(
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('amount'),
        ).where(
            (Transaction.type == TransactionType.WITHDRAWAL) &
            (Transaction.status == TransactionStatus.PENDING)
        )
        pending_wd = (await self.session.execute(pending_wd_stmt)).one()

        # Total pending balance across all users
        pending_balance_stmt = select(
            func.coalesce(func.sum(User.balance), 0)
        )
        total_pending_balance = (await self.session.execute(pending_balance_stmt)).scalar() or Decimal("0")

        return PlatformFinancialStatsDTO(
            total_users=total_users,
            verified_users=verified_users,
            users_with_deposits=users_with_deposits,
            total_deposits_count=deposit_stats.total_count or 0,
            total_deposited_amount=Decimal(str(deposit_stats.total_amount)),
            active_deposits_count=active_deposits.count or 0,
            active_deposits_amount=Decimal(str(active_deposits.amount)),
            total_withdrawals_count=confirmed_wd.count or 0,
            total_withdrawn_amount=Decimal(str(confirmed_wd.amount)),
            pending_withdrawals_count=pending_wd.count or 0,
            pending_withdrawals_amount=Decimal(str(pending_wd.amount)),
            total_roi_paid=Decimal(str(deposit_stats.total_roi_paid)),
            total_pending_balance=Decimal(str(total_pending_balance)),
        )

    async def get_users_financial_summary(
        self, page: int = 1, per_page: int = 10
    ) -> tuple[list[UserFinancialDTO], int]:
        """
        Get paginated list of users with financial summaries.

        Returns:
            Tuple of (List of DTOs, Total count of users)
        """
        # Calculate total count first
        count_stmt = select(func.count(User.id))
        total_count = (await self.session.execute(count_stmt)).scalar() or 0

        # Main query with aggregations
        stmt = (
            select(
                User.id,
                User.telegram_id,
                User.username,
                func.coalesce(func.sum(Deposit.amount), 0).label('total_deposited'),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (Transaction.type == TransactionType.WITHDRAWAL) &
                                (Transaction.status == TransactionStatus.CONFIRMED),
                                Transaction.amount
                            ),
                            else_=0
                        )
                    ), 0
                ).label('total_withdrawn'),
                func.coalesce(func.sum(Deposit.roi_paid_amount), 0).label('total_earned')
            )
            .outerjoin(Deposit, User.id == Deposit.user_id)
            .outerjoin(Transaction, User.id == Transaction.user_id)
            .group_by(User.id)
            .order_by(User.id.asc())
            .limit(per_page)
            .offset((page - 1) * per_page)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        dtos = [
            UserFinancialDTO(
                id=row.id,
                telegram_id=row.telegram_id,
                username=row.username,
                total_deposited=Decimal(str(row.total_deposited)),
                total_withdrawn=Decimal(str(row.total_withdrawn)),
                total_earned=Decimal(str(row.total_earned))
            )
            for row in rows
        ]

        return dtos, total_count

    async def get_user_financial_details(self, user_id: int) -> UserFinancialDetailDTO | None:
        """Get detailed financial stats for a specific user."""
        user = await self.session.get(User, user_id)
        if not user:
            return None

        # 1. Total Deposited & Earned & Count
        deposit_stats = await self.session.execute(
            select(
                func.coalesce(func.sum(Deposit.amount), 0),
                func.coalesce(func.sum(Deposit.roi_paid_amount), 0),
                func.count(Deposit.id),
                func.max(Deposit.created_at)
            ).where(Deposit.user_id == user_id)
        )
        total_deposited, total_earned, deposits_count, last_deposit = deposit_stats.one()

        # 2. Total Withdrawn
        withdrawal_stats = await self.session.execute(
            select(
                func.coalesce(func.sum(Transaction.amount), 0),
                func.max(Transaction.created_at)
            ).where(
                (Transaction.user_id == user_id) &
                (Transaction.type == TransactionType.WITHDRAWAL) &
                (Transaction.status == TransactionStatus.CONFIRMED)
            )
        )
        total_withdrawn, last_withdrawal = withdrawal_stats.one()

        return UserFinancialDetailDTO(
            user=user,
            total_deposited=Decimal(str(total_deposited)),
            total_withdrawn=Decimal(str(total_withdrawn)),
            total_earned=Decimal(str(total_earned)),
            active_deposits_count=deposits_count,
            last_deposit_date=last_deposit,
            last_withdrawal_date=last_withdrawal
        )

    async def get_user_withdrawals(
        self, user_id: int, limit: int = 20
    ) -> list[Transaction]:
        """Get recent confirmed withdrawals with transaction hashes."""
        stmt = (
            select(Transaction)
            .where(
                (Transaction.user_id == user_id) &
                (Transaction.type == TransactionType.WITHDRAWAL) &
                (Transaction.status == TransactionStatus.CONFIRMED)
            )
            .order_by(desc(Transaction.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_detailed_financial_report(
        self, user_id: int
    ) -> UserDetailedFinancialDTO | None:
        """
        Get complete detailed financial report for a user.

        Includes:
        - General statistics (deposits, withdrawals, earnings)
        - Full deposit history with ROI details
        - Full withdrawal history with TX hashes
        - Wallet change history

        Args:
            user_id: User ID

        Returns:
            UserDetailedFinancialDTO or None if user not found
        """
        # 1. Get user
        user = await self.session.get(User, user_id)
        if not user:
            return None

        # 2. Get all deposits with details
        deposits_stmt = (
            select(Deposit)
            .where(Deposit.user_id == user_id)
            .options(joinedload(Deposit.deposit_version))
            .order_by(desc(Deposit.created_at))
        )
        deposits_result = await self.session.execute(deposits_stmt)
        deposits = list(deposits_result.scalars().all())

        deposit_dtos = [
            DepositDetailDTO(
                id=d.id,
                created_at=d.created_at,
                level=d.level,
                amount=d.amount,
                roi_cap=d.roi_cap_amount,
                roi_paid=d.roi_paid_amount,
                is_completed=d.is_roi_completed,
                tx_hash=d.tx_hash,
                roi_percent=(
                    d.deposit_version.roi_percent
                    if d.deposit_version
                    else None
                ),
                status=d.status
            )
            for d in deposits
        ]

        # 3. Get all withdrawals with TX hashes
        withdrawals_stmt = (
            select(Transaction)
            .where(
                (Transaction.user_id == user_id) &
                (Transaction.type == TransactionType.WITHDRAWAL)
            )
            .order_by(desc(Transaction.created_at))
        )
        withdrawals_result = await self.session.execute(withdrawals_stmt)
        withdrawals = list(withdrawals_result.scalars().all())

        withdrawal_dtos = [
            WithdrawalDetailDTO(
                id=w.id,
                created_at=w.created_at,
                amount=w.amount,
                status=w.status,
                tx_hash=w.tx_hash,
                wallet_address=user.wallet_address
            )
            for w in withdrawals
        ]

        # 4. Get wallet change history
        from app.models.user_wallet_history import UserWalletHistory

        wallet_history_stmt = (
            select(UserWalletHistory)
            .where(UserWalletHistory.user_id == user_id)
            .order_by(desc(UserWalletHistory.changed_at))
        )
        wallet_history_result = await self.session.execute(wallet_history_stmt)
        wallet_history = list(wallet_history_result.scalars().all())

        wallet_dtos = [
            WalletChangeDTO(
                changed_at=wh.changed_at,
                old_wallet=wh.old_wallet_address,
                new_wallet=wh.new_wallet_address
            )
            for wh in wallet_history
        ]

        # 5. Calculate totals
        total_deposited = sum(d.amount for d in deposits)
        total_earned = sum(d.roi_paid_amount for d in deposits)

        confirmed_withdrawals = [
            w for w in withdrawals
            if w.status == TransactionStatus.CONFIRMED.value
        ]
        total_withdrawn = sum(w.amount for w in confirmed_withdrawals)

        return UserDetailedFinancialDTO(
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            current_wallet=user.wallet_address,
            total_deposited=total_deposited,
            total_earned=total_earned,
            total_withdrawn=total_withdrawn,
            balance=user.balance,
            pending_earnings=user.pending_earnings,
            deposits=deposit_dtos,
            withdrawals=withdrawal_dtos,
            wallet_history=wallet_dtos
        )

    async def export_all_users_csv(self) -> str:
        """
        Export all users to CSV format.

        Returns:
            CSV string with all user data
        """
        import csv
        import io

        # Get all users with their stats
        stmt = (
            select(
                User.id,
                User.telegram_id,
                User.username,
                User.wallet_address,
                User.balance,
                User.total_earned,
                User.is_verified,
                User.is_banned,
                User.created_at,
                User.last_active,
                func.coalesce(func.sum(Deposit.amount), 0).label('total_deposited'),
                func.count(Deposit.id).label('deposits_count'),
            )
            .outerjoin(Deposit, User.id == Deposit.user_id)
            .group_by(User.id)
            .order_by(User.id.asc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'ID', 'Telegram ID', 'Username', 'Wallet', 'Balance',
            'Total Earned', 'Total Deposited', 'Deposits Count',
            'Verified', 'Banned', 'Created At', 'Last Active'
        ])

        # Data rows
        for row in rows:
            writer.writerow([
                row.id,
                row.telegram_id,
                row.username or '',
                row.wallet_address,
                float(row.balance),
                float(row.total_earned),
                float(row.total_deposited),
                row.deposits_count,
                'Yes' if row.is_verified else 'No',
                'Yes' if row.is_banned else 'No',
                row.created_at.strftime('%Y-%m-%d %H:%M') if row.created_at else '',
                row.last_active.strftime('%Y-%m-%d %H:%M') if row.last_active else '',
            ])

        return output.getvalue()
