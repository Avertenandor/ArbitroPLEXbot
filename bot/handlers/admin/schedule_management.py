"""
Schedule Management for Admin Panel.

Allows admins to view and control scheduled tasks:
- View all scheduled tasks and their status
- Manually trigger tasks
- Enable/disable tasks
- Adjust task intervals
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.keyboards.inline import InlineKeyboardBuilder

router = Router()


class ScheduleStates(StatesGroup):
    """Schedule management states."""

    viewing = State()
    editing_interval = State()


# Task definitions with metadata
SCHEDULED_TASKS = {
    "balance_notifications": {
        "name": "💰 Уведомления о балансе",
        "description": "Часовые уведомления о заработке пользователям",
        "default_interval": "1 час",
        "module": "jobs.tasks.balance_notification",
        "function": "send_balance_notifications",
        "can_trigger": True,
    },
    "plex_balance_monitor": {
        "name": "💎 Мониторинг PLEX балансов",
        "description": "Проверка достаточности PLEX для работы депозитов",
        "default_interval": "1 час",
        "module": "jobs.tasks.plex_balance_monitor",
        "function": "monitor_plex_balances",
        "can_trigger": True,
    },
    "daily_rewards": {
        "name": "📈 Начисление наград",
        "description": "Ежедневное начисление ROI по депозитам",
        "default_interval": "1 день (00:05 UTC)",
        "module": "jobs.tasks.daily_rewards",
        "function": "process_daily_rewards",
        "can_trigger": True,
    },
    "deposit_monitoring": {
        "name": "📦 Мониторинг депозитов",
        "description": "Проверка новых депозитов в блокчейне",
        "default_interval": "1 минута",
        "module": "jobs.tasks.deposit_monitoring",
        "function": "monitor_deposits",
        "can_trigger": True,
    },
    "blockchain_cache_sync": {
        "name": "⛓️ Синхронизация кэша",
        "description": "Синхронизация транзакций из блокчейна",
        "default_interval": "30 секунд",
        "module": "jobs.tasks.blockchain_cache_sync",
        "function": "sync_blockchain_cache",
        "can_trigger": True,
    },
    "notification_retry": {
        "name": "🔄 Повтор уведомлений",
        "description": "Повторная отправка неудачных уведомлений",
        "default_interval": "1 минута",
        "module": "jobs.tasks.notification_retry",
        "function": "process_notification_retries",
        "can_trigger": False,
    },
    "payment_retry": {
        "name": "💸 Повтор платежей",
        "description": "Повторная обработка неудачных платежей",
        "default_interval": "1 минута",
        "module": "jobs.tasks.payment_retry",
        "function": "process_payment_retries",
        "can_trigger": False,
    },
}


def schedule_main_keyboard():
    """Main schedule management keyboard."""
    builder = InlineKeyboardBuilder()

    for task_id, task in SCHEDULED_TASKS.items():
        builder.button(
            text=task["name"],
            callback_data=f"schedule_task:{task_id}"
        )

    builder.button(text="🔄 Обновить статус", callback_data="schedule_refresh")
    builder.button(text="◀️ Назад в админку", callback_data="admin_back")

    builder.adjust(1)
    return builder.as_markup()


def task_detail_keyboard(task_id: str, task: dict):
    """Task detail keyboard with actions."""
    builder = InlineKeyboardBuilder()

    if task.get("can_trigger", False):
        builder.button(
            text="▶️ Запустить сейчас",
            callback_data=f"schedule_run:{task_id}"
        )

    builder.button(text="📊 Статус задачи", callback_data=f"schedule_status:{task_id}")
    builder.button(text="◀️ Назад к списку", callback_data="schedule_list")

    builder.adjust(1)
    return builder.as_markup()


@router.message(StateFilter('*'), F.text == "⏰ Расписание задач")
async def show_schedule_management(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show schedule management panel."""
    user: User | None = data.get("user")

    if not user or not user.is_admin:
        await message.answer("❌ Доступ запрещён")
        return

    await state.set_state(ScheduleStates.viewing)

    text = (
        "⏰ *Управление расписанием*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Здесь вы можете:\n"
        "• Просматривать запланированные задачи\n"
        "• Запускать задачи вручную\n"
        "• Проверять статус выполнения\n\n"
        "Выберите задачу для управления:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=schedule_main_keyboard(),
    )

    logger.info(f"[ADMIN] Schedule management opened by {user.telegram_id}")


