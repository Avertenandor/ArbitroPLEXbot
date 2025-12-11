"""
Developer Chat Handler - Direct communication with Copilot/Claude.

This handler allows admins to respond to messages from the development AI.
Responses are stored in Redis for Copilot to read.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dev_chat_service import DevChatService


router = Router(name="dev_chat")


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
            "Или просто ответьте на сообщение от разработчика.",
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
                    "✅ **Ответ отправлен разработчику!**\n\n"
                    f"Ваше сообщение: _{response_text[:100]}{'...' if len(response_text) > 100 else ''}_",
                    parse_mode="Markdown",
                )
                logger.info(f"DevChat: Admin @{admin_username} sent response")
            else:
                await message.answer("❌ Ошибка отправки ответа")
        else:
            # Fallback - just log
            logger.info(f"DevChat response from @{admin_username}: {response_text}")
            await message.answer(
                "✅ Ответ записан (режим без Redis)",
                parse_mode="Markdown",
            )

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
        "🔧 **Dev Chat Status**\n\n"
        "Этот канал используется для прямой связи с разработчиком (Copilot/Claude).\n\n"
        "**Команды:**\n"
        "• `/dev_reply <текст>` - ответить разработчику\n"
        "• `/dev_status` - эта справка\n\n"
        "_Когда разработчик отправляет вам сообщение, просто ответьте "
        "командой /dev\\_reply или через 🤖 AI Помощник._",
        parse_mode="Markdown",
    )
