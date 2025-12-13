"""
Deposit management handlers for AI tool execution.

Handles deposit operations and ROI configuration.
"""

from typing import Any

from app.services.ai.executor.validators import (
    validate_limit,
    validate_optional_string,
    validate_positive_decimal,
    validate_positive_int,
    validate_required_string,
    validate_user_identifier,
)


class DepositHandlersMixin:
    """Mixin for deposit management tool handlers."""

    async def _execute_deposits_tool(self, name: str, inp: dict) -> Any:
        """Execute deposits tools."""
        if name == "get_deposit_levels_config":
            return await self._deposits_service.get_deposit_levels_config()
        elif name == "get_user_deposits_list":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            return await self._deposits_service.get_user_deposits(
                user_identifier=user_id
            )
        elif name == "get_pending_deposits":
            limit = validate_limit(
                inp.get("limit"), default=20, max_limit=100
            )
            return await self._deposits_service.get_pending_deposits(
                limit=limit
            )
        elif name == "get_deposit_details":
            deposit_id = validate_positive_int(
                inp.get("deposit_id"), "deposit_id"
            )
            return await self._deposits_service.get_deposit_details(
                deposit_id=deposit_id
            )
        elif name == "get_platform_deposit_stats":
            return (
                await self._deposits_service.get_platform_deposit_stats()
            )
        elif name == "change_max_deposit_level":
            new_max = validate_positive_int(
                inp.get("new_max"), "new_max", max_value=10
            )
            return await self._deposits_service.change_max_deposit_level(
                new_max=new_max
            )
        elif name == "create_manual_deposit":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            level = validate_positive_int(
                inp.get("level"), "level", max_value=10
            )
            amount = validate_positive_decimal(
                inp.get("amount"), "amount"
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            return await self._deposits_service.create_manual_deposit(
                user_identifier=user_id,
                level=level,
                amount=amount,
                reason=reason,
            )
        elif name == "modify_deposit_roi":
            deposit_id = validate_positive_int(
                inp.get("deposit_id"), "deposit_id"
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            # These are optional, but validate if provided
            new_roi_paid = None
            new_roi_cap = None
            if inp.get("new_roi_paid") is not None:
                new_roi_paid = validate_positive_decimal(
                    inp.get("new_roi_paid"), "new_roi_paid"
                )
            if inp.get("new_roi_cap") is not None:
                new_roi_cap = validate_positive_decimal(
                    inp.get("new_roi_cap"), "new_roi_cap"
                )
            return await self._deposits_service.modify_deposit_roi(
                deposit_id=deposit_id,
                new_roi_paid=new_roi_paid,
                new_roi_cap=new_roi_cap,
                reason=reason,
            )
        elif name == "cancel_deposit":
            deposit_id = validate_positive_int(
                inp.get("deposit_id"), "deposit_id"
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            return await self._deposits_service.cancel_deposit(
                deposit_id=deposit_id,
                reason=reason,
            )
        elif name == "confirm_deposit":
            deposit_id = validate_positive_int(
                inp.get("deposit_id"), "deposit_id"
            )
            reason = (
                validate_optional_string(
                    inp.get("reason"), "reason", max_length=500
                )
                or ""
            )
            return await self._deposits_service.confirm_deposit(
                deposit_id=deposit_id,
                reason=reason,
            )
        return {"error": "Unknown deposits tool"}

    async def _execute_roi_tool(self, name: str, inp: dict) -> Any:
        """Execute ROI corridor tools."""
        if name == "get_roi_config":
            return await self._roi_service.get_roi_config(
                level=inp.get("level")
            )
        elif name == "set_roi_corridor":
            return await self._roi_service.set_roi_corridor(
                level=inp["level"],
                mode=inp["mode"],
                roi_min=inp.get("roi_min"),
                roi_max=inp.get("roi_max"),
                roi_fixed=inp.get("roi_fixed"),
                reason=inp.get("reason", ""),
            )
        elif name == "get_corridor_history":
            return await self._roi_service.get_corridor_history(
                level=inp.get("level"),
                limit=inp.get("limit", 20),
            )
        return {"error": "Unknown ROI tool"}
