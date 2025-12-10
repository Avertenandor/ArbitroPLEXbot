"""
Withdrawal history module.

This module handles displaying withdrawal transaction history with pagination support.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.models.user import User
from app.services.withdrawal.withdrawal_lifecycle_handler import (
    WithdrawalLifecycleHandler,
)
from app.services.withdrawal_service import WithdrawalService
from bot.keyboards.user.menus.financial_menu import withdrawal_menu_keyboard

# Router will be created in __init__.py and imported there
router = Router()


@router.message(F.text == "📜 История выводов")
async def show_history(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show withdrawal history."""
    user: User | None = data.get("user")
    if not user:
        return

    # Filter out 'user' to avoid duplicate argument error
    filtered_data = {k: v for k, v in data.items() if k != "user"}
    await _show_withdrawal_history(message, state, user, page=1, **filtered_data)


async def _show_withdrawal_history(
    message: Message,
    state: FSMContext,
    user: User,
    page: int = 1,
    **data: Any,
) -> None:
    """Show withdrawal history with pagination."""
    session_factory = data.get("session_factory")

    if not session_factory:
        session = data.get("session")
        if not session:
            await message.answer("❌ Системная ошибка.")
            return
        withdrawal_service = WithdrawalService(session)
        result = await withdrawal_service.get_user_withdrawals(
            user.id, page=page, limit=10
        )
    else:
        async with session_factory() as session:
            async with session.begin():
                withdrawal_service = WithdrawalService(session)
                result = await withdrawal_service.get_user_withdrawals(
                    user.id, page=page, limit=10
                )

    withdrawals = result["withdrawals"]
    result["total"]
    total_pages = result["pages"]

    await state.update_data(withdrawal_page=page)

    if not withdrawals:
        await message.answer(
            "📜 История выводов пуста",
            reply_markup=withdrawal_menu_keyboard()
        )
        return

    text = f"📜 *История выводов* (Страница {page}/{total_pages})\n\n"

    # Build inline buttons for PENDING withdrawals
    inline_buttons = []

    for tx in withdrawals:
        status_icon = {
            "pending": "⏳",
            "processing": "⚙️",
            "confirmed": "✅",
            "failed": "❌",
            "frozen": "❄️"
        }.get(tx.status, "❓")

        date = tx.created_at.strftime("%d.%m.%Y %H:%M")
        net_amount = tx.amount - tx.fee
        text += f"{status_icon} *{tx.amount} USDT* (комиссия: {tx.fee}, получено: {net_amount}) | {date}\n"
        text += f"ID: `{tx.id}`\n"
        if tx.tx_hash:
            text += f"🔗 [BscScan](https://bscscan.com/tx/{tx.tx_hash})\n"

        # Add cancel button for PENDING withdrawals
        if tx.status == "pending":
            inline_buttons.append([
                InlineKeyboardButton(
                    text=f"❌ Отменить вывод ID:{tx.id}",
                    callback_data=f"cancel_withdrawal_{tx.id}"
                )
            ])

        text += "───────────────────\n"

    # Create inline keyboard if there are any PENDING withdrawals
    inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_buttons) if inline_buttons else None

    # Pagination keyboard would go here (omitted for brevity, assume simple list)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=inline_markup or withdrawal_menu_keyboard()
    )


@router.callback_query(F.data.startswith("cancel_withdrawal_"))
async def handle_cancel_withdrawal_request(
    callback: CallbackQuery,
    user: User,
    **data: Any,
) -> None:
    """Handle withdrawal cancellation request - show confirmation."""
    if not callback.data:
        await callback.answer("Ошибка: некорректные данные")
        return

    # Extract transaction ID
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка: некорректный ID транзакции")
        return

    # Show confirmation dialog
    confirmation_text = (
        f"⚠️ *Подтверждение отмены*\n\n"
        f"Вы действительно хотите отменить вывод ID: `{tx_id}`?\n\n"
        f"После отмены средства будут возвращены на ваш баланс."
    )

    confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да, отменить",
                callback_data=f"confirm_cancel_{tx_id}"
            ),
            InlineKeyboardButton(
                text="❌ Нет, вернуться",
                callback_data=f"reject_cancel_{tx_id}"
            )
        ]
    ])

    await callback.message.edit_text(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=confirmation_keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_cancel_"))
async def handle_confirm_cancel_withdrawal(
    callback: CallbackQuery,
    user: User,
    **data: Any,
) -> None:
    """Handle confirmed withdrawal cancellation."""
    if not callback.data:
        await callback.answer("Ошибка: некорректные данные")
        return

    # Extract transaction ID
    try:
        tx_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка: некорректный ID транзакции")
        return

    # Get session from data
    session = data.get("session")
    session_factory = data.get("session_factory")

    if not session and not session_factory:
        await callback.answer("❌ Системная ошибка")
        return

    # Process cancellation
    try:
        if session:
            lifecycle_handler = WithdrawalLifecycleHandler(session)
            success, error_msg = await lifecycle_handler.cancel_withdrawal(
                tx_id, user.id
            )
        else:
            async with session_factory() as sess:
                async with sess.begin():
                    lifecycle_handler = WithdrawalLifecycleHandler(sess)
                    success, error_msg = await lifecycle_handler.cancel_withdrawal(
                        tx_id, user.id
                    )

        if success:
            success_text = (
                f"✅ *Вывод успешно отменен*\n\n"
                f"Вывод ID: `{tx_id}` был отменен.\n"
                f"Средства возвращены на ваш баланс."
            )
            await callback.message.edit_text(
                success_text,
                parse_mode="Markdown"
            )
            await callback.answer("✅ Вывод отменен")
        else:
            error_text = (
                f"❌ *Ошибка отмены вывода*\n\n"
                f"{error_msg or 'Не удалось отменить вывод'}"
            )
            await callback.message.edit_text(
                error_text,
                parse_mode="Markdown"
            )
            await callback.answer(f"❌ {error_msg or 'Ошибка отмены'}")

    except Exception:
        await callback.message.edit_text(
            "❌ *Системная ошибка*\n\nНе удалось отменить вывод. Попробуйте позже.",
            parse_mode="Markdown"
        )
        await callback.answer("❌ Системная ошибка")


@router.callback_query(F.data.startswith("reject_cancel_"))
async def handle_reject_cancel_withdrawal(
    callback: CallbackQuery,
    **data: Any,
) -> None:
    """Handle rejection of withdrawal cancellation - return to history."""
    await callback.message.edit_text(
        "ℹ️ Отмена вывода отменена.\n\n"
        "Используйте кнопку '📜 История выводов' чтобы вернуться к истории.",
        parse_mode="Markdown"
    )
    await callback.answer("Действие отменено")
