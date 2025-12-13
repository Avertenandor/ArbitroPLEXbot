"""
Admin management and security handlers for AI tool execution.

Handles admin operations, security checks, and verification.
"""

from typing import Any


class AdminHandlersMixin:
    """Mixin for admin management and security tool handlers."""

    async def _execute_admin_mgmt_tool(
        self, name: str, inp: dict
    ) -> Any:
        """Execute admin management tools."""
        from app.services.ai_admin_management_service import (
            AIAdminManagementService,
        )

        admin_mgmt_service = AIAdminManagementService(
            self.session, self.admin_data
        )

        if name == "get_admins_list":
            return await admin_mgmt_service.get_admins_list()
        elif name == "get_admin_details":
            return await admin_mgmt_service.get_admin_details(
                admin_identifier=inp["admin_identifier"]
            )
        elif name == "block_admin":
            return await admin_mgmt_service.block_admin(
                admin_identifier=inp["admin_identifier"],
                reason=inp["reason"],
            )
        elif name == "unblock_admin":
            return await admin_mgmt_service.unblock_admin(
                admin_identifier=inp["admin_identifier"]
            )
        elif name == "change_admin_role":
            return await admin_mgmt_service.change_admin_role(
                admin_identifier=inp["admin_identifier"],
                new_role=inp["new_role"],
            )
        elif name == "get_admin_stats":
            return await admin_mgmt_service.get_admin_stats()
        return {"error": "Unknown admin management tool"}

    async def _execute_security_tool(self, name: str, inp: dict) -> Any:
        """Execute security tools."""
        from app.config.admin_config import VERIFIED_ADMIN_IDS
        from app.services.admin_security_service import (
            AdminSecurityService,
            username_similarity,
        )

        security_service = AdminSecurityService(self.session)

        if name == "check_username_spoofing":
            username = inp["username"].lstrip("@")
            telegram_id = inp.get("telegram_id", 0)

            warnings = []
            for admin_id, admin_info in VERIFIED_ADMIN_IDS.items():
                if admin_id == telegram_id:
                    continue
                sim = username_similarity(
                    username, admin_info["username"]
                )
                if sim >= 0.7:
                    level = (
                        "🚨 КРИТИЧНО" if sim >= 0.9 else "⚠️ ПОДОЗРЕНИЕ"
                    )
                    warnings.append(
                        f"{level}: @{username} похож на админа "
                        f"@{admin_info['username']} ({sim * 100:.0f}%)"
                    )

            if warnings:
                return (
                    f"🔍 **Проверка безопасности: @{username}**\n\n"
                    + "\n".join(warnings)
                    + "\n\n⚠️ Возможная попытка маскировки "
                    + "под админа!"
                )
            return (
                f"✅ @{username} не похож ни на одного "
                "верифицированного админа"
            )

        elif name == "get_verified_admins":
            admins = await security_service.get_all_verified_admins()
            lines = ["🛡️ **Верифицированные администраторы:**\n"]
            for a in admins:
                lines.append(
                    f"• {a['username']} (ID: `{a['telegram_id']}`)\n"
                    f"  Роль: {a['role']}, Имя: {a['name']}"
                )
            return "\n".join(lines)

        elif name == "verify_admin_identity":
            telegram_id = inp["telegram_id"]
            username = inp.get("username")

            verification = await security_service.verify_admin_identity(
                telegram_id, username
            )

            if verification["is_verified_admin"]:
                info = verification["admin_info"]
                result = (
                    f"✅ **ВЕРИФИЦИРОВАН**\n\n"
                    f"Telegram ID: `{info['telegram_id']}`\n"
                    f"Username: @{info['expected_username']}\n"
                    f"Роль: {info['role']}\n"
                    f"Имя: {info['name']}"
                )
                if verification["warnings"]:
                    result += (
                        "\n\n⚠️ Предупреждения:\n"
                        + "\n".join(verification["warnings"])
                    )
                return result
            else:
                if verification["spoofing_detected"]:
                    warning = (
                        verification["warnings"][0]
                        if verification["warnings"]
                        else ""
                    )
                    return (
                        f"🚨 **ВНИМАНИЕ! ПОПЫТКА СПУФИНГА!**\n\n"
                        f"Telegram ID: `{telegram_id}`\n"
                        f"Username: @{username}\n\n"
                        f"Похож на админа: "
                        f"@{verification['similar_to_admin']}\n\n"
                        f"{warning}"
                    )
                return (
                    f"❌ ID `{telegram_id}` НЕ является "
                    "верифицированным админом"
                )

        return {"error": "Unknown security tool"}
