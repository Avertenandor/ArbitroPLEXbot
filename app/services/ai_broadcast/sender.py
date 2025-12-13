"""Message sending utilities for AI Broadcast Service."""

import asyncio
from typing import Any

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_broadcast.targeting import UserTargeting


class MessageSender:
    """Handles all message sending operations."""

    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        targeting: UserTargeting,
    ):
        self.session = session
        self.bot = bot
        self.targeting = targeting

    async def send_to_user(
        self,
        user_identifier: str | int,
        message_text: str,
        admin_telegram_id: int | None = None,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """
        Send a single message to a user.

        Args:
            user_identifier: @username, telegram_id, or ID:xxx
            message_text: Message text to send
            admin_telegram_id: Admin who initiated the send
            parse_mode: Markdown or HTML

        Returns:
            Result dict with status
        """
        try:
            # Find user
            user = await self.targeting.find_user(user_identifier)
            if not user:
                return {
                    "success": False,
                    "error": (
                        f"Пользователь '{user_identifier}' "
                        f"не найден"
                    ),
                }

            # Send message
            await self.bot.send_message(
                user.telegram_id,
                message_text,
                parse_mode=parse_mode,
            )

            logger.info(
                f"ARIA (admin {admin_telegram_id}) sent message "
                f"to user {user.telegram_id} (@{user.username})"
            )

            return {
                "success": True,
                "user_id": user.telegram_id,
                "username": user.username,
                "message": "Сообщение успешно отправлено",
            }

        except TelegramForbiddenError:
            logger.warning(
                f"User {user_identifier} blocked the bot or "
                f"bot lacks permission"
            )
            return {
                "success": False,
                "error": "Пользователь заблокировал бота",
            }
        except TelegramBadRequest as e:
            logger.error(
                f"Invalid request when sending to {user_identifier}: {e}"
            )
            return {
                "success": False,
                "error": "Ошибка отправки сообщения (неверный запрос)",
            }
        except TelegramRetryAfter as e:
            logger.warning(
                f"Rate limit hit when sending to {user_identifier}, "
                f"retry after {e.retry_after}s"
            )
            return {
                "success": False,
                "error": "Превышен лимит запросов, повторите позже",
            }
        except TelegramAPIError as e:
            logger.error(
                f"Telegram API error when sending to {user_identifier}: {e}"
            )
            return {
                "success": False,
                "error": "Ошибка Telegram API",
            }
        except Exception as e:
            logger.error(
                f"Unexpected error sending message to {user_identifier}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": "Ошибка отправки сообщения",
            }

    async def broadcast_to_group(
        self,
        group: str,
        message_text: str,
        limit: int = 100,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """
        Broadcast message to a group of users.

        Args:
            group: Group type:
                - "active_appeals" - users with open appeals
                - "active_deposits" - users with active deposits
                - "active_24h" - users active in last 24 hours
                - "all" - all users (careful!)
            message_text: Message to send
            limit: Max users to send to
            parse_mode: Markdown or HTML

        Returns:
            Result dict with stats
        """
        try:
            # Get user IDs based on group
            user_ids = await self.targeting.get_users_by_group(
                group, limit
            )

            if not user_ids:
                return {
                    "success": False,
                    "error": (
                        f"Нет пользователей в группе '{group}'"
                    ),
                    "total": 0,
                }

            # Send messages with rate limiting
            success = 0
            failed = 0
            failed_users = []

            for user_id in user_ids:
                try:
                    await self.bot.send_message(
                        user_id,
                        message_text,
                        parse_mode=parse_mode,
                    )
                    success += 1
                    # Rate limit: 20 msg/sec to avoid Telegram limits
                    await asyncio.sleep(0.05)
                except TelegramForbiddenError:
                    failed += 1
                    logger.debug(f"User {user_id} blocked the bot")
                    failed_users.append(
                        {"user_id": user_id, "error": "User blocked bot"}
                    )
                except (TelegramBadRequest, TelegramAPIError) as e:
                    failed += 1
                    logger.warning(
                        f"Failed to send to user {user_id}: {e}"
                    )
                    failed_users.append(
                        {"user_id": user_id, "error": str(e)}
                    )
                except Exception as e:
                    failed += 1
                    logger.error(
                        f"Unexpected error sending to user {user_id}: {e}"
                    )
                    failed_users.append(
                        {"user_id": user_id, "error": str(e)}
                    )

            logger.info(
                f"ARIA broadcast to '{group}': "
                f"{success} sent, {failed} failed"
            )

            return {
                "success": True,
                "group": group,
                "total": len(user_ids),
                "sent": success,
                "failed": failed,
                "failed_details": (
                    failed_users[:5] if failed_users else []
                ),
                "message": (
                    f"Отправлено {success} из {len(user_ids)} "
                    f"сообщений"
                ),
            }

        except TelegramAPIError as e:
            logger.error(f"Telegram API error during broadcast: {e}")
            return {
                "success": False,
                "error": f"Ошибка Telegram API: {str(e)}",
            }
        except Exception as e:
            logger.error(
                f"Unexpected error during broadcast to '{group}': {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def send_invitation(
        self,
        user_identifier: str | int,
        custom_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Send personal invitation to dialog with ARIA.

        Args:
            user_identifier: @username, telegram_id, or ID:xxx
            custom_message: Optional custom message

        Returns:
            Result dict
        """
        user = await self.targeting.find_user(user_identifier)
        if not user:
            return {
                "success": False,
                "error": (
                    f"Пользователь '{user_identifier}' не найден"
                ),
            }

        # Default invitation message
        if custom_message:
            message = custom_message
        else:
            name = user.username or user.first_name or "друг"
            message = (
                f"👋 Привет, {name}!\n\n"
                f"Я **Арья** — AI-помощник ArbitroPLEX.\n\n"
                f"Заметила, что у тебя могут быть вопросы. "
                f"Я здесь, чтобы помочь!\n\n"
                f"Напиши мне прямо сейчас или нажми кнопку "
                f"**💬 Свободный диалог** в меню.\n\n"
                f"С удовольствием отвечу на любые вопросы! 🤗"
            )

        return await self.send_to_user(user.telegram_id, message)

    async def mass_invite(
        self,
        group: str = "active_appeals",
        custom_message: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Send invitations to dialog to a group of users.

        Args:
            group: Target group
            custom_message: Optional custom message template
            limit: Max invitations

        Returns:
            Result dict with stats
        """
        try:
            users = (
                await self.targeting.get_users_details_by_group(
                    group, limit
                )
            )

            if not users:
                return {
                    "success": False,
                    "error": (
                        f"Нет пользователей в группе '{group}'"
                    ),
                }

            success = 0
            failed = 0

            for user_data in users:
                name = (
                    user_data.get("username")
                    or user_data.get("first_name")
                    or "друг"
                )

                if custom_message:
                    message = custom_message.replace("{name}", name)
                else:
                    message = (
                        f"👋 Привет, {name}!\n\n"
                        f"Я **Арья** — AI-помощник "
                        f"ArbitroPLEX.\n\n"
                        f"Хочу убедиться, что у тебя всё хорошо и "
                        f"ответить на любые вопросы.\n\n"
                        f"Напиши мне в **💬 Свободный диалог** — "
                        f"я на связи! 🤗"
                    )

                try:
                    await self.bot.send_message(
                        user_data["telegram_id"],
                        message,
                        parse_mode="Markdown",
                    )
                    success += 1
                    await asyncio.sleep(0.05)
                except TelegramForbiddenError:
                    failed += 1
                    logger.debug(
                        f"User {user_data['telegram_id']} blocked the bot"
                    )
                except (TelegramBadRequest, TelegramAPIError) as e:
                    failed += 1
                    logger.warning(
                        f"Failed to send invitation to "
                        f"{user_data['telegram_id']}: {e}"
                    )
                except Exception as e:
                    failed += 1
                    logger.error(
                        f"Unexpected error sending invitation to "
                        f"{user_data['telegram_id']}: {e}"
                    )

            logger.info(
                f"ARIA mass invite to '{group}': "
                f"{success} sent, {failed} failed"
            )

            return {
                "success": True,
                "group": group,
                "total": len(users),
                "sent": success,
                "failed": failed,
                "message": (
                    f"Приглашения отправлены: "
                    f"{success} из {len(users)}"
                ),
            }

        except TelegramAPIError as e:
            logger.error(f"Telegram API error during mass invite: {e}")
            return {
                "success": False,
                "error": f"Ошибка Telegram API: {str(e)}",
            }
        except Exception as e:
            logger.error(
                f"Unexpected error during mass invite to '{group}': {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def send_feedback_request(
        self,
        admin_identifier: str | int,
        topic: str,
        question: str,
    ) -> dict[str, Any]:
        """
        Send a feedback request to a specific admin.

        Args:
            admin_identifier: @username or telegram_id of admin
            topic: Topic of the feedback request
            question: Specific question to ask

        Returns:
            Result dict with status
        """
        try:
            # Find admin
            admin = await self.targeting.find_admin(
                admin_identifier
            )
            if not admin:
                return {
                    "success": False,
                    "error": (
                        f"Админ '{admin_identifier}' не найден"
                    ),
                }

            # Format feedback request message
            message = (
                f"💬 **Запрос обратной связи от ARIA**\n\n"
                f"📋 **Тема:** {topic}\n\n"
                f"❓ **Вопрос:**\n{question}\n\n"
                f"_Пожалуйста, ответьте на это сообщение или "
                f"нажмите '🤖 AI Помощник' чтобы обсудить "
                f"с ARIA._"
            )

            await self.bot.send_message(
                admin.telegram_id,
                message,
                parse_mode="Markdown",
            )

            logger.info(
                f"ARIA sent feedback request to admin "
                f"{admin.telegram_id} (@{admin.username}) "
                f"on topic: {topic}"
            )

            return {
                "success": True,
                "admin_id": admin.telegram_id,
                "admin_username": admin.username,
                "topic": topic,
                "message": f"Запрос отправлен @{admin.username}",
            }

        except TelegramForbiddenError:
            logger.warning(
                f"Admin {admin_identifier} blocked the bot or "
                f"bot lacks permission"
            )
            return {
                "success": False,
                "error": "Админ заблокировал бота",
            }
        except TelegramBadRequest as e:
            logger.error(
                f"Invalid request when sending feedback to "
                f"{admin_identifier}: {e}"
            )
            return {
                "success": False,
                "error": "Ошибка отправки (неверный запрос)",
            }
        except TelegramAPIError as e:
            logger.error(
                f"Telegram API error sending feedback request to "
                f"{admin_identifier}: {e}"
            )
            return {
                "success": False,
                "error": f"Ошибка Telegram API: {str(e)}",
            }
        except Exception as e:
            logger.error(
                f"Unexpected error sending feedback request to "
                f"{admin_identifier}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": f"Ошибка отправки: {str(e)}",
            }

    async def broadcast_to_admins(
        self,
        message_text: str,
        request_feedback: bool = True,
    ) -> dict[str, Any]:
        """
        Broadcast message to all active admins.

        Args:
            message_text: Message to send
            request_feedback: Whether to add feedback prompt

        Returns:
            Result dict with stats
        """
        from app.models import Admin

        try:
            # Get all active admins
            stmt = select(Admin).where(
                Admin.is_active == True  # noqa: E712
            )
            result = await self.session.execute(stmt)
            admins = result.scalars().all()

            if not admins:
                return {
                    "success": False,
                    "error": "Нет активных админов",
                }

            # Add feedback prompt if requested
            if request_feedback:
                message_text += (
                    "\n\n💬 _Есть идеи или предложения? "
                    "Нажмите '🤖 AI Помощник' чтобы обсудить "
                    "с ARIA._"
                )

            sent_count = 0
            failed_count = 0
            sent_to = []

            for admin in admins:
                try:
                    await self.bot.send_message(
                        admin.telegram_id,
                        message_text,
                        parse_mode="Markdown",
                    )
                    sent_count += 1
                    sent_to.append(f"@{admin.username}")
                    await asyncio.sleep(0.1)  # Rate limiting
                except TelegramForbiddenError:
                    logger.warning(
                        f"Admin {admin.telegram_id} blocked the bot"
                    )
                    failed_count += 1
                except (TelegramBadRequest, TelegramAPIError) as e:
                    logger.warning(
                        f"Failed to send to admin {admin.telegram_id}: {e}"
                    )
                    failed_count += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error sending to admin "
                        f"{admin.telegram_id}: {e}"
                    )
                    failed_count += 1

            logger.info(
                f"ARIA broadcast to {sent_count} admins: "
                f"{', '.join(sent_to)}"
            )

            return {
                "success": True,
                "sent": sent_count,
                "failed": failed_count,
                "admins": sent_to,
                "message": f"Отправлено {sent_count} админам",
            }

        except TelegramAPIError as e:
            logger.error(f"Telegram API error during admin broadcast: {e}")
            return {
                "success": False,
                "error": f"Ошибка Telegram API: {str(e)}",
            }
        except Exception as e:
            logger.error(
                f"Unexpected error during admin broadcast: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": f"Ошибка рассылки: {str(e)}",
            }
