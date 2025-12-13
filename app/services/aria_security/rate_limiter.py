"""
Rate Limiter for Tool Execution.

Prevents abuse by limiting operations per admin.
"""

from datetime import UTC, datetime

from loguru import logger


# ========================================================================
# RATE LIMITER FOR TOOL EXECUTION
# ========================================================================

class ToolRateLimiter:
    """
    Rate limiter for AI tool execution.
    Prevents abuse by limiting operations per admin.
    """

    def __init__(self):
        # Structure: {admin_id: {tool_name: [(timestamp, count), ...]}}
        self._usage: dict[int, dict[str, list[tuple[datetime, int]]]] = {}

        # Limits per tool per hour
        self._limits = {
            "grant_bonus": 100,
            "broadcast_to_group": 10,
            "send_message_to_user": 200,
            "mass_invite_to_dialog": 20,
            "approve_withdrawal": 200,
            "reject_withdrawal": 100,
            "add_to_blacklist": 40,
            "emergency_full_stop": 6,
            "emergency_full_resume": 6,
            "block_admin": 10,
            "change_admin_role": 10,
            "default": 400,  # Default for unlisted tools
        }

    def check_limit(
        self,
        admin_id: int,
        tool_name: str
    ) -> tuple[bool, str]:
        """
        Check if admin can execute tool.

        Returns:
            (allowed, message) - allowed=True if within limits
        """
        now = datetime.now(UTC)
        hour_ago = now.replace(minute=0, second=0, microsecond=0)

        # Get limit for this tool
        limit = self._limits.get(tool_name, self._limits["default"])

        # Initialize if needed
        if admin_id not in self._usage:
            self._usage[admin_id] = {}
        if tool_name not in self._usage[admin_id]:
            self._usage[admin_id][tool_name] = []

        # Clean old entries (older than 1 hour)
        self._usage[admin_id][tool_name] = [
            (ts, cnt) for ts, cnt in self._usage[admin_id][tool_name]
            if ts >= hour_ago
        ]

        # Count current usage
        current_usage = sum(
            cnt for _, cnt in self._usage[admin_id][tool_name]
        )

        if current_usage >= limit:
            logger.warning(
                f"RATE LIMIT: Admin {admin_id} exceeded {tool_name} "
                f"limit ({current_usage}/{limit})"
            )
            return (
                False,
                f"❌ Превышен лимит операций '{tool_name}' "
                f"({limit}/час)"
            )

        return True, ""

    def record_usage(
        self,
        admin_id: int,
        tool_name: str,
        count: int = 1
    ) -> None:
        """Record tool usage."""
        now = datetime.now(UTC)

        if admin_id not in self._usage:
            self._usage[admin_id] = {}
        if tool_name not in self._usage[admin_id]:
            self._usage[admin_id][tool_name] = []

        self._usage[admin_id][tool_name].append((now, count))

        logger.debug(
            f"Tool usage recorded: {admin_id} -> {tool_name} x{count}"
        )


# Singleton rate limiter
_rate_limiter: ToolRateLimiter | None = None


def get_rate_limiter() -> ToolRateLimiter:
    """Get or create rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ToolRateLimiter()
    return _rate_limiter
