"""
User Support Handler - УПРОЩЕННАЯ ВЕРСИЯ с Reply Keyboards
"""

from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.models.user import User
from bot.keyboards.reply import support_keyboard
from bot.states.support_states import SupportStates
from bot.utils.formatters import escape_md

router = Router(name="support")


@router.message(F.text == "💬 Поддержка")
async def handle_support_menu(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show support menu."""
    await state.clear()

    text = "💬 *Служба поддержки*\n\nВыберите действие из меню ниже:"

    await message.answer(
        text, reply_markup=support_keyboard(), parse_mode="Markdown"
    )


@router.message(F.text == "✉️ Создать обращение")
async def handle_create_ticket(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start ticket creation.

    R1-7: Supports guest tickets (user_id=None, telegram_id required).
    """
    data.get("user")
    telegram_id = message.from_user.id if message.from_user else None

    # R1-7: Разрешаем гостевые тикеты
    if not telegram_id:
        await message.answer(
            "❌ Системная ошибка. Отправьте /start или попробуйте позже.",
            reply_markup=support_keyboard(),
        )
        return

    text = (
        "✉️ *Создать обращение*\n\n"
        "Опишите вашу проблему или вопрос.\n"
        "Отправьте текстовое сообщение.\n\n"
        "💡 **Совет:** Если вопрос касается финансов, укажите:\n"
        "• ID транзакции (Hash)\n"
        "• Сумму и дату\n\n"
        "Для отмены нажмите '📊 Главное меню'"
    )

    await state.set_state(SupportStates.awaiting_input)
    await message.answer(text, parse_mode="Markdown")


@router.message(SupportStates.awaiting_input)
async def process_ticket_message(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process ticket message.
    Uses session_factory for short transaction during ticket creation.
    """
    user: User | None = data.get("user")
    from bot.utils.menu_buttons import is_menu_button

    # Check if user pressed menu button
    if is_menu_button(message.text):
        await state.clear()
        return

    # Save ticket to database with SHORT transaction
    from app.models.enums import SupportCategory
    from app.services.support_service import SupportService

    session_factory = data.get("session_factory")
    telegram_id = message.from_user.id if message.from_user else None

    if not telegram_id:
        await state.clear()
        await message.answer("❌ Ошибка: не удалось определить пользователя")
        return

    try:
        if not session_factory:
            # Fallback to old session for backward compatibility
            session = data.get("session")
            if not session:
                await state.clear()
                await message.answer(
                    "❌ Системная ошибка. Отправьте /start или "
                    "обратитесь в поддержку."
                )
                return

            support_service = SupportService(session)
            # Create ticket: use user.id if user exists,
            # otherwise None for guest ticket
            user_id = user.id if user else None
            ticket, error = await support_service.create_ticket(
                user_id=user_id,
                telegram_id=telegram_id if user_id is None else None,
                category=SupportCategory.OTHER,
                initial_message=message.text,
            )
        else:
            # NEW pattern: short transaction
            async with session_factory() as session:
                async with session.begin():
                    support_service = SupportService(session)
                    # Create ticket: use user.id if user exists,
            # otherwise None for guest ticket
                    user_id = user.id if user else None
                    ticket, error = await support_service.create_ticket(
                        user_id=user_id,
                        telegram_id=telegram_id if user_id is None else None,
                        category=SupportCategory.OTHER,
                        initial_message=message.text,
                    )
            # Transaction closed here

        if error or not ticket:
            await message.answer(
                f"❌ Ошибка при создании обращения:\n{error}",
                parse_mode="Markdown",
            )
            await state.clear()
            return

        await state.clear()

        text = (
            f"✅ *Обращение создано!*\n\n"
            f"Номер: `#{ticket.id}`\n"
            f"Статус: Открыто\n\n"
            f"Мы ответим вам в ближайшее время."
        )

        await message.answer(
            text, parse_mode="Markdown", reply_markup=support_keyboard()
        )

        # Notify admins
        from app.config.settings import settings
        from bot.main import bot_instance

        if bot_instance:
            # Format admin notification
            if user:
                username = escape_md(user.username) if user.username else "пользователь"
                admin_text = (
                    f"🆕 *Новое обращение #{ticket.id}*\n\n"
                    f"От: @{username} "
                    f"(`{user.telegram_id}`)\n"
                    f"Текст: {message.text}"
                )
            else:
                # Guest ticket
                username = (
                    escape_md(message.from_user.username)
                    if message.from_user and message.from_user.username
                    else "гость"
                )
                admin_text = (
                    f"🆕 *Новое обращение #{ticket.id}* (Гость)\n\n"
                    f"От: @{username} (`{telegram_id}`)\n"
                    f"Текст: {message.text}"
                )

            for admin_id in settings.get_admin_ids():
                try:
                    await bot_instance.send_message(
                        admin_id, admin_text, parse_mode="Markdown"
                    )
                except TelegramAPIError as e:
                    logger.warning(f"Failed to notify admin {admin_id}: {e}")

    except Exception as e:
        await state.clear()
        await message.answer(f"❌ Ошибка создания обращения: {e}")


@router.message(F.text == "📋 Мои обращения")
async def handle_my_tickets(
    message: Message,
    **data: Any,
) -> None:
    """
    Show user's or guest's tickets.
    Uses session_factory for short read transaction.
    Supports both registered users and guests.
    """
    user: User | None = data.get("user")
    telegram_id = message.from_user.id if message.from_user else None
    from app.services.support_service import SupportService

    if not telegram_id:
        await message.answer(
            "❌ Системная ошибка. Отправьте /start или попробуйте позже.",
            reply_markup=support_keyboard(),
        )
        return

    session_factory = data.get("session_factory")

    if not session_factory:
        # Fallback to old session
        session = data.get("session")
        if not session:
            await message.answer(
                "❌ Системная ошибка. Отправьте /start или попробуйте позже.",
                reply_markup=support_keyboard(),
            )
            return
        support_service = SupportService(session)
        if user:
            tickets = await support_service.get_user_tickets(user.id)
        else:
            # Guest tickets
            tickets = await support_service.get_guest_tickets(telegram_id)
    else:
        # NEW pattern: short read transaction
        async with session_factory() as session:
            async with session.begin():
                support_service = SupportService(session)
                if user:
                    tickets = await support_service.get_user_tickets(user.id)
                else:
                    # Guest tickets
                    tickets = await support_service.get_guest_tickets(telegram_id)
        # Transaction closed here

    # R1-8: Просмотр обращений у гостя
    if not tickets:
        if user is None:
            text = (
                "📋 *Мои обращения*\n\n"
                "У вас пока нет обращений.\n\n"
                "Для создания обращения используйте кнопку '✉️ Создать обращение'."
            )
        else:
            text = "📋 У вас пока нет обращений"
    else:
        text = "📋 *Ваши обращения:*\n\n"

        for ticket in tickets[:10]:  # Show last 10
            status_emoji = {
                "open": "🔵",
                "in_progress": "🟡",
                "answered": "🟢",
                "closed": "⚫",
            }.get(ticket.status, "⚪")

            created_date = ticket.created_at.strftime('%d.%m.%Y %H:%M')
            subject = getattr(ticket, 'subject', 'Обращение')
            # Add "(Гость)" marker for guest tickets
            guest_marker = " (Гость)" if user is None else ""
            text += (
                f"{status_emoji} #{ticket.id} - {subject}{guest_marker}\n"
                f"   Создано: {created_date}\n\n"
            )

    await message.answer(
        text, parse_mode="Markdown", reply_markup=support_keyboard()
    )


@router.message(F.text == "❓ FAQ")
async def handle_faq(
    message: Message,
) -> None:
    """Show FAQ."""
    text = (
        "❓ *Часто задаваемые вопросы*\n\n"
        "*Q: Как сделать депозит?*\n"
        "A: Выберите '💰 Депозит' → Выберите уровень → Отправьте USDT.\n"
        "⚠️ **Важно:** Только через сеть BSC (BEP-20) с личного кошелька!\n\n"
        "*Q: Сколько ждать подтверждения депозита?*\n"
        "A: Обычно 1-3 минуты после подтверждения в блокчейне.\n"
        "ℹ️ Требуется минимум 12 подтверждений в сети BSC.\n\n"
        "*Q: Как вывести средства?*\n"
        "A: Выберите '💸 Вывод' → Укажите сумму → Подтвердите фин. паролем.\n"
        "ℹ️ Выводы идут в USDT по сети BSC (BEP-20).\n\n"
        "*Q: Почему вывод заблокирован?*\n"
        "A: Возможные причины:\n"
        "• Недостаточно средств на балансе\n"
        "• Не хватает PLEX токенов\n"
        "• Активный депозит еще не завершен\n"
        "• Неверный финансовый пароль\n\n"
        "*Q: Что такое PLEX токен и зачем он нужен?*\n"
        "A: PLEX - внутренний токен платформы для комиссий.\n"
        "💡 Используется для оплаты транзакций, участия в арбитраже.\n"
        "⚠️ **Без PLEX работа бота останавливается!**\n\n"
        "*Q: Сколько PLEX нужно в день?*\n"
        "A: Зависит от уровня депозита:\n"
        "• Уровень 1-2: ~10-20 PLEX/день\n"
        "• Уровень 3-4: ~30-50 PLEX/день\n"
        "• Уровень 5-6: ~60-100 PLEX/день\n\n"
        "*Q: Что будет если PLEX закончится?*\n"
        "A: Бот прекратит арбитражные операции → доход остановится.\n"
        "⚠️ **Важно:** Регулярно пополняйте PLEX для непрерывной работы!\n\n"
        "*Q: Откуда берется доход 30-70%?*\n"
        "A: От арбитража между DEX биржами (разница цен).\n"
        "💡 Бот автоматически находит выгодные сделки 24/7.\n"
        "ℹ️ Доход зависит от волатильности рынка и уровня депозита.\n\n"
        "*Q: Почему нужны кролики DEXRabbit?*\n"
        "A: Кролики - это NFT для повышения прибыли:\n"
        "• Увеличивают скорость арбитража\n"
        "• Дают бонус к доходности (+5-15%)\n"
        "• Открывают доступ к премиум сделкам\n\n"
        "*Q: Как работает реферальная программа?*\n"
        "A: Пригласите друга → Получайте % от его депозитов.\n"
        "🎁 **3 уровня наград:**\n"
        "• 1 уровень: 5% от депозитов\n"
        "• 2 уровень: 3% от депозитов\n"
        "• 3 уровень: 2% от депозитов\n"
        "💰 Выплаты моментально на баланс!\n\n"
        "*Q: Как восстановить аккаунт?*\n"
        "A: Аккаунт привязан к вашему Telegram ID.\n"
        "✅ Просто отправьте /start - данные восстановятся автоматически.\n"
        "⚠️ Финпароль восстанавливается через '🔑 Восстановить финпароль'.\n\n"
        "*Q: Что делать если забыл финансовый пароль?*\n"
        "A: Используйте пункт '🔑 Восстановить финпароль'.\n"
        "ℹ️ Потребуется подтверждение через поддержку.\n\n"
        "*Q: Безопасно ли это?*\n"
        "A: Да! Мы используем:\n"
        "✅ Смарт-контракты для хранения средств\n"
        "✅ Финансовый пароль для вывода\n"
        "✅ Работаем только с проверенными DEX\n"
        "⚠️ **Никогда не сообщайте финпароль третьим лицам!**\n\n"
        "Для других вопросов создайте обращение в поддержку."
    )

    await message.answer(
        text, parse_mode="Markdown", reply_markup=support_keyboard()
    )
