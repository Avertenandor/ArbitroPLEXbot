"""
Message and communication handlers for AI tool execution.

Handles messaging, broadcasting, interviews, appeals, and inquiries.
"""

from typing import Any

from app.services.ai.executor.validators import (
    validate_limit,
    validate_optional_string,
    validate_required_string,
    validate_user_identifier,
)


class MessageHandlersMixin:
    """Mixin for message and communication tool handlers."""

    async def _execute_messaging_tool(
        self, name: str, inp: dict
    ) -> Any:
        """Execute messaging/broadcast tools."""
        if name == "send_message_to_user":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            message = validate_required_string(
                inp.get("message_text"), "message_text", max_length=4000
            )
            return await self._broadcast_service.send_message_to_user(
                user_identifier=user_id,
                message_text=message,
            )
        elif name == "broadcast_to_group":
            group = validate_required_string(
                inp.get("group"), "group", max_length=50
            )
            message = validate_required_string(
                inp.get("message_text"), "message_text", max_length=4000
            )
            limit = validate_limit(
                inp.get("limit"), default=100, max_limit=1000
            )
            return await self._broadcast_service.broadcast_to_group(
                group=group,
                message_text=message,
                limit=limit,
            )
        elif name == "get_users_list":
            group = validate_required_string(
                inp.get("group"), "group", max_length=50
            )
            limit = validate_limit(
                inp.get("limit"), default=20, max_limit=100
            )
            return await self._broadcast_service.get_users_list(
                group=group,
                limit=limit,
            )
        elif name == "invite_to_dialog":
            user_id = validate_user_identifier(
                inp.get("user_identifier")
            )
            custom_msg = validate_optional_string(
                inp.get("custom_message"), "custom_message", max_length=500
            )
            return await self._broadcast_service.invite_to_dialog(
                user_identifier=user_id,
                custom_message=custom_msg,
            )
        elif name == "mass_invite_to_dialog":
            group = validate_required_string(
                inp.get("group"), "group", max_length=50
            )
            custom_msg = validate_optional_string(
                inp.get("custom_message"), "custom_message", max_length=500
            )
            limit = validate_limit(
                inp.get("limit"), default=50, max_limit=200
            )
            return await self._broadcast_service.mass_invite_to_dialog(
                group=group,
                custom_message=custom_msg,
                limit=limit,
            )
        elif name == "send_feedback_request":
            admin_id = validate_user_identifier(
                inp.get("admin_identifier")
            )
            topic = validate_required_string(
                inp.get("topic"), "topic", max_length=100
            )
            question = validate_required_string(
                inp.get("question"), "question", max_length=1000
            )
            return await self._broadcast_service.send_feedback_request(
                admin_identifier=admin_id,
                topic=topic,
                question=question,
            )
        elif name == "broadcast_to_admins":
            message = validate_required_string(
                inp.get("message_text"), "message_text", max_length=4000
            )
            request_feedback = inp.get("request_feedback", True)
            return await self._broadcast_service.broadcast_to_admins(
                message_text=message,
                request_feedback=request_feedback,
            )
        return {"error": "Unknown messaging tool"}

    async def _execute_interview_tool(
        self, name: str, inp: dict, resolve_admin_id_func: Any
    ) -> Any:
        """Execute interview tools."""
        from app.services.ai_interview_service import (
            get_interview_service,
            init_interview_service,
        )

        interview_service = get_interview_service(self.bot)
        if not interview_service:
            interview_service = init_interview_service(self.bot)

        if name == "start_interview":
            if not resolve_admin_id_func:
                return {
                    "success": False,
                    "error": "Функция поиска админа недоступна",
                }
            admin_id = await resolve_admin_id_func(
                inp["admin_identifier"], self.session
            )
            if not admin_id:
                return {
                    "success": False,
                    "error": (
                        f"Админ '{inp['admin_identifier']}' не найден"
                    ),
                }
            return await interview_service.start_interview(
                interviewer_id=self.admin_data.get("ID", 0),
                target_admin_id=admin_id["telegram_id"],
                target_admin_username=(
                    admin_id["username"]
                    or str(admin_id["telegram_id"])
                ),
                topic=inp["topic"],
                questions=inp["questions"],
            )
        elif name == "get_interview_status":
            if not resolve_admin_id_func:
                return {
                    "success": False,
                    "error": "Функция поиска админа недоступна",
                }
            admin_id = await resolve_admin_id_func(
                inp["admin_identifier"], self.session
            )
            if not admin_id:
                return {"success": False, "error": "Админ не найден"}
            status = interview_service.get_interview_status(
                admin_id["telegram_id"]
            )
            return (
                status
                if status
                else {"success": False, "error": "Нет активного интервью"}
            )
        elif name == "cancel_interview":
            if not resolve_admin_id_func:
                return {
                    "success": False,
                    "error": "Функция поиска админа недоступна",
                }
            admin_id = await resolve_admin_id_func(
                inp["admin_identifier"], self.session
            )
            if not admin_id:
                return {"success": False, "error": "Админ не найден"}
            return await interview_service.cancel_interview(
                admin_id["telegram_id"]
            )
        elif name == "get_knowledge_by_user":
            from app.services.knowledge_base import get_knowledge_base

            kb = get_knowledge_base()
            username = inp.get("username", "").replace("@", "")
            entries = kb.get_entries_by_user(username)
            if not entries:
                return {
                    "success": True,
                    "count": 0,
                    "message": f"Записей от @{username} не найдено",
                    "entries": [],
                }
            # Format entries for display
            formatted = []
            for e in entries:
                formatted.append(
                    {
                        "id": e.get("id"),
                        "question": e.get("question"),
                        "answer": e.get("answer"),
                        "category": e.get("category"),
                        "added_at": e.get("added_at"),
                        "verified": e.get("verified_by_boss", False),
                    }
                )
            return {
                "success": True,
                "count": len(entries),
                "message": f"Найдено {len(entries)} записей от @{username}",
                "entries": formatted,
            }
        return {"error": "Unknown interview tool"}

    async def _execute_appeals_tool(self, name: str, inp: dict) -> Any:
        """Execute appeals tools."""
        if name == "get_appeals_list":
            return await self._appeals_service.get_appeals_list(
                status=inp.get("status"),
                limit=inp.get("limit", 20),
            )
        elif name == "get_appeal_details":
            return await self._appeals_service.get_appeal_details(
                appeal_id=inp["appeal_id"]
            )
        elif name == "take_appeal":
            return await self._appeals_service.take_appeal(
                appeal_id=inp["appeal_id"]
            )
        elif name == "resolve_appeal":
            return await self._appeals_service.resolve_appeal(
                appeal_id=inp["appeal_id"],
                decision=inp["decision"],
                notes=inp.get("notes"),
            )
        elif name == "reply_to_appeal":
            return await self._appeals_service.reply_to_appeal(
                appeal_id=inp["appeal_id"],
                message=inp["message"],
                bot=self.bot,
            )
        return {"error": "Unknown appeals tool"}

    async def _execute_inquiries_tool(self, name: str, inp: dict) -> Any:
        """Execute inquiries tools."""
        if name == "get_inquiries_list":
            return await self._inquiries_service.get_inquiries_list(
                status=inp.get("status"),
                limit=inp.get("limit", 20),
            )
        elif name == "get_inquiry_details":
            return await self._inquiries_service.get_inquiry_details(
                inquiry_id=inp["inquiry_id"]
            )
        elif name == "take_inquiry":
            return await self._inquiries_service.take_inquiry(
                inquiry_id=inp["inquiry_id"]
            )
        elif name == "reply_to_inquiry":
            return await self._inquiries_service.reply_to_inquiry(
                inquiry_id=inp["inquiry_id"],
                message=inp["message"],
                bot=self.bot,
            )
        elif name == "close_inquiry":
            return await self._inquiries_service.close_inquiry(
                inquiry_id=inp["inquiry_id"],
                reason=inp.get("reason"),
            )
        return {"error": "Unknown inquiries tool"}
