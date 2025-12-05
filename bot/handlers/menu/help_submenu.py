"""
Help submenu handlers.

This module contains handlers for the help submenu, which includes:
- FAQ
- Instructions
- Rules
- Support contact
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.keyboards.user import help_submenu_keyboard
from bot.utils.user_loader import UserLoader

router = Router()


@router.message(StateFilter('*'), F.text == "💬 Помощь")
async def show_help_submenu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show help submenu.

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[SUBMENU] Help submenu requested by user {telegram_id}")

    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    text = (
        "💬 *Помощь и поддержка*\n\n"
        "Здесь вы найдете всю необходимую информацию:\n\n"
        "❓ *FAQ* — ответы на частые вопросы\n"
        "📖 *Инструкции* — как пользоваться ботом\n"
        "📋 *Правила* — правила платформы\n"
        "✉️ *Написать в поддержку* — связаться с администрацией\n\n"
        "Выберите нужный раздел:"
    )

    await message.answer(
        text,
        reply_markup=help_submenu_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"[SUBMENU] Help submenu shown to user {telegram_id}")


@router.message(StateFilter('*'), F.text == "❓ FAQ")
async def show_faq(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show FAQ (Frequently Asked Questions).

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[FAQ] FAQ requested by user {telegram_id}")

    await state.clear()

    faq_text = (
        "❓ *Часто задаваемые вопросы (FAQ)*\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "*1. Как начать работу с ботом?*\n"
        "• Пройдите регистрацию через /start\n"
        "• Привяжите кошелек USDT (TRC-20)\n"
        "• Создайте финансовый пароль\n"
        "• Сделайте первый депозит\n\n"
        "*2. Какие уровни депозитов доступны?*\n"
        "• Level 1: 10 USDT\n"
        "• Level 2: 50 USDT\n"
        "• Level 3: 100 USDT\n"
        "• Level 4: 150 USDT\n"
        "• Level 5: 300 USDT\n\n"
        "*3. Как вывести средства?*\n"
        "• Перейдите в раздел «💸 Вывод»\n"
        "• Укажите сумму или выведите все\n"
        "• Подтвердите операцию финпаролем\n"
        "• Ожидайте обработки (до 24 часов)\n\n"
        "*4. Что такое финпароль?*\n"
        "Финансовый пароль защищает ваши средства. "
        "Он требуется для вывода и смены кошелька.\n\n"
        "*5. Как работает реферальная программа?*\n"
        "Получайте 5% от депозитов каждого приглашенного друга. "
        "Средства начисляются на реферальный кошелек.\n\n"
        "*6. Что делать, если забыл финпароль?*\n"
        "Используйте функцию восстановления в разделе «🔐 Финпароль».\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "💡 Не нашли ответ? Используйте кнопку «✉️ Написать в поддержку»"
    )

    await message.answer(
        faq_text,
        reply_markup=help_submenu_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"[FAQ] FAQ shown to user {telegram_id}")


@router.message(StateFilter('*'), F.text == "✉️ Написать в поддержку")
async def show_support_contact(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show support contact options.

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[SUPPORT] Support contact requested by user {telegram_id}")

    await state.clear()

    text = (
        "✉️ *Связь с поддержкой*\n\n"
        "Вы можете связаться с нашей службой поддержки несколькими способами:\n\n"
        "1️⃣ *Создать обращение в боте*\n"
        "Используйте кнопку ниже для создания обращения прямо в боте. "
        "Администрация ответит вам в течение 24 часов.\n\n"
        "2️⃣ *Связаться напрямую*\n"
        "Напишите администратору @support_username\n\n"
        "⏰ Время работы поддержки: ежедневно, 24/7\n"
        "⚡ Среднее время ответа: 1-3 часа"
    )

    # Add inline keyboard with support options
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✉️ Создать обращение",
            callback_data="support:create_inquiry"
        )],
        [InlineKeyboardButton(
            text="📋 Мои обращения",
            callback_data="support:my_inquiries"
        )],
    ])

    await message.answer(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )

    # Send back button with reply keyboard
    await message.answer(
        "⬅️ Для возврата в меню помощи:",
        reply_markup=help_submenu_keyboard()
    )
    logger.info(f"[SUPPORT] Support contact shown to user {telegram_id}")
