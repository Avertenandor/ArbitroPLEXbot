"""
Broadcast Service.

Handles mass message sending with rate limiting and background execution.
"""

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import (
    TELEGRAM_BATCH_DELAY,
    TELEGRAM_BATCH_SIZE,
    TELEGRAM_TIMEOUT,
)
from app.services.user_service import UserService
from app.utils.datetime_utils import utc_now


class BroadcastService:
    """Service for handling broadcasts."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self._cancel_event = asyncio.Event()
        self._active_broadcasts: dict[str, dict] = {}

    async def start_broadcast(
        self,
        admin_id: int,
        broadcast_data: dict,
        button_data: dict | None,
        admin_telegram_id: int,  # To notify about completion
    ) -> str:
        """
        Start broadcast in background.

        Returns:
            Broadcast ID
        """
        broadcast_id = f"broadcast_{admin_id}_{int(utc_now().timestamp())}"

        # Start background task with error handler
        task = asyncio.create_task(
            self._broadcast_task(
                admin_id, broadcast_data, button_data, admin_telegram_id, broadcast_id
            )
        )
        task.add_done_callback(self._handle_task_error)

        return broadcast_id

    def _handle_task_error(self, task: asyncio.Task) -> None:
        """Handle errors from background broadcast tasks."""
        try:
            task.result()
        except Exception as e:
            logger.error(f"Background broadcast task failed: {e}", exc_info=True)

    async def cancel_broadcast(self, broadcast_id: str) -> bool:
        """
        Cancel active broadcast.

        Args:
            broadcast_id: Broadcast ID to cancel

        Returns:
            True if broadcast was cancelled, False if not found
        """
        if broadcast_id in self._active_broadcasts:
            self._active_broadcasts[broadcast_id]["cancelled"] = True
            logger.info(f"Broadcast {broadcast_id} marked for cancellation")
            return True
        return False

    async def get_broadcast_progress(self, broadcast_id: str) -> dict | None:
        """
        Get progress of active broadcast.

        Args:
            broadcast_id: Broadcast ID

        Returns:
            Progress dict with keys: progress, total, cancelled, or None if not found
        """
        return self._active_broadcasts.get(broadcast_id)

    async def send_broadcast_with_progress(
        self,
        admin_message: Message,
        broadcast_data: dict,
        button_data: dict | None = None,
    ) -> None:
        """
        Send broadcast with real-time progress updates to admin.

        Args:
            admin_message: Admin's message to reply to
            broadcast_data: Broadcast content data
            button_data: Optional button data
        """
        # Count total users
        user_service = UserService(self.session)
        total_users = await user_service.count_verified_users()

        if total_users == 0:
            await admin_message.answer("Нет пользователей для рассылки.")
            return

        # Send initial progress message
        progress_message = await admin_message.answer(
            f"📤 **Рассылка запущена**\n\n"
            f"Прогресс: 0/{total_users} (0%)\n"
            f"✅ Успешно: 0\n"
            f"🚫 Заблокировали: 0\n"
            f"❌ Ошибки: 0",
            parse_mode="Markdown",
        )

        # Prepare markup
        reply_markup = None
        if button_data:
            builder = InlineKeyboardBuilder()
            builder.button(text=button_data["text"], url=button_data["url"])
            reply_markup = builder.as_markup()

        stats = {"success": 0, "failed": 0, "blocked": 0}

        broadcast_type = broadcast_data["type"]
        text = broadcast_data.get("text")
        file_id = broadcast_data.get("file_id")
        caption = broadcast_data.get("caption")

        # Track for progress updates
        last_update_count = 0
        update_interval = 50  # Update every 50 messages

        try:
            # Send in batches
            async for batch in user_service.get_telegram_ids_batched(TELEGRAM_BATCH_SIZE):
                # Create tasks for the batch
                tasks = [
                    self._send_message_to_user(
                        telegram_id,
                        broadcast_type,
                        text,
                        file_id,
                        caption,
                        reply_markup,
                    )
                    for telegram_id in batch
                ]

                # Send batch in parallel
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        stats["failed"] += 1
                    else:
                        _, status = result
                        stats[status] = stats.get(status, 0) + 1

                # Update progress message periodically
                total_sent = sum(stats.values())
                if total_sent - last_update_count >= update_interval or total_sent == total_users:
                    try:
                        percentage = int((total_sent / total_users) * 100)
                        await progress_message.edit_text(
                            f"📤 **Рассылка в процессе**\n\n"
                            f"Прогресс: {total_sent}/{total_users} ({percentage}%)\n"
                            f"✅ Успешно: {stats['success']}\n"
                            f"🚫 Заблокировали: {stats['blocked']}\n"
                            f"❌ Ошибки: {stats['failed']}",
                            parse_mode="Markdown",
                        )
                        last_update_count = total_sent
                    except Exception as e:
                        logger.warning(f"Failed to update progress message: {e}")

                # Pause between batches
                await asyncio.sleep(TELEGRAM_BATCH_DELAY)

            # Final update
            total_sent = sum(stats.values())
            await progress_message.edit_text(
                f"✅ **Рассылка завершена!**\n\n"
                f"Всего отправлено: {total_sent}/{total_users}\n"
                f"✅ Успешно: {stats['success']}\n"
                f"🚫 Заблокировали бота: {stats['blocked']}\n"
                f"❌ Ошибки: {stats['failed']}",
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Broadcast with progress failed: {e}", exc_info=True)
            try:
                await progress_message.edit_text(
                    f"❌ **Ошибка рассылки**: {e}",
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    async def _send_message_to_user(
        self,
        telegram_id: int,
        broadcast_type: str,
        text: str | None,
        file_id: str | None,
        caption: str | None,
        reply_markup: InlineKeyboardMarkup | None,
    ) -> tuple[int, str]:
        """
        Send message to single user.

        Args:
            telegram_id: User telegram ID
            broadcast_type: Type of broadcast (text, photo, voice, audio)
            text: Text message (for text type)
            file_id: File ID (for media types)
            caption: Caption (for media types)
            reply_markup: Reply markup

        Returns:
            Tuple (telegram_id, status) where status is "success", "blocked", or "failed"
        """
        try:
            if broadcast_type == "text":
                await asyncio.wait_for(
                    self.bot.send_message(
                        telegram_id,
                        text,
                        parse_mode="Markdown",
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )
            elif broadcast_type == "photo":
                await asyncio.wait_for(
                    self.bot.send_photo(
                        telegram_id,
                        file_id,
                        caption=caption,
                        parse_mode="Markdown" if caption else None,
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )
            elif broadcast_type == "voice":
                await asyncio.wait_for(
                    self.bot.send_voice(
                        telegram_id,
                        file_id,
                        caption=caption,
                        parse_mode="Markdown" if caption else None,
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )
            elif broadcast_type == "audio":
                await asyncio.wait_for(
                    self.bot.send_audio(
                        telegram_id,
                        file_id,
                        caption=caption,
                        parse_mode="Markdown" if caption else None,
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )

            return telegram_id, "success"

        except TelegramForbiddenError:
            # User blocked the bot
            return telegram_id, "blocked"
        except TimeoutError:
            logger.warning(f"Timeout sending to {telegram_id}")
            return telegram_id, "failed"
        except Exception as e:
            logger.debug(f"Failed to send to {telegram_id}: {e}")
            return telegram_id, "failed"

    def _prepare_reply_markup(self, button_data: dict | None):
        """Prepare reply markup from button data."""
        if not button_data:
            return None

        builder = InlineKeyboardBuilder()
        builder.button(text=button_data["text"], url=button_data["url"])
        return builder.as_markup()

    async def _process_batch_results(
        self,
        results: list,
        stats: dict,
    ) -> None:
        """Process batch send results and update stats."""
        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
                logger.error(f"Task exception: {result}")
            else:
                _, status = result
                stats[status] = stats.get(status, 0) + 1

    async def _send_broadcast_batch(
        self,
        batch: list[int],
        broadcast_type: str,
        text: str | None,
        file_id: str | None,
        caption: str | None,
        reply_markup,
    ) -> list:
        """Send messages to a batch of users in parallel."""
        tasks = [
            self._send_message_to_user(
                telegram_id,
                broadcast_type,
                text,
                file_id,
                caption,
                reply_markup,
            )
            for telegram_id in batch
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _notify_admin_completion(
        self,
        admin_telegram_id: int,
        broadcast_id: str,
        stats: dict,
        total_sent: int,
        total_users: int,
        is_cancelled: bool,
    ) -> None:
        """Notify admin about broadcast completion."""
        try:
            status_text = "отменена" if is_cancelled else "завершена"
            await asyncio.wait_for(
                self.bot.send_message(
                    admin_telegram_id,
                    f"✅ **Рассылка {broadcast_id} {status_text}!**\n\n"
                    f"✅ Успешно: {stats['success']}\n"
                    f"🚫 Заблокировали бота: {stats['blocked']}\n"
                    f"❌ Ошибки: {stats['failed']}\n"
                    f"👥 Всего отправлено: {total_sent}/{total_users}",
                    parse_mode="Markdown",
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
        except TimeoutError:
            logger.warning(
                f"Timeout notifying admin {admin_telegram_id} about broadcast completion"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    async def _notify_admin_error(
        self,
        admin_telegram_id: int,
        broadcast_id: str,
        error: Exception,
    ) -> None:
        """Notify admin about broadcast error."""
        try:
            await asyncio.wait_for(
                self.bot.send_message(
                    admin_telegram_id,
                    f"❌ **Ошибка рассылки {broadcast_id}**: {error}",
                    parse_mode="Markdown",
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
        except TimeoutError:
            logger.warning(
                f"Timeout notifying admin {admin_telegram_id} about broadcast error"
            )
        except Exception as notify_error:
            logger.error(f"Failed to notify admin about error: {notify_error}")

    async def _broadcast_task(
        self,
        admin_id: int,
        broadcast_data: dict,
        button_data: dict | None,
        admin_telegram_id: int,
        broadcast_id: str,
    ) -> None:
        """Background broadcast task with batched sending."""
        logger.info(f"Starting broadcast {broadcast_id}")

        # Track active broadcast
        self._active_broadcasts[broadcast_id] = {
            "cancelled": False,
            "progress": 0,
            "total": 0,
        }

        try:
            user_service = UserService(self.session)

            # Count total users for progress tracking
            total_users = await user_service.count_verified_users()
            self._active_broadcasts[broadcast_id]["total"] = total_users

            if total_users == 0:
                logger.info(f"No users to broadcast to for {broadcast_id}")
                return

            reply_markup = self._prepare_reply_markup(button_data)
            stats = {"success": 0, "failed": 0, "blocked": 0}

            broadcast_type = broadcast_data["type"]
            text = broadcast_data.get("text")
            file_id = broadcast_data.get("file_id")
            caption = broadcast_data.get("caption")

            # Send in batches with asyncio.gather
            batch_num = 0
            async for batch in user_service.get_telegram_ids_batched(TELEGRAM_BATCH_SIZE):
                # Check for cancellation
                if self._active_broadcasts[broadcast_id].get("cancelled", False):
                    logger.info(f"Broadcast {broadcast_id} cancelled by request")
                    break

                batch_num += 1
                logger.debug(f"Processing batch {batch_num} with {len(batch)} users")

                # Send batch in parallel
                results = await self._send_broadcast_batch(
                    batch, broadcast_type, text, file_id, caption, reply_markup
                )

                # Process results
                await self._process_batch_results(results, stats)

                # Update progress
                total_sent = sum(stats.values())
                self._active_broadcasts[broadcast_id]["progress"] = total_sent

                # Log progress every 100 messages
                if total_sent % 100 == 0:
                    logger.info(
                        f"Broadcast {broadcast_id} progress: {total_sent}/{total_users} "
                        f"(success: {stats['success']}, failed: {stats['failed']}, "
                        f"blocked: {stats['blocked']})"
                    )

                # Pause between batches for rate limiting
                await asyncio.sleep(TELEGRAM_BATCH_DELAY)

            # Notify admin about completion
            total_sent = sum(stats.values())
            is_cancelled = self._active_broadcasts[broadcast_id].get("cancelled", False)
            await self._notify_admin_completion(
                admin_telegram_id, broadcast_id, stats, total_sent, total_users, is_cancelled
            )

        except Exception as e:
            logger.error(f"Broadcast {broadcast_id} failed: {e}", exc_info=True)
            await self._notify_admin_error(admin_telegram_id, broadcast_id, e)

        finally:
            # Clean up active broadcast tracking
            if broadcast_id in self._active_broadcasts:
                del self._active_broadcasts[broadcast_id]
