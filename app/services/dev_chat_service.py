"""
Developer Chat Service - Direct communication channel between Copilot/Claude and admins.

This service allows the development AI (Copilot) to communicate directly with admins
through the Telegram bot, bypassing ARIA. Used for:
- Collecting requirements and feedback
- Technical discussions
- Quick iterations on features
- Bug reports and fixes

The workflow:
1. Copilot writes messages to Redis queue
2. Bot periodically checks queue and sends messages to admins
3. Admin responses are logged and can be fetched by Copilot
"""

import json
from datetime import datetime
from typing import Any

from aiogram import Bot
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin


# Redis keys
DEV_CHAT_OUTBOX = "dev_chat:outbox"  # Messages from Copilot to admins
DEV_CHAT_INBOX = "dev_chat:inbox"  # Responses from admins
DEV_CHAT_LOG = "dev_chat:log"  # Full conversation log


class DevChatService:
    """
    Service for direct Copilot-Admin communication.

    This creates a fast feedback loop for development:
    - Copilot can ask questions to specific admins
    - Admins respond through bot
    - Responses are stored for Copilot to read
    """

    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        redis: Redis,
    ):
        self.session = session
        self.bot = bot
        self.redis = redis

    async def send_dev_message(
        self,
        admin_identifier: str | int,
        message: str,
        sender: str = "Copilot",
        priority: str = "normal",
    ) -> dict[str, Any]:
        """
        Queue a message from Copilot to an admin.

        Args:
            admin_identifier: @username or telegram_id
            message: Message text
            sender: Sender name (Copilot, Claude, etc.)
            priority: normal, high, urgent

        Returns:
            Result dict
        """
        try:
            admin = await self._find_admin(admin_identifier)
            if not admin:
                return {"success": False, "error": f"Admin {admin_identifier} not found"}

            # Create message payload
            msg_data = {
                "id": f"dev_{datetime.utcnow().timestamp()}",
                "to_admin_id": admin.telegram_id,
                "to_username": admin.username,
                "message": message,
                "sender": sender,
                "priority": priority,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending",
            }

            # Add to outbox queue
            await self.redis.lpush(DEV_CHAT_OUTBOX, json.dumps(msg_data))

            # Also add to log
            await self.redis.lpush(
                DEV_CHAT_LOG,
                json.dumps(
                    {
                        **msg_data,
                        "direction": "outgoing",
                    }
                ),
            )

            logger.info(f"DevChat: Queued message to @{admin.username} from {sender}")

            return {
                "success": True,
                "message_id": msg_data["id"],
                "to": f"@{admin.username}",
            }

        except Exception as e:
            logger.error(f"DevChat send error: {e}")
            return {"success": False, "error": str(e)}

    async def process_outbox(self) -> int:
        """
        Process pending messages in outbox and send them.
        Called periodically by bot or manually.

        Returns:
            Number of messages sent
        """
        sent_count = 0

        while True:
            # Get next message from queue
            msg_json = await self.redis.rpop(DEV_CHAT_OUTBOX)
            if not msg_json:
                break

            try:
                msg_data = json.loads(msg_json)

                # Format message
                priority_emoji = {
                    "urgent": "🚨",
                    "high": "⚡",
                    "normal": "💬",
                }.get(msg_data.get("priority", "normal"), "💬")

                formatted_msg = (
                    f"{priority_emoji} **Сообщение от разработчика ({msg_data.get('sender', 'Dev')})**\n\n"
                    f"{msg_data['message']}\n\n"
                    f"_Ответьте на это сообщение — ваш ответ будет передан разработчику._\n"
                    f"_Или используйте команду: /dev\\_reply <ваш ответ>_"
                )

                # Send to admin
                await self.bot.send_message(
                    msg_data["to_admin_id"],
                    formatted_msg,
                    parse_mode="Markdown",
                )

                # Update status
                msg_data["status"] = "sent"
                msg_data["sent_at"] = datetime.utcnow().isoformat()

                sent_count += 1
                logger.info(f"DevChat: Sent message to {msg_data['to_admin_id']}")

            except Exception as e:
                logger.error(f"DevChat: Failed to send message: {e}")
                # Re-queue failed message
                await self.redis.rpush(DEV_CHAT_OUTBOX, msg_json)
                break

        return sent_count

    async def record_admin_response(
        self,
        admin_id: int,
        admin_username: str,
        response_text: str,
    ) -> dict[str, Any]:
        """
        Record a response from admin to the inbox.

        Args:
            admin_id: Admin's telegram_id
            admin_username: Admin's username
            response_text: Their response

        Returns:
            Result dict
        """
        try:
            response_data = {
                "id": f"resp_{datetime.utcnow().timestamp()}",
                "from_admin_id": admin_id,
                "from_username": admin_username,
                "message": response_text,
                "received_at": datetime.utcnow().isoformat(),
                "read": False,
            }

            # Add to inbox
            await self.redis.lpush(DEV_CHAT_INBOX, json.dumps(response_data))

            # Add to log
            await self.redis.lpush(
                DEV_CHAT_LOG,
                json.dumps(
                    {
                        **response_data,
                        "direction": "incoming",
                    }
                ),
            )

            logger.info(f"DevChat: Recorded response from @{admin_username}")

            return {"success": True, "response_id": response_data["id"]}

        except Exception as e:
            logger.error(f"DevChat: Failed to record response: {e}")
            return {"success": False, "error": str(e)}

    async def get_unread_responses(self, limit: int = 50) -> list[dict]:
        """
        Get unread responses from admins.

        Args:
            limit: Max responses to return

        Returns:
            List of response dicts
        """
        try:
            responses = []
            inbox_items = await self.redis.lrange(DEV_CHAT_INBOX, 0, limit - 1)

            for item in inbox_items:
                data = json.loads(item)
                if not data.get("read", False):
                    responses.append(data)

            return responses

        except Exception as e:
            logger.error(f"DevChat: Failed to get responses: {e}")
            return []

    async def get_conversation_log(self, limit: int = 100) -> list[dict]:
        """
        Get full conversation log.

        Args:
            limit: Max entries to return

        Returns:
            List of log entries (newest first)
        """
        try:
            log_items = await self.redis.lrange(DEV_CHAT_LOG, 0, limit - 1)
            return [json.loads(item) for item in log_items]
        except Exception as e:
            logger.error(f"DevChat: Failed to get log: {e}")
            return []

    async def broadcast_to_all_admins(
        self,
        message: str,
        sender: str = "Copilot",
    ) -> dict[str, Any]:
        """
        Send message to all active admins.

        Args:
            message: Message text
            sender: Sender name

        Returns:
            Result with count of queued messages
        """
        try:
            stmt = select(Admin).where(Admin.is_active == True)  # noqa: E712
            result = await self.session.execute(stmt)
            admins = result.scalars().all()

            queued = 0
            for admin in admins:
                result = await self.send_dev_message(
                    admin_identifier=admin.telegram_id,
                    message=message,
                    sender=sender,
                )
                if result.get("success"):
                    queued += 1

            return {
                "success": True,
                "queued": queued,
                "total_admins": len(admins),
            }

        except Exception as e:
            logger.error(f"DevChat broadcast error: {e}")
            return {"success": False, "error": str(e)}

    async def _find_admin(self, identifier: str | int) -> Admin | None:
        """Find admin by username or telegram_id."""
        try:
            if isinstance(identifier, int):
                telegram_id = identifier
            elif str(identifier).startswith("@"):
                username = str(identifier)[1:]
                stmt = select(Admin).where(Admin.username == username)
                result = await self.session.execute(stmt)
                return result.scalar_one_or_none()
            elif str(identifier).isdigit():
                telegram_id = int(identifier)
            else:
                stmt = select(Admin).where(Admin.username == str(identifier))
                result = await self.session.execute(stmt)
                return result.scalar_one_or_none()

            stmt = select(Admin).where(Admin.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"DevChat: Error finding admin: {e}")
            return None


# Global instance for easy access
_dev_chat_service: DevChatService | None = None


def get_dev_chat_service() -> DevChatService | None:
    """Get the global DevChatService instance."""
    return _dev_chat_service


def init_dev_chat_service(session: AsyncSession, bot: Bot, redis: Redis) -> DevChatService:
    """Initialize the global DevChatService instance."""
    global _dev_chat_service
    _dev_chat_service = DevChatService(session, bot, redis)
    return _dev_chat_service
