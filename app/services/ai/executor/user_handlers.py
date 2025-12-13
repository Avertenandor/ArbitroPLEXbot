"""
User management handlers for AI tool execution.

Handles user operations, bonuses, wallet, and referrals.
"""

from typing import Any

from app.services.ai.executor.validators import (
    validate_limit,
    validate_positive_decimal,
    validate_positive_int,
    validate_required_string,
    validate_user_identifier,
)


class UserHandlersMixin:
    """Mixin for user management tool handlers."""

    async def _execute_user_tool(self, name: str, inp: dict) -> Any:
        """Execute user management tools."""
        if name == "get_user_profile":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            return await self._users_service.get_user_profile(
                user_identifier=user_id
            )
        elif name == "search_users":
            query = validate_required_string(
                inp.get("query"), "query", max_length=100
            )
            limit = validate_limit(
                inp.get("limit"), default=20, max_limit=50
            )
            return await self._users_service.search_users(
                query=query,
                limit=limit,
            )
        elif name == "change_user_balance":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            amount = validate_positive_decimal(
                inp.get("amount"), "amount"
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            operation = validate_required_string(
                inp.get("operation"), "operation", max_length=20
            )
            if operation not in ("add", "subtract", "set"):
                raise ValueError(
                    "operation must be 'add', 'subtract', or 'set'"
                )
            return await self._users_service.change_user_balance(
                user_identifier=user_id,
                amount=amount,
                reason=reason,
                operation=operation,
            )
        elif name == "block_user":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            return await self._users_service.block_user(
                user_identifier=user_id,
                reason=reason,
            )
        elif name == "unblock_user":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            return await self._users_service.unblock_user(
                user_identifier=user_id
            )
        elif name == "get_user_deposits":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            return await self._users_service.get_user_deposits(
                user_identifier=user_id
            )
        elif name == "get_users_stats":
            return await self._users_service.get_users_stats()
        return {"error": "Unknown user tool"}

    async def _execute_bonus_tool(self, name: str, inp: dict) -> Any:
        """Execute bonus tools."""
        if name == "grant_bonus":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            amount = validate_positive_decimal(
                inp.get("amount"), "amount"
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            return await self._bonus_service.grant_bonus(
                user_identifier=user_id,
                amount=amount,
                reason=reason,
            )
        elif name == "get_user_bonuses":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            return await self._bonus_service.get_user_bonuses(
                user_identifier=user_id,
                active_only=bool(inp.get("active_only", False)),
            )
        elif name == "cancel_bonus":
            bonus_id = validate_positive_int(
                inp.get("bonus_id"), "bonus_id"
            )
            reason = validate_required_string(
                inp.get("reason"), "reason", max_length=500
            )
            return await self._bonus_service.cancel_bonus(
                bonus_id=bonus_id,
                reason=reason,
            )
        return {"error": "Unknown bonus tool"}

    async def _execute_wallet_tool(self, name: str, inp: dict) -> Any:
        """Execute wallet tools."""
        from app.services.ai_wallet_service import AIWalletService

        wallet_service = AIWalletService(self.session, self.admin_data)

        if name == "check_user_wallet":
            return await wallet_service.check_user_wallet(
                user_identifier=inp["user_identifier"]
            )
        elif name == "get_plex_rate":
            return await wallet_service.get_plex_rate()
        elif name == "get_wallet_summary_for_dialog":
            return await wallet_service.get_wallet_summary_for_dialog_end(
                user_telegram_id=inp["user_telegram_id"]
            )
        return {"error": "Unknown wallet tool"}

    async def _execute_referral_tool(self, name: str, inp: dict) -> Any:
        """Execute referral tools."""
        if name == "get_platform_referral_stats":
            return (
                await self._referral_service.get_platform_referral_stats()
            )
        elif name == "get_user_referrals":
            return await self._referral_service.get_user_referrals(
                user_identifier=inp["user_identifier"],
                limit=inp.get("limit", 20),
            )
        elif name == "get_top_referrers":
            return await self._referral_service.get_top_referrers(
                limit=inp.get("limit", 20)
            )
        elif name == "get_top_earners":
            return await self._referral_service.get_top_earners(
                limit=inp.get("limit", 20)
            )
        return {"error": "Unknown referral tool"}
