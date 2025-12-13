"""
Broadcast Service Core Module.

Contains core broadcast management functionality including
broadcast lifecycle management and basic message sending.
"""

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import TELEGRAM_TIMEOUT
from app.utils.datetime_utils import utc_now


class BroadcastServiceCore:
    """Core service for handling broadcast management."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self._cancel_event = asyncio.Event()
        self._broadcasts_lock = asyncio.Lock()
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
        broadcast_id = (
            f"broadcast_{admin_id}_{int(utc_now().timestamp())}"
        )

        # Start background task with error handler
        task = asyncio.create_task(
            self._broadcast_task(
                admin_id,
                broadcast_data,
                button_data,
                admin_telegram_id,
                broadcast_id,
            )
        )
        task.add_done_callback(self._handle_task_error)

        return broadcast_id

    def _handle_task_error(self, task: asyncio.Task) -> None:
        """Handle errors from background broadcast tasks."""
        try:
            task.result()
        except Exception as e:
            logger.error(
                f"Background broadcast task failed: {e}", exc_info=True
            )

    async def cancel_broadcast(self, broadcast_id: str) -> bool:
        """
        Cancel active broadcast.

        Args:
            broadcast_id: Broadcast ID to cancel

        Returns:
            True if broadcast was cancelled, False if not found
        """
        async with self._broadcasts_lock:
            if broadcast_id in self._active_broadcasts:
                self._active_broadcasts[broadcast_id]["cancelled"] = True
                logger.info(
                    f"Broadcast {broadcast_id} marked for cancellation"
                )
                return True
            return False

    async def get_broadcast_progress(
        self, broadcast_id: str
    ) -> dict | None:
        """
        Get progress of active broadcast.

        Args:
            broadcast_id: Broadcast ID

        Returns:
            Progress dict with keys: progress, total, cancelled,
            or None if not found
        """
        async with self._broadcasts_lock:
            # Return a copy to prevent external modification
            broadcast_data = self._active_broadcasts.get(broadcast_id)
            return broadcast_data.copy() if broadcast_data else None

    async def broadcast_to_users(
        self, user_ids: list[int], message: str
    ) -> dict:
        """
        Send message to specific users with batching and rate limiting.

        Args:
            user_ids: List of user telegram IDs
            message: Message text to send

        Returns:
            Dict with sent/failed counts

        Performance: Uses batching (20 users/batch) with 1s delay
        between batches to avoid Telegram rate limits.
        """
        BATCH_SIZE = 20
        results = {"sent": 0, "failed": 0}

        for i in range(0, len(user_ids), BATCH_SIZE):
            batch = user_ids[i : i + BATCH_SIZE]
            tasks = [
                self._send_message_safe(uid, message) for uid in batch
            ]
            batch_results = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            for r in batch_results:
                if isinstance(r, Exception):
                    results["failed"] += 1
                    logger.debug(f"Failed to send message: {r}")
                else:
                    results["sent"] += 1

            # Pause between batches to avoid rate limiting
            if i + BATCH_SIZE < len(user_ids):
                await asyncio.sleep(1.0)

        logger.info(
            f"Broadcast to users completed: {results['sent']} sent, "
            f"{results['failed']} failed out of {len(user_ids)} total"
        )
        return results

    async def _send_message_safe(
        self, user_id: int, message: str
    ) -> bool:
        """
        Safely send message to a user.

        Args:
            user_id: User telegram ID
            message: Message text

        Returns:
            True if sent successfully, False otherwise

        Raises:
            Exception if send fails (caught by caller)
        """
        try:
            await asyncio.wait_for(
                self.bot.send_message(
                    user_id,
                    message,
                    parse_mode="Markdown",
                ),
                timeout=TELEGRAM_TIMEOUT,
            )
            return True
        except TelegramForbiddenError:
            logger.debug(f"User {user_id} blocked the bot")
            return False
        except TimeoutError:
            logger.warning(f"Timeout sending to {user_id}")
            return False
        except Exception as e:
            logger.debug(f"Failed to send to {user_id}: {e}")
            return False

    async def _broadcast_task(
        self,
        admin_id: int,
        broadcast_data: dict,
        button_data: dict | None,
        admin_telegram_id: int,
        broadcast_id: str,
    ) -> None:
        """
        Background broadcast task.

        This method should be implemented in subclass.
        """
        raise NotImplementedError(
            "Subclass must implement _broadcast_task"
        )
