"""
Admin Withdrawals - Approval/Rejection Handler.

Handles withdrawal approval and rejection with dual control support.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.services.admin_log_service import AdminLogService
from app.services.blockchain_service import get_blockchain_service
from app.services.notification_service import NotificationService
from app.services.user_service import UserService
from app.services.withdrawal_service import WithdrawalService
from bot.keyboards.reply import admin_withdrawals_keyboard, withdrawal_confirm_keyboard
from bot.states.admin_states import AdminStates
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import format_usdt

router = Router(name="admin_withdrawals_approval")


async def _show_confirmation(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    action: str,
) -> None:
    """Show confirmation dialog."""
    fsm_data = await state.get_data()
    withdrawal_id = fsm_data.get("withdrawal_id")

    if not withdrawal_id:
        await message.answer("❌ Ошибка: ID заявки не найден.")
        # Import here to avoid circular dependency
        from bot.handlers.admin.withdrawals.pending import handle_pending_withdrawals

        await handle_pending_withdrawals(message, session, state)
        return

    action_text = "ОДОБРИТЬ" if action == "approve" else "ОТКЛОНИТЬ"
    action_emoji = "✅" if action == "approve" else "❌"

    await state.set_state(AdminStates.confirming_withdrawal_action)

    await message.answer(
        f"{action_emoji} **Подтверждение: {action_text}**\n\n"
        f"📝 Заявка: #{withdrawal_id}\n\n"
        f"Вы уверены, что хотите **{action_text.lower()}** эту заявку?",
        parse_mode="Markdown",
        reply_markup=withdrawal_confirm_keyboard(withdrawal_id, action),
    )


@router.message(
    F.text.regexp(r"^✅ Да, (одобрить|отклонить) #(\d+)$"),
    AdminStates.confirming_withdrawal_action,
)
async def handle_confirm_withdrawal_action(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Execute the confirmed withdrawal action."""
    fsm_data = await state.get_data()
    action = fsm_data.get("withdrawal_action")
    withdrawal_id = fsm_data.get("withdrawal_id")

    await clear_state_preserve_admin_token(state)

    if not withdrawal_id:
        await message.answer(
            "❌ Ошибка: ID заявки не найден.",
            reply_markup=admin_withdrawals_keyboard(),
        )
        return

    withdrawal_service = WithdrawalService(session)
    user_service = UserService(session)
    notification_service = NotificationService(session)
    admin: Admin | None = data.get("admin")

    try:
        withdrawal = await withdrawal_service.get_withdrawal_by_id(withdrawal_id)

        if not withdrawal:
            await message.answer(
                f"❌ Заявка #{withdrawal_id} не найдена.",
                reply_markup=admin_withdrawals_keyboard(),
            )
            return

        if action == "approve":
            # Check maintenance mode
            from app.config.settings import settings

            if settings.blockchain_maintenance_mode:
                await message.answer(
                    "⚠️ **Blockchain в режиме обслуживания**\n\n"
                    "Операции с блокчейном временно недоступны.",
                    parse_mode="Markdown",
                    reply_markup=admin_withdrawals_keyboard(),
                )
                return

            # Check dual control
            withdrawal_amount = float(withdrawal.amount)
            requires_dual_control = (
                withdrawal_amount >= settings.dual_control_withdrawal_threshold
            )

            if requires_dual_control:
                # Create escrow for dual control
                from app.repositories.admin_action_escrow_repository import (
                    AdminActionEscrowRepository,
                )

                escrow_repo = AdminActionEscrowRepository(session)
                admin_id = admin.id if admin else None

                existing_escrow = await escrow_repo.get_pending_by_operation(
                    "WITHDRAWAL_APPROVAL", withdrawal_id
                )

                if existing_escrow:
                    if existing_escrow.initiator_admin_id == admin_id:
                        await message.answer(
                            f"⚠️ Для вывода {withdrawal_amount} USDT требуется "
                            "подтверждение второго администратора.\n\n"
                            f"Escrow #{existing_escrow.id} ожидает подтверждения.",
                            reply_markup=admin_withdrawals_keyboard(),
                        )
                        return

                escrow = await escrow_repo.create(
                    operation_type="WITHDRAWAL_APPROVAL",
                    target_id=withdrawal_id,
                    operation_data={
                        "transaction_id": withdrawal_id,
                        "amount": str(withdrawal.amount),
                        "user_id": withdrawal.user_id,
                        "to_address": withdrawal.to_address,
                    },
                    initiator_admin_id=admin_id,
                    expires_in_hours=settings.dual_control_escrow_expiry_hours,
                )
                await session.commit()

                await message.answer(
                    f"⚠️ Для вывода {withdrawal_amount} USDT требуется "
                    "подтверждение второго администратора.\n\n"
                    f"Escrow #{escrow.id} создан.",
                    reply_markup=admin_withdrawals_keyboard(),
                )
                return

            # Send blockchain transaction
            blockchain_service = get_blockchain_service()
            # CRITICAL: Send net_amount (amount - fee) to user, not gross amount
            # User requested 'amount', we deducted 'amount', but send 'amount - fee'
            net_amount = withdrawal.amount - withdrawal.fee
            payment_result = await blockchain_service.send_payment(
                withdrawal.to_address, net_amount
            )

            if not payment_result["success"]:
                error_msg = payment_result.get("error", "Неизвестная ошибка")
                await message.answer(
                    f"❌ Ошибка отправки: {error_msg}",
                    reply_markup=admin_withdrawals_keyboard(),
                )
                return

            tx_hash = payment_result["tx_hash"]
            admin_id = admin.id if admin else None
            success, error_msg = await withdrawal_service.approve_withdrawal(
                withdrawal_id, tx_hash, admin_id
            )

            if not success:
                await message.answer(
                    f"❌ Ошибка: {error_msg}",
                    reply_markup=admin_withdrawals_keyboard(),
                )
                return

            # Notify user
            user = await user_service.find_by_id(withdrawal.user_id)
            if user:
                logger.info(f"Attempting to notify user {user.id} (TG: {user.telegram_id}) about withdrawal {tx_hash}")
                notify_result = await notification_service.notify_withdrawal_processed(
                    user.telegram_id, float(withdrawal.amount), tx_hash
                )
                logger.info(f"Notification result for user {user.id}: {notify_result}")
            else:
                logger.warning(f"User {withdrawal.user_id} not found for notification")

            await message.answer(
                f"✅ **Заявка #{withdrawal_id} одобрена!**\n\n"
                f"💰 Сумма: {format_usdt(withdrawal.amount)} USDT\n"
                f"🔗 TX: `{tx_hash}`\n\n"
                "Средства отправлены пользователю.",
                parse_mode="Markdown",
                reply_markup=admin_withdrawals_keyboard(),
            )

            # Log action
            if admin:
                log_service = AdminLogService(session)
                await log_service.log_withdrawal_approved(
                    admin=admin,
                    withdrawal_id=withdrawal_id,
                    user_id=withdrawal.user_id,
                    amount=str(withdrawal.amount),
                )

        else:  # reject
            success, error_msg = await withdrawal_service.reject_withdrawal(
                withdrawal_id
            )

            if not success:
                await message.answer(
                    f"❌ Ошибка: {error_msg}",
                    reply_markup=admin_withdrawals_keyboard(),
                )
                return

            # Notify user
            user = await user_service.find_by_id(withdrawal.user_id)
            if user:
                await notification_service.notify_withdrawal_rejected(
                    user.telegram_id, float(withdrawal.amount)
                )

            await message.answer(
                f"❌ **Заявка #{withdrawal_id} отклонена**\n\n"
                f"💰 Сумма: {format_usdt(withdrawal.amount)} USDT\n\n"
                "Средства возвращены на баланс пользователя.",
                parse_mode="Markdown",
                reply_markup=admin_withdrawals_keyboard(),
            )

            # Log action
            if admin:
                log_service = AdminLogService(session)
                await log_service.log_withdrawal_rejected(
                    admin=admin,
                    withdrawal_id=withdrawal_id,
                    user_id=withdrawal.user_id,
                    reason=None,
                )

    except Exception as e:
        await session.rollback()
        logger.error(f"Error processing withdrawal action: {e}")
        await message.answer(
            "❌ Ошибка при обработке. Попробуйте позже.",
            reply_markup=admin_withdrawals_keyboard(),
        )
