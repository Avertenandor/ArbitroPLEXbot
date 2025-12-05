"""
Admin Security Monitor - Action Checks Module.

Module: action_checks.py
Contains specific action checking logic for different admin operations.
Detects mass operations, unusual timing, and large approvals.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from app.config.settings import settings
from app.models.admin_action import AdminAction


class ActionChecker:
    """Specific action checking logic."""

    def __init__(self, action_repo, session) -> None:
        """Initialize action checker."""
        self.action_repo = action_repo
        self.session = session

    async def check_mass_user_actions(
        self, admin_id: int, action_type: str
    ) -> dict[str, Any]:
        """Check for mass bans/terminations."""
        threshold = (
            settings.admin_max_bans_per_hour
            if action_type == "USER_BLOCKED"
            else settings.admin_max_terminations_per_hour
        )

        # Count actions in last hour
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        count = await self.action_repo.count_by_admin_and_type(
            admin_id=admin_id,
            action_type=action_type,
            since=one_hour_ago,
        )

        if count >= threshold:
            severity = "critical" if count >= threshold * 2 else "high"
            return {
                "suspicious": True,
                "reason": (
                    f"Mass {action_type.lower()}: {count} actions in last hour "
                    f"(threshold: {threshold})"
                ),
                "should_block": True,
                "severity": severity,
            }

        return {
            "suspicious": False,
            "reason": None,
            "should_block": False,
            "severity": None,
        }

    async def check_withdrawal_approval(
        self, admin_id: int, details: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        Check for mass or large withdrawal approvals.

        R18-4: Also checks daily limits (count and total amount).
        """
        # Count approvals in last hour
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        count = await self.action_repo.count_by_admin_and_type(
            admin_id=admin_id,
            action_type="WITHDRAWAL_APPROVED",
            since=one_hour_ago,
        )

        # Check for mass approvals (hourly)
        if count >= settings.admin_max_withdrawal_approvals_per_hour:
            return {
                "suspicious": True,
                "reason": (
                    f"Mass withdrawal approvals: {count} in last hour "
                    f"(threshold: {settings.admin_max_withdrawal_approvals_per_hour})"
                ),
                "should_block": True,
                "severity": "critical",
            }

        # R18-4: Check daily limits
        one_day_ago = datetime.now(UTC) - timedelta(days=1)
        daily_count = await self.action_repo.count_by_admin_and_type(
            admin_id=admin_id,
            action_type="WITHDRAWAL_APPROVED",
            since=one_day_ago,
        )

        if daily_count >= settings.admin_max_withdrawals_per_day:
            return {
                "suspicious": True,
                "reason": (
                    f"Daily withdrawal limit exceeded: {daily_count} withdrawals "
                    f"(threshold: {settings.admin_max_withdrawals_per_day}/day)"
                ),
                "should_block": True,
                "severity": "critical",
            }

        # R18-4: Check daily total amount limit
        daily_total = await self.action_repo.sum_withdrawal_amounts_by_admin(
            admin_id, one_day_ago
        )

        if daily_total >= settings.admin_max_withdrawal_amount_per_day:
            return {
                "suspicious": True,
                "reason": (
                    f"Daily withdrawal amount limit exceeded: "
                    f"${daily_total:.2f} USDT "
                    f"(threshold: ${settings.admin_max_withdrawal_amount_per_day}/day)"
                ),
                "should_block": True,
                "severity": "critical",
            }

        # Check for large withdrawal (>$1000)
        if details:
            amount = details.get("amount")
            if amount:
                try:
                    amount_decimal = Decimal(str(amount))
                    if amount_decimal >= settings.admin_large_withdrawal_threshold:
                        # Count large withdrawals in last hour
                        large_count = await self._count_large_withdrawals(
                            admin_id, one_hour_ago
                        )
                        max_large = settings.admin_max_large_withdrawal_approvals_per_hour
                        if large_count >= max_large:
                            return {
                                "suspicious": True,
                                "reason": (
                                    f"Mass large withdrawal approvals: "
                                    f"{large_count} >${settings.admin_large_withdrawal_threshold} "
                                    f"in last hour"
                                ),
                                "should_block": True,
                                "severity": "critical",
                            }
                except (ValueError, TypeError):
                    pass

        return {
            "suspicious": False,
            "reason": None,
            "should_block": False,
            "severity": None,
        }

    async def check_balance_adjustment_limits(self, admin_id: int) -> dict[str, Any]:
        """Check balance adjustment limits (R18-4)."""
        # This is a placeholder - actual implementation would check specific limits
        # For now, return no suspicious activity
        return {
            "suspicious": False,
            "reason": None,
            "should_block": False,
            "severity": None,
        }

    async def check_admin_management(
        self, admin_id: int, action_type: str
    ) -> dict[str, Any]:
        """Check for admin creation/deletion spikes."""
        threshold = (
            settings.admin_max_creations_per_day
            if action_type == "ADMIN_CREATED"
            else settings.admin_max_deletions_per_day
        )

        # Count actions in last 24 hours
        one_day_ago = datetime.now(UTC) - timedelta(days=1)
        count = await self.action_repo.count_by_admin_and_type(
            admin_id=admin_id,
            action_type=action_type,
            since=one_day_ago,
        )

        if count >= threshold:
            return {
                "suspicious": True,
                "reason": (
                    f"Mass {action_type.lower()}: {count} in last 24 hours "
                    f"(threshold: {threshold})"
                ),
                "should_block": True,
                "severity": "critical",
            }

        return {
            "suspicious": False,
            "reason": None,
            "should_block": False,
            "severity": None,
        }

    async def check_critical_config_changes(
        self, admin_id: int, action_type: str
    ) -> dict[str, Any]:
        """Check for critical configuration changes."""
        # Any critical config change is suspicious if done outside business hours
        # (3am-6am UTC is suspicious)
        now = datetime.now(UTC)
        hour = now.hour

        if 3 <= hour < 6:
            return {
                "suspicious": True,
                "reason": (
                    f"Critical config change ({action_type}) "
                    f"at unusual time ({hour}:00 UTC)"
                ),
                "should_block": False,  # Don't auto-block, but alert
                "severity": "high",
            }

        return {
            "suspicious": False,
            "reason": None,
            "should_block": False,
            "severity": None,
        }

    async def _count_large_withdrawals(
        self, admin_id: int, since: datetime
    ) -> int:
        """Count large withdrawal approvals by admin since timestamp."""
        stmt = (
            select(func.count(AdminAction.id))
            .where(AdminAction.admin_id == admin_id)
            .where(AdminAction.action_type == "WITHDRAWAL_APPROVED")
            .where(AdminAction.created_at >= since)
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        # Filter by amount in details (if available)
        # This is simplified - in production, would need to parse JSON details
        return count
