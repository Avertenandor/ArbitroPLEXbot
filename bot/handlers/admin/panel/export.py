"""
Admin Export Handler

Provides data export functionality for admins:
- /export - Export all users to CSV file
"""

from datetime import UTC, datetime
from typing import Any

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny

router = Router(name="admin_panel_export")


@router.message(Command("export"))
async def cmd_export_users(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Export all users to CSV file for admins.
    Usage: /export
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.services.financial_report_service import FinancialReportService

    # Send typing indicator
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.UPLOAD_DOCUMENT
    )

    try:
        report_service = FinancialReportService(session)
        csv_data = await report_service.export_all_users_csv()

        # Create file
        file_bytes = csv_data.encode('utf-8-sig')  # BOM for Excel compatibility
        file = BufferedInputFile(
            file_bytes,
            filename=f"users_export_{datetime.now(UTC).strftime('%Y%m%d_%H%M')}.csv"
        )

        await message.answer_document(
            file,
            caption="📊 *Экспорт пользователей*\n\nФайл содержит данные всех пользователей.",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        await message.answer("❌ Ошибка при экспорте пользователей.")