@router.callback_query(F.data == "schedule_list")
async def show_schedule_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show schedule task list."""
    await callback.answer()

    text = (
        "⏰ *Управление расписанием*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите задачу для управления:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=schedule_main_keyboard(),
    )


@router.callback_query(F.data.startswith("schedule_task:"))
async def show_task_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show task details."""
    await callback.answer()

    task_id = callback.data.split(":")[1]
    task = SCHEDULED_TASKS.get(task_id)

    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return

    text = (
        f"{task['name']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 *Описание:*\n{task['description']}\n\n"
        f"⏱️ *Интервал:* {task['default_interval']}\n"
        f"📦 *Модуль:* `{task['module']}`\n"
        f"🔧 *Функция:* `{task['function']}`\n\n"
        "_Выберите действие:_"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=task_detail_keyboard(task_id, task),
    )


@router.callback_query(F.data.startswith("schedule_run:"))
async def run_task_manually(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Manually trigger a scheduled task."""
    task_id = callback.data.split(":")[1]
    task = SCHEDULED_TASKS.get(task_id)

    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return

    if not task.get("can_trigger", False):
        await callback.answer("❌ Эту задачу нельзя запустить вручную", show_alert=True)
        return

    await callback.answer("⏳ Запускаю задачу...")

    user: User | None = data.get("user")
    logger.info(f"[ADMIN] Manual task trigger: {task_id} by {user.telegram_id if user else 'unknown'}")

    try:
        # Dynamically import and run the task
        if task_id == "balance_notifications":
            from jobs.tasks.balance_notification import send_balance_notifications
            send_balance_notifications.send()
            result_msg = "✅ Задача отправлена в очередь"

        elif task_id == "plex_balance_monitor":
            from jobs.tasks.plex_balance_monitor import monitor_plex_balances
            monitor_plex_balances.send()
            result_msg = "✅ Задача отправлена в очередь"

        elif task_id == "daily_rewards":
            from jobs.tasks.daily_rewards import process_daily_rewards
            process_daily_rewards.send()
            result_msg = "✅ Задача отправлена в очередь"

        elif task_id == "deposit_monitoring":
            from jobs.tasks.deposit_monitoring import monitor_deposits
            monitor_deposits.send()
            result_msg = "✅ Задача отправлена в очередь"

        elif task_id == "blockchain_cache_sync":
            from jobs.tasks.blockchain_cache_sync import sync_blockchain_cache
            sync_blockchain_cache.send()
            result_msg = "✅ Задача отправлена в очередь"

        else:
            result_msg = "❌ Неизвестная задача"

        text = (
            f"{task['name']}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 *Результат:* {result_msg}\n\n"
            f"📝 {task['description']}\n\n"
            "_Задача будет выполнена в ближайшее время._"
        )

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=task_detail_keyboard(task_id, task),
        )

    except Exception as e:
        logger.error(f"[ADMIN] Failed to trigger task {task_id}: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка запуска задачи:\n`{str(e)[:200]}`",
            parse_mode="Markdown",
            reply_markup=task_detail_keyboard(task_id, task),
        )


@router.callback_query(F.data.startswith("schedule_status:"))
async def show_task_status(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show task execution status from Redis."""
    await callback.answer("📊 Загружаю статус...")

    task_id = callback.data.split(":")[1]
    task = SCHEDULED_TASKS.get(task_id)

    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return

    try:
        import redis.asyncio as redis
        from app.config.settings import settings

        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password if settings.redis_password else None,
            db=settings.redis_db,
            decode_responses=True,
        )

        # Get last execution info
        last_run_key = f"scheduler:last_run:{task_id}"
        last_run = await redis_client.get(last_run_key)

        # Get execution count
        count_key = f"scheduler:count:{task_id}"
        exec_count = await redis_client.get(count_key) or "0"

        # Get error count
        error_key = f"scheduler:errors:{task_id}"
        error_count = await redis_client.get(error_key) or "0"

        await redis_client.close()

        status_text = (
            f"{task['name']} - Статус\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱️ *Последний запуск:*\n{last_run or 'Нет данных'}\n\n"
            f"📊 *Выполнений:* {exec_count}\n"
            f"❌ *Ошибок:* {error_count}\n\n"
            f"⏰ *Интервал:* {task['default_interval']}\n"
        )

    except Exception as e:
        logger.error(f"[ADMIN] Failed to get task status: {e}")
        status_text = (
            f"{task['name']} - Статус\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ Не удалось загрузить статистику\n"
            f"Ошибка: `{str(e)[:100]}`"
        )

    await callback.message.edit_text(
        status_text,
        parse_mode="Markdown",
        reply_markup=task_detail_keyboard(task_id, task),
    )


@router.callback_query(F.data == "schedule_refresh")
async def refresh_schedule_status(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Refresh schedule status."""
    await callback.answer("🔄 Обновлено")

    # Just re-show the list
    text = (
        "⏰ *Управление расписанием*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите задачу для управления:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=schedule_main_keyboard(),
    )
