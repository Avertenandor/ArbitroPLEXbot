"""
Withdrawal management handlers for AI tool execution.

Handles withdrawal operations and approvals.
"""

from typing import Any

from app.services.ai.executor.validators import (
    validate_limit,
    validate_optional_string,
    validate_positive_int,
    validate_required_string,
)


class WithdrawalHandlersMixin:
    """Mixin for withdrawal management tool handlers."""

    async def _execute_withdrawals_tool(
        self, name: str, inp: dict
    ) -> Any:
        """Execute withdrawals tools."""
        if name == "get_pending_withdrawals":
            limit = validate_limit(
                inp.get("limit"), default=20, max_limit=100
            )
            return await self._withdrawals_service.get_pending_withdrawals(
                limit=limit
            )
        elif name == "get_withdrawal_details":
            withdrawal_id = validate_positive_int(
                inp.get("withdrawal_id"), "withdrawal_id"
            )
            return await self._withdrawals_service.get_withdrawal_details(
                withdrawal_id=withdrawal_id
            )
        elif name == "approve_withdrawal":
            withdrawal_id = validate_positive_int(
                inp.get("withdrawal_id"), "withdrawal_id"
            )
            tx_hash = validate_optional_string(
                inp.get("tx_hash"), "tx_hash", max_length=100
            )
            return await self._withdrawals_service.approve_withdrawal(
                withdrawal_id=withdrawal_id,
                tx_hash=tx_hash,
            )
        elif name == "reject_withdrawal":
            withdrawal_id = validate_positive_int(
                inp.get("withdrawal_id"), "withdrawal_id"
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            return await self._withdrawals_service.reject_withdrawal(
                withdrawal_id=withdrawal_id,
                reason=reason,
            )
        elif name == "get_withdrawals_statistics":
            return await self._withdrawals_service.get_statistics()
        return {"error": "Unknown withdrawals tool"}
