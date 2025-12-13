"""
Broadcast Sender Module.

Contains message sending functionality for broadcasts,
including progress tracking and different media types.
"""

import asyncio

from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from app.config.constants import (
    TELEGRAM_BATCH_DELAY,
    TELEGRAM_BATCH_SIZE,
    TELEGRAM_TIMEOUT,
    TELEGRAM_VIDEO_TIMEOUT,
)
from app.services.broadcast.core import BroadcastServiceCore
from app.services.user_service import UserService


class BroadcastService(BroadcastServiceCore):
    """Extended broadcast service with message sending capabilities."""

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
        total_users = await user_service.get_verified_users_count()

        if total_users == 0:
            await admin_message.answer(
                "Нет пользователей для рассылки."
            )
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
            builder.button(
                text=button_data["text"], url=button_data["url"]
            )
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
            async for batch in user_service.get_telegram_ids_batched(
                TELEGRAM_BATCH_SIZE
            ):
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
                results = await asyncio.gather(
                    *tasks, return_exceptions=True
                )

                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        stats["failed"] += 1
                    else:
                        _, status = result
                        stats[status] = stats.get(status, 0) + 1

                # Update progress message periodically
                total_sent = sum(stats.values())
                if (
                    total_sent - last_update_count >= update_interval
                    or total_sent == total_users
                ):
                    try:
                        percentage = int(
                            (total_sent / total_users) * 100
                        )
                        await progress_message.edit_text(
                            f"📤 **Рассылка в процессе**\n\n"
                            f"Прогресс: {total_sent}/{total_users} "
                            f"({percentage}%)\n"
                            f"✅ Успешно: {stats['success']}\n"
                            f"🚫 Заблокировали: {stats['blocked']}\n"
                            f"❌ Ошибки: {stats['failed']}",
                            parse_mode="Markdown",
                        )
                        last_update_count = total_sent
                    except Exception as e:
                        logger.warning(
                            f"Failed to update progress message: {e}"
                        )

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
            logger.error(
                f"Broadcast with progress failed: {e}", exc_info=True
            )
            try:
                await progress_message.edit_text(
                    f"❌ **Ошибка рассылки**: {e}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(
                    f"Failed to update progress message with error "
                    f"status: {e}"
                )

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
            broadcast_type: Type of broadcast
                (text, photo, voice, audio, etc.)
            text: Text message (for text type)
            file_id: File ID (for media types)
            caption: Caption (for media types)
            reply_markup: Reply markup

        Returns:
            Tuple (telegram_id, status) where status is
            "success", "blocked", or "failed"
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
            elif broadcast_type == "video":
                await asyncio.wait_for(
                    self.bot.send_video(
                        telegram_id,
                        file_id,
                        caption=caption,
                        parse_mode="Markdown" if caption else None,
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_VIDEO_TIMEOUT,
                )
            elif broadcast_type == "video_note":
                await asyncio.wait_for(
                    self.bot.send_video_note(
                        telegram_id,
                        file_id,
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_VIDEO_TIMEOUT,
                )
            elif broadcast_type == "document":
                await asyncio.wait_for(
                    self.bot.send_document(
                        telegram_id,
                        file_id,
                        caption=caption,
                        parse_mode="Markdown" if caption else None,
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_VIDEO_TIMEOUT,
                )
            elif broadcast_type == "animation":
                await asyncio.wait_for(
                    self.bot.send_animation(
                        telegram_id,
                        file_id,
                        caption=caption,
                        parse_mode="Markdown" if caption else None,
                        reply_markup=reply_markup,
                    ),
                    timeout=TELEGRAM_VIDEO_TIMEOUT,
                )
            elif broadcast_type == "sticker":
                await asyncio.wait_for(
                    self.bot.send_sticker(
                        telegram_id,
                        file_id,
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
        async with self._broadcasts_lock:
            self._active_broadcasts[broadcast_id] = {
                "cancelled": False,
                "progress": 0,
                "total": 0,
            }

        try:
            user_service = UserService(self.session)

            # Count total users for progress tracking
            total_users = await user_service.get_verified_users_count()
            async with self._broadcasts_lock:
                self._active_broadcasts[broadcast_id][
                    "total"
                ] = total_users

            if total_users == 0:
                logger.info(
                    f"No users to broadcast to for {broadcast_id}"
                )
                return

            # Prepare markup
            reply_markup = None
            if button_data:
                builder = InlineKeyboardBuilder()
                builder.button(
                    text=button_data["text"], url=button_data["url"]
                )
                reply_markup = builder.as_markup()

            stats = {"success": 0, "failed": 0, "blocked": 0}

            broadcast_type = broadcast_data["type"]
            text = broadcast_data.get("text")
            file_id = broadcast_data.get("file_id")
            caption = broadcast_data.get("caption")

            # Send in batches with asyncio.gather
            batch_num = 0
            async for batch in user_service.get_telegram_ids_batched(
                TELEGRAM_BATCH_SIZE
            ):
                # Check for cancellation
                async with self._broadcasts_lock:
                    is_cancelled = self._active_broadcasts[
                        broadcast_id
                    ].get("cancelled", False)
                if is_cancelled:
                    logger.info(
                        f"Broadcast {broadcast_id} cancelled by request"
                    )
                    break

                batch_num += 1
                logger.debug(
                    f"Processing batch {batch_num} with "
                    f"{len(batch)} users"
                )

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
                results = await asyncio.gather(
                    *tasks, return_exceptions=True
                )

                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        stats["failed"] += 1
                        logger.error(f"Task exception: {result}")
                    else:
                        _, status = result
                        stats[status] = stats.get(status, 0) + 1

                # Update progress
                total_sent = sum(stats.values())
                async with self._broadcasts_lock:
                    self._active_broadcasts[broadcast_id][
                        "progress"
                    ] = total_sent

                # Log progress every 100 messages
                if total_sent % 100 == 0:
                    logger.info(
                        f"Broadcast {broadcast_id} progress: "
                        f"{total_sent}/{total_users} "
                        f"(success: {stats['success']}, "
                        f"failed: {stats['failed']}, "
                        f"blocked: {stats['blocked']})"
                    )

                # Pause between batches for rate limiting
                await asyncio.sleep(TELEGRAM_BATCH_DELAY)

            # Calculate totals
            total_sent = sum(stats.values())

            # Notify admin about completion
            try:
                async with self._broadcasts_lock:
                    is_cancelled = self._active_broadcasts[
                        broadcast_id
                    ].get("cancelled", False)
                status_text = "отменена" if is_cancelled else "завершена"
                await asyncio.wait_for(
                    self.bot.send_message(
                        admin_telegram_id,
                        f"✅ **Рассылка {broadcast_id} "
                        f"{status_text}!**\n\n"
                        f"✅ Успешно: {stats['success']}\n"
                        f"🚫 Заблокировали бота: {stats['blocked']}\n"
                        f"❌ Ошибки: {stats['failed']}\n"
                        f"👥 Всего отправлено: "
                        f"{total_sent}/{total_users}",
                        parse_mode="Markdown",
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )
            except TimeoutError:
                logger.warning(
                    f"Timeout notifying admin {admin_telegram_id} "
                    f"about broadcast completion"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")

        except asyncio.CancelledError:
            logger.warning(
                f"Broadcast {broadcast_id} cancelled, "
                f"performing cleanup"
            )
            # Mark as cancelled in tracking
            async with self._broadcasts_lock:
                if broadcast_id in self._active_broadcasts:
                    self._active_broadcasts[broadcast_id][
                        "cancelled"
                    ] = True
            raise  # Always re-raise CancelledError
        except Exception as e:
            logger.error(
                f"Broadcast {broadcast_id} failed: {e}", exc_info=True
            )
            try:
                await asyncio.wait_for(
                    self.bot.send_message(
                        admin_telegram_id,
                        f"❌ **Ошибка рассылки {broadcast_id}**: {e}",
                        parse_mode="Markdown",
                    ),
                    timeout=TELEGRAM_TIMEOUT,
                )
            except TimeoutError:
                logger.warning(
                    f"Timeout notifying admin {admin_telegram_id} "
                    f"about broadcast error"
                )
            except Exception as notify_error:
                logger.error(
                    f"Failed to notify admin about error: "
                    f"{notify_error}"
                )
        finally:
            # Clean up active broadcast tracking
            async with self._broadcasts_lock:
                if broadcast_id in self._active_broadcasts:
                    del self._active_broadcasts[broadcast_id]
