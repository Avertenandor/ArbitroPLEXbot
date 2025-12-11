"""
Developer Chat Handler - Direct communication with Copilot/Claude (Darya).

This handler allows admins to send messages directly to the developer.
Messages are stored in Redis for Copilot to read during monitoring.
"""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dev_chat_service import DevChatService


router = Router(name="dev_chat")


class DevChatStates(StatesGroup):
    """States for developer chat."""
    
    writing_message = State()  # Admin is writing a message to Darya


def get_dev_chat_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard for dev chat."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


@router.message(F.text == "💬 Написать Дарье")
async def handle_write_to_darya(
    message: Message,
    state: FSMContext,
    is_admin: bool = False,
    **kwargs,
):
    """Handle button press to write to Darya (developer)."""
    if not is_admin:
        return

    await state.set_state(DevChatStates.writing_message)
    
    await message.answer(
        "💬 **Написать Дарье (разработчику)**\n\n"
        "Привет! Я Дарья — ИИ-разработчик бота (Copilot/Claude).\n\n"
        "Напиши мне:\n"
        "• Что неудобно в боте?\n"
        "• Какие функции добавить?\n"
        "• Какие баги исправить?\n"
        "• Любые идеи и предложения!\n\n"
        "✍️ **Просто напиши сообщение ниже:**",
        parse_mode="Markdown",
        reply_markup=get_dev_chat_keyboard(),
    )


@router.message(StateFilter(DevChatStates.writing_message), F.text == "❌ Отмена")
async def handle_cancel_dev_chat(
    message: Message,
    state: FSMContext,
    **kwargs,
):
    """Cancel dev chat."""
    await state.clear()
    
    # Return to admin panel
    from bot.keyboards.reply import get_admin_keyboard_from_data
    
    await message.answer(
        "✅ Отменено. Возвращаю в админ-панель.",
        reply_markup=get_admin_keyboard_from_data(kwargs),
    )


@router.message(StateFilter(DevChatStates.writing_message))
async def handle_dev_chat_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    redis_client=None,
    **kwargs,
):
    """Handle message to Darya."""
    if not message.text:
        await message.answer("❌ Пожалуйста, напишите текстовое сообщение")
        return

    admin_username = message.from_user.username or str(message.from_user.id)
    admin_id = message.from_user.id
    response_text = message.text

    try:
        if redis_client:
            service = DevChatService(session, message.bot, redis_client)
            result = await service.record_admin_response(
                admin_id=admin_id,
                admin_username=admin_username,
                response_text=response_text,
            )

            if result.get("success"):
                await state.clear()
                
                from bot.keyboards.reply import get_admin_keyboard_from_data
                
                await message.answer(
                    "✅ **Сообщение отправлено Дарье!**\n\n"
                    f"Ваше сообщение:\n_{response_text[:200]}{'...' if len(response_text) > 200 else ''}_\n\n"
                    "Я прочитаю его при следующем мониторинге и отвечу или внесу изменения. "
                    "Если нужен быстрый ответ — напишите через 🤖 AI Помощник.",
                    parse_mode="Markdown",
                    reply_markup=get_admin_keyboard_from_data(kwargs),
                )
                logger.info(f"DevChat: @{admin_username} sent message to Darya: {response_text[:50]}...")
            else:
                await message.answer("❌ Ошибка отправки. Попробуйте ещё раз.")
        else:
            # Fallback without Redis - just log
            logger.info(f"DevChat (no Redis) from @{admin_username}: {response_text}")
            await state.clear()
            
            from bot.keyboards.reply import get_admin_keyboard_from_data
            
            await message.answer(
                "✅ Сообщение записано в лог. Дарья увидит его при мониторинге.",
                reply_markup=get_admin_keyboard_from_data(kwargs),
            )

    except Exception as e:
        logger.error(f"DevChat message error: {e}")
        await message.answer("❌ Ошибка. Попробуйте позже или используйте 🤖 AI Помощник.")


@router.message(Command("dev_reply"))
async def handle_dev_reply(
    message: Message,
    session: AsyncSession,
    redis_client=None,
    is_admin: bool = False,
    **kwargs,
):
    """
    Handle /dev_reply command - send response to developer.

    Usage: /dev_reply Your response message here
    """
    if not is_admin:
        return

    if not message.text:
        await message.answer("❌ Пожалуйста, добавьте текст ответа после команды")
        return

    # Extract response text (remove command)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "📝 **Ответ разработчику**\n\n"
            "Использование: `/dev_reply Ваш ответ`\n\n"
            "Или нажмите кнопку **💬 Написать Дарье** в админ-панели.",
            parse_mode="Markdown",
        )
        return

    response_text = parts[1]
    admin_username = message.from_user.username or str(message.from_user.id)
    admin_id = message.from_user.id

    try:
        if redis_client:
            service = DevChatService(session, message.bot, redis_client)
            result = await service.record_admin_response(
                admin_id=admin_id,
                admin_username=admin_username,
                response_text=response_text,
            )

            if result.get("success"):
                await message.answer(
                    "✅ **Сообщение отправлено Дарье!**\n\n"
                    f"_{response_text[:100]}{'...' if len(response_text) > 100 else ''}_",
                    parse_mode="Markdown",
                )
                logger.info(f"DevChat: Admin @{admin_username} sent response")
            else:
                await message.answer("❌ Ошибка отправки ответа")
        else:
            logger.info(f"DevChat response from @{admin_username}: {response_text}")
            await message.answer("✅ Ответ записан")

    except Exception as e:
        logger.error(f"DevChat reply error: {e}")
        await message.answer("❌ Ошибка обработки ответа")


@router.message(Command("dev_status"))
async def handle_dev_status(
    message: Message,
    is_admin: bool = False,
    **kwargs,
):
    """Show dev chat status."""
    if not is_admin:
        return

    await message.answer(
        "💬 **Связь с Дарьей (разработчиком)**\n\n"
        "Дарья — это ИИ-разработчик (Copilot/Claude), который:\n"
        "• Пишет код бота\n"
        "• Исправляет баги\n"
        "• Добавляет новые функции\n"
        "• Читает ваши сообщения при мониторинге\n\n"
        "**Как связаться:**\n"
        "• Кнопка **💬 Написать Дарье** в админ-панели\n"
        "• Команда `/dev_reply <текст>`\n\n"
        "_Дарья читает сообщения во время сессий разработки и оперативно вносит изменения._",
        parse_mode="Markdown",
    )
