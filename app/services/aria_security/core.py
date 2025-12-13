"""
ARIA Security Guard - Core Module.

Main security guard that wraps ARIA's processing.
Should be called before ARIA processes any message.
"""

from typing import Any

from loguru import logger

from .validators import SecurityAnalyzer


# ========================================================================
# ARIA SECURITY GUARD
# ========================================================================

class ARIASecurityGuard:
    """
    Security guard that wraps ARIA's processing.
    Should be called before ARIA processes any message.
    """

    def __init__(self):
        self.analyzer = SecurityAnalyzer()
        self.blocked_count = 0
        self.warned_count = 0

    def check_message(
        self,
        text: str,
        telegram_id: int,
        username: str | None,
        is_admin: bool,
    ) -> dict[str, Any]:
        """
        Check message for security threats.

        Args:
            text: Message text
            telegram_id: Sender's telegram ID
            username: Sender's username
            is_admin: Whether sender is admin

        Returns:
            dict with security check result
        """
        result = {
            "allow": True,
            "warnings": [],
            "block_reason": None,
            "log_level": "info",
        }

        # Analyze message content
        analysis = self.analyzer.analyze_message(text)

        if analysis["should_block"]:
            self.blocked_count += 1
            result["allow"] = False
            result["block_reason"] = self.analyzer.format_threat_report()
            result["log_level"] = "error"

            logger.error(
                f"🚨 SECURITY BLOCK: User {telegram_id} "
                f"(@{username}) message blocked. "
                f"Threats: {analysis['threats']}"
            )

        elif analysis["should_warn"]:
            self.warned_count += 1
            result["warnings"].append(
                self.analyzer.format_threat_report()
            )
            result["log_level"] = "warning"

            logger.warning(
                f"⚠️ SECURITY WARNING: User {telegram_id} "
                f"(@{username}) suspicious activity. "
                f"Threats: {analysis['threats']}"
            )

        # Additional check: non-admin trying admin operations
        if not is_admin and self._contains_admin_operations(text):
            result["warnings"].append(
                "⚠️ Обнаружена попытка использования "
                "админ-операций от не-админа"
            )
            logger.warning(
                f"⚠️ NON-ADMIN attempting admin ops: {telegram_id} "
                f"(@{username})"
            )

        return result

    def _contains_admin_operations(self, text: str) -> bool:
        """Check if text contains admin operation keywords."""
        admin_keywords = [
            "заблокируй", "разблокируй", "одобри", "отклони",
            "начисли бонус", "измени баланс",
            "добавь в чёрный",
            "block", "unblock", "approve", "reject",
            "grant bonus", "change balance", "add to blacklist",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in admin_keywords)

    def get_stats(self) -> dict[str, int]:
        """Get security statistics."""
        return {
            "blocked": self.blocked_count,
            "warned": self.warned_count,
        }


# Singleton security guard
_security_guard: ARIASecurityGuard | None = None


def get_security_guard() -> ARIASecurityGuard:
    """Get or create security guard singleton."""
    global _security_guard
    if _security_guard is None:
        _security_guard = ARIASecurityGuard()
    return _security_guard
