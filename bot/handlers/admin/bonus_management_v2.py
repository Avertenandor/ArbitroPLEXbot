"""
Admin Bonus Management Handler V2.

ПОЛНОСТЬЮ ПЕРЕРАБОТАННЫЙ модуль управления бонусами:
- Интуитивное меню с понятной навигацией
- Быстрые шаблоны причин
- Детальная статистика
- Управление по ролям
- Отмена бонусов с логированием

Permissions:
- super_admin: Полный доступ + отмена любых бонусов
- extended_admin: Начисление + просмотр + отмена своих бонусов
- admin: Начисление + просмотр
- moderator: Только просмотр
"""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import (
    get_admin_or_deny,
    get_admin_or_deny_callback,
)
from bot.keyboards.reply import get_admin_keyboard_from_data
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown


if TYPE_CHECKING:
    from app.models.bonus_credit import BonusCredit

router = Router(name="admin_bonus_management_v2")


# ============ HELPERS ============


def get_bonus_status(bonus: "BonusCredit") -> str:
    """
    Get status string from BonusCredit model.

    Model has: is_active, is_roi_completed, cancelled_at
    Returns: "active", "completed", or "cancelled"
    """
    if bonus.cancelled_at is not None:
        return "cancelled"
    if bonus.is_roi_completed:
        return "completed"
    if bonus.is_active:
        return "active"
    return "inactive"


def get_bonus_status_emoji(bonus: "BonusCredit") -> str:
    """Get status emoji for bonus."""
    status = get_bonus_status(bonus)
    return {"active": "🟢", "completed": "✅", "cancelled": "❌", "inactive": "⚪"}.get(status, "⚪")


# ============ STATES ============


class BonusStates(StatesGroup):
    """States for bonus management."""

    menu = State()  # Главное меню бонусов
    select_action = State()  # Выбор действия

    # Начисление бонуса
    grant_user = State()  # Ввод пользователя
    grant_amount = State()  # Ввод суммы
    grant_reason = State()  # Ввод/выбор причины
    grant_confirm = State()  # Подтверждение

    # Поиск пользователя
    search_user = State()  # Поиск бонусов пользователя

    # Просмотр бонуса
    view_bonus = State()  # Детали бонуса

    # Отмена бонуса
    cancel_bonus = State()  # Отмена бонуса
    cancel_reason = State()  # Причина отмены


# ============ TEMPLATES ============

BONUS_REASON_TEMPLATES = [
    ("🎉 Приветственный", "Приветственный бонус за регистрацию"),
    ("🔧 Компенсация", "Компенсация за технические проблемы"),
    ("🏆 За активность", "Бонус за активное участие в проекте"),
    ("👥 Реферальный", "Бонус за привлечение рефералов"),
    ("🎁 Акция", "Бонус в рамках промо-акции"),
    ("⭐ VIP", "VIP-бонус для особого клиента"),
    ("📝 Другое", None),  # Ручной ввод
]

QUICK_AMOUNTS = [10, 25, 50, 100, 250, 500, 1000]


# ============ KEYBOARDS ============


def bonus_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    """
    Главное меню бонусов с учётом роли.

    Модератор: только просмотр
    Админ: просмотр + начисление
    Старший админ: + отмена своих
    Супер-админ: полный доступ
    """
    buttons = []

    # Все роли могут видеть статистику и историю
    buttons.append(
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="📋 История"),
        ]
    )

    # Админы и выше могут начислять
    if role in ("super_admin", "extended_admin", "admin"):
        buttons.append([KeyboardButton(text="➕ Начислить бонус")])

    # Поиск доступен всем
    buttons.append(
        [
            KeyboardButton(text="🔍 Найти пользователя"),
            KeyboardButton(text="📑 Мои начисления"),
        ]
    )

    # Супер-админ может отменять бонусы
    if role == "super_admin":
        buttons.append([KeyboardButton(text="⚠️ Отмена бонусов")])

    buttons.append([KeyboardButton(text="◀️ Назад в админку")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def amount_quick_select_keyboard() -> ReplyKeyboardMarkup:
    """Быстрый выбор суммы."""
    buttons = [
        [
            KeyboardButton(text="10 USDT"),
            KeyboardButton(text="5 USDT"),
            KeyboardButton(text="50 USDT"),
        ],
        [
            KeyboardButton(text="100 USDT"),
            KeyboardButton(text="30 USDT"),
            KeyboardButton(text="70 USDT"),
        ],
        [KeyboardButton(text="💵 Ввести сумму вручную")],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def reason_templates_keyboard() -> InlineKeyboardMarkup:
    """Шаблоны причин для быстрого выбора."""
    buttons = []
    for idx, (emoji_name, reason) in enumerate(BONUS_REASON_TEMPLATES):
        # Use index instead of full text to avoid 64-byte callback_data limit
        callback = f"bonus_reason:{idx}" if reason else "bonus_reason:custom"
        buttons.append([InlineKeyboardButton(text=emoji_name, callback_data=callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_bonus_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение начисления."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Начислить", callback_data="bonus_do_grant"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="bonus_edit"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="bonus_cancel_grant")],
        ]
    )


def bonus_details_keyboard(bonus_id: int, can_cancel: bool) -> InlineKeyboardMarkup:
    """Клавиатура деталей бонуса."""
    buttons = []

    if can_cancel:
        buttons.append([InlineKeyboardButton(text="⚠️ Отменить бонус", callback_data=f"bonus_cancel:{bonus_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="bonus_back_to_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка назад."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True,
    )


# ============ HELPERS ============


def get_role_display(role: str) -> str:
    """Получить отображаемое имя роли."""
    return {
        "super_admin": "👑 Босс",
        "extended_admin": "⭐ Старший админ",
        "admin": "👤 Админ",
        "moderator": "👁 Модератор",
    }.get(role, role)


def get_role_permissions(role: str) -> dict:
    """Получить права роли."""
    return {
        "super_admin": {
            "can_grant": True,
            "can_view": True,
            "can_cancel_any": True,
            "can_cancel_own": True,
        },
        "extended_admin": {
            "can_grant": True,
            "can_view": True,
            "can_cancel_any": False,
            "can_cancel_own": True,
        },
        "admin": {
            "can_grant": True,
            "can_view": True,
            "can_cancel_any": False,
            "can_cancel_own": False,
        },
        "moderator": {
            "can_grant": False,
            "can_view": True,
            "can_cancel_any": False,
            "can_cancel_own": False,
        },
    }.get(role, {"can_grant": False, "can_view": False, "can_cancel_any": False, "can_cancel_own": False})


# ============ MAIN MENU ============


@router.message(StateFilter("*"), F.text == "🎁 Бонусы")
async def open_bonus_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Открыть главное меню бонусов."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(BonusStates.menu)

    bonus_service = BonusService(session)
    stats = await bonus_service.get_global_bonus_stats()

    role_display = get_role_display(admin.role)
    permissions = get_role_permissions(admin.role)

    # Формируем подсказку по правам
    perm_text = []
    if permissions["can_grant"]:
        perm_text.append("✅ начисление")
    if permissions["can_cancel_any"]:
        perm_text.append("✅ отмена любых")
    elif permissions["can_cancel_own"]:
        perm_text.append("✅ отмена своих")
    if permissions["can_view"]:
        perm_text.append("✅ просмотр")

    text = (
        f"🎁 **Управление бонусами**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Вы: {role_display}\n"
        f"🔐 Права: {', '.join(perm_text)}\n\n"
        f"📊 **Общая статистика:**\n"
        f"├ 💰 Всего начислено: **{format_usdt(stats.get('total_granted', 0))}** USDT\n"
        f"├ 🟢 Активных: **{stats.get('active_count', 0)}** бонусов\n"
        f"├ 📅 За 24 часа: **{format_usdt(stats.get('last_24h', 0))}** USDT\n"
        f"└ 📋 Всего записей: **{stats.get('total_count', 0)}**\n\n"
        f"_Выберите действие:_"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )


# ============ STATISTICS ============


@router.message(BonusStates.menu, F.text == "📊 Статистика")
async def show_detailed_stats(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Показать детальную статистику."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_service = BonusService(session)
    stats = await bonus_service.get_global_bonus_stats()

    # Получаем недавние бонусы для анализа
    recent = await bonus_service.get_recent_bonuses(limit=50)

    # Считаем по статусам
    active_sum = sum(b.amount for b in recent if get_bonus_status(b) == "active")
    completed_sum = sum(b.amount for b in recent if get_bonus_status(b) == "completed")
    cancelled_sum = sum(b.amount for b in recent if get_bonus_status(b) == "cancelled")

    text = (
        f"📊 **Детальная статистика бонусов**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Общие суммы:**\n"
        f"├ Всего начислено: **{format_usdt(stats.get('total_granted', 0))}** USDT\n"
        f"├ За последние 24ч: **{format_usdt(stats.get('last_24h', 0))}** USDT\n"
        f"└ Всего записей: **{stats.get('total_count', 0)}**\n\n"
        f"📈 **По статусам (последние 50):**\n"
        f"├ 🟢 Активные: **{format_usdt(active_sum)}** USDT\n"
        f"├ ✅ Завершённые: **{format_usdt(completed_sum)}** USDT\n"
        f"└ ❌ Отменённые: **{format_usdt(cancelled_sum)}** USDT\n\n"
        f"ℹ️ _Бонус считается завершённым когда выплачен весь ROI Cap (500%)_"
    )

    await message.answer(text, parse_mode="Markdown")


# ============ HISTORY ============


@router.message(BonusStates.menu, F.text == "📋 История")
async def show_bonus_history(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Показать историю бонусов."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_service = BonusService(session)
    recent = await bonus_service.get_recent_bonuses(limit=15)

    if not recent:
        await message.answer(
            "📋 **История бонусов пуста**\n\nЕщё не было начислено ни одного бонуса.",
            parse_mode="Markdown",
        )
        return

    text = "📋 **Последние 15 бонусов:**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for b in recent:
        # Статус
        status = get_bonus_status_emoji(b)

        # Данные
        admin_name = b.admin.username if b.admin else "система"
        user_name = b.user.username if b.user else f"ID:{b.user_id}"
        safe_user = escape_markdown(user_name) if user_name else str(b.user_id)
        safe_admin = escape_markdown(admin_name) if admin_name else "система"

        # ROI прогресс для активных
        progress = ""
        if get_bonus_status(b) == "active" and hasattr(b, "roi_progress_percent"):
            progress = f" ({b.roi_progress_percent:.0f}%)"

        reason_short = (b.reason or "")[:25]
        if len(b.reason or "") > 25:
            reason_short += "..."

        text += (
            f"{status} **{format_usdt(b.amount)}** → @{safe_user}{progress}\n"
            f"   📝 _{reason_short}_ | 👤 @{safe_admin}\n"
            f"   🆔 `bonus:{b.id}` для просмотра деталей\n\n"
        )

    text += "_Нажмите на ID чтобы увидеть детали бонуса_"

    await message.answer(text, parse_mode="Markdown")


# ============ MY BONUSES ============


@router.message(BonusStates.menu, F.text == "📑 Мои начисления")
async def show_my_bonuses(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Показать бонусы, начисленные этим админом."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_service = BonusService(session)
    recent = await bonus_service.get_recent_bonuses(limit=50)

    # Фильтруем по админу
    my_bonuses = [b for b in recent if b.admin_id == admin.id]

    if not my_bonuses:
        await message.answer(
            "📑 **Ваши начисления**\n\nВы ещё не начислили ни одного бонуса.",
            parse_mode="Markdown",
        )
        return

    # Статистика
    total = sum(b.amount for b in my_bonuses)
    active = [b for b in my_bonuses if get_bonus_status(b) == "active"]

    text = (
        f"📑 **Ваши начисления**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Всего: **{len(my_bonuses)}** бонусов на **{format_usdt(total)}** USDT\n"
        f"🟢 Активных: **{len(active)}**\n\n"
    )

    for b in my_bonuses[:10]:
        status = get_bonus_status_emoji(b)
        user_name = b.user.username if b.user else f"ID:{b.user_id}"
        safe_user = escape_markdown(user_name)

        text += f"{status} **{format_usdt(b.amount)}** → @{safe_user}\n"

    if len(my_bonuses) > 10:
        text += f"\n_...и ещё {len(my_bonuses) - 10} бонусов_"

    await message.answer(text, parse_mode="Markdown")


# ============ GRANT BONUS FLOW ============


@router.message(BonusStates.menu, F.text == "➕ Начислить бонус")
async def start_grant_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать процесс начисления бонуса."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    permissions = get_role_permissions(admin.role)
    if not permissions["can_grant"]:
        await message.answer(
            "❌ **Недостаточно прав**\n\nНачисление бонусов доступно только администраторам.",
            parse_mode="Markdown",
        )
        return

    await state.set_state(BonusStates.grant_user)
    await state.update_data(admin_role=admin.role)

    await message.answer(
        "➕ **Начисление бонуса**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Шаг 1 из 4:** Укажите получателя\n\n"
        "Введите данные пользователя:\n"
        "• `@username` — по юзернейму\n"
        "• `123456789` — по Telegram ID\n"
        "• `ID:42` — по внутреннему ID\n\n"
        "_Или нажмите «Отмена» для возврата_",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(BonusStates.grant_user, F.text != "❌ Отмена")
async def process_grant_user(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать ввод пользователя."""
    logger.info(f"process_grant_user called with text: {message.text}")

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        logger.warning("process_grant_user: admin check failed")
        return

    user_input = message.text.strip() if message.text else ""
    logger.info(f"process_grant_user: user_input='{user_input}'")

    user_service = UserService(session)
    user = None

    # Поиск по разным форматам
    if user_input.startswith("@"):
        user = await user_service.get_by_username(user_input[1:])
    elif user_input.upper().startswith("ID:"):
        try:
            user_id = int(user_input[3:])
            user = await user_service.get_by_id(user_id)
        except ValueError:
            pass
    elif user_input.isdigit():
        user = await user_service.get_by_telegram_id(int(user_input))
    else:
        user = await user_service.get_by_username(user_input)

    if not user:
        await message.answer(
            f"❌ **Пользователь не найден**\n\n"
            f"Не удалось найти: `{escape_markdown(user_input)}`\n\n"
            f"Попробуйте другой формат:\n"
            f"• @username\n"
            f"• Telegram ID (число)\n"
            f"• ID:42 (внутренний ID)",
            parse_mode="Markdown",
        )
        return

    # Получаем статистику пользователя
    bonus_service = BonusService(session)
    user_stats = await bonus_service.get_user_bonus_stats(user.id)

    safe_username = escape_markdown(user.username) if user.username else "не указан"

    await state.update_data(
        target_user_id=user.id,
        target_username=user.username or str(user.telegram_id),
        target_telegram_id=user.telegram_id,
    )

    text = (
        f"✅ **Пользователь найден**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Username: @{safe_username}\n"
        f"🆔 Telegram ID: `{user.telegram_id}`\n"
        f"📊 Внутренний ID: `{user.id}`\n\n"
        f"💰 **Бонусный баланс:** {format_usdt(user_stats['total_bonus_balance'])} USDT\n"
        f"📈 **Заработано ROI:** {format_usdt(user_stats['total_bonus_roi_earned'])} USDT\n"
        f"🟢 **Активных бонусов:** {user_stats['active_bonuses_count']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Шаг 2 из 4:** Выберите сумму бонуса"
    )

    await state.set_state(BonusStates.grant_amount)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=amount_quick_select_keyboard(),
    )


@router.message(BonusStates.grant_amount, F.text != "❌ Отмена")
async def process_grant_amount(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать выбор/ввод суммы."""
    logger.info(f"process_grant_amount called with text: {message.text}")

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        logger.warning("process_grant_amount: admin check failed")
        return

    text_input = message.text.strip() if message.text else ""
    logger.info(f"process_grant_amount: text_input='{text_input}'")

    # Обработка быстрого выбора
    if text_input == "💵 Ввести сумму вручную":
        await message.answer(
            "💵 **Ввод суммы вручную**\n\n"
            "Введите сумму бонуса в USDT:\n"
            "• Минимум: 1 USDT\n"
            "• Максимум: 100,000 USDT\n\n"
            "_Например: `150` или `75.50`_",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return

    # Парсим сумму
    amount_str = text_input.replace("USDT", "").replace(",", ".").strip()
    logger.info(f"process_grant_amount: amount_str='{amount_str}'")

    try:
        amount = Decimal(amount_str)
        if amount < 1:
            raise ValueError("Minimum 1 USDT")
        if amount > 100000:
            raise ValueError("Maximum 100000 USDT")
    except (InvalidOperation, ValueError) as e:
        logger.warning(f"process_grant_amount: invalid amount '{amount_str}': {e}")
        await message.answer(
            "❌ **Неверная сумма**\n\nВведите число от 1 до 100,000\n_Например: `100` или `50.5`_",
            parse_mode="Markdown",
        )
        return

    logger.info(f"process_grant_amount: amount={amount}")
    await state.update_data(amount=str(amount))

    roi_cap = amount * 5  # 500%

    await state.set_state(BonusStates.grant_reason)
    await message.answer(
        f"💰 **Сумма:** {format_usdt(amount)} USDT\n"
        f"🎯 **ROI Cap (500%):** {format_usdt(roi_cap)} USDT\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Шаг 3 из 4:** Выберите причину начисления\n\n"
        f"_Нажмите на шаблон или введите свою причину:_",
        parse_mode="Markdown",
        reply_markup=reason_templates_keyboard(),
    )


@router.callback_query(BonusStates.grant_reason, F.data.startswith("bonus_reason:"))
async def process_reason_template(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать выбор шаблона причины."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    reason_data = callback.data.split(":", 1)[1]

    if reason_data == "custom":
        await callback.message.answer(
            "📝 **Введите причину вручную:**\n\n_Минимум 5 символов, максимум 200_",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        await callback.answer()
        return

    # Get reason text from index
    try:
        reason_idx = int(reason_data)
        if 0 <= reason_idx < len(BONUS_REASON_TEMPLATES):
            _, reason_text = BONUS_REASON_TEMPLATES[reason_idx]
            if reason_text:
                await state.update_data(reason=reason_text)
                await show_grant_confirmation(callback.message, state, admin)
                await callback.answer()
                return
    except ValueError:
        pass

    # Fallback: use raw data as reason (backward compatibility)
    await state.update_data(reason=reason_data)
    await show_grant_confirmation(callback.message, state, admin)
    await callback.answer()


@router.message(BonusStates.grant_reason, F.text != "❌ Отмена")
async def process_custom_reason(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать ввод причины вручную."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    reason = message.text.strip()

    if len(reason) < 5:
        await message.answer("❌ Причина слишком короткая. Минимум 5 символов.")
        return

    if len(reason) > 200:
        await message.answer("❌ Причина слишком длинная. Максимум 200 символов.")
        return

    await state.update_data(reason=reason)
    await show_grant_confirmation(message, state, admin)


async def show_grant_confirmation(target, state: FSMContext, admin) -> None:
    """Показать подтверждение начисления."""
    state_data = await state.get_data()

    amount = Decimal(state_data["amount"])
    roi_cap = amount * 5
    safe_username = escape_markdown(state_data.get("target_username", ""))

    text = (
        f"🎁 **Подтверждение начисления**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Шаг 4 из 4:** Проверьте данные\n\n"
        f"👤 **Получатель:** @{safe_username}\n"
        f"🆔 **Telegram ID:** `{state_data['target_telegram_id']}`\n\n"
        f"💰 **Сумма бонуса:** {format_usdt(amount)} USDT\n"
        f"🎯 **ROI Cap (500%):** {format_usdt(roi_cap)} USDT\n\n"
        f"📝 **Причина:** _{escape_markdown(state_data['reason'])}_\n\n"
        f"👤 **Админ:** @{escape_markdown(admin.username or str(admin.telegram_id))}\n\n"
        f"⚠️ **Подтвердите начисление бонуса**"
    )

    await state.set_state(BonusStates.grant_confirm)

    # Check if target is a callback message that can be edited
    # For regular messages, always use answer()
    if hasattr(target, "message") and target.message:
        # This is a CallbackQuery - edit the message
        await target.message.edit_text(text, parse_mode="Markdown", reply_markup=confirm_bonus_keyboard())
    elif hasattr(target, "edit_text") and target.from_user and target.from_user.is_bot:
        # This is a bot message - can be edited
        await target.edit_text(text, parse_mode="Markdown", reply_markup=confirm_bonus_keyboard())
    else:
        # Regular user message - send new message
        await target.answer(text, parse_mode="Markdown", reply_markup=confirm_bonus_keyboard())


@router.callback_query(BonusStates.grant_confirm, F.data == "bonus_do_grant")
async def execute_grant_bonus(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Выполнить начисление бонуса."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    state_data = await state.get_data()

    user_id = state_data["target_user_id"]
    amount = Decimal(state_data["amount"])
    reason = state_data["reason"]

    bonus_service = BonusService(session)
    bonus, error = await bonus_service.grant_bonus(
        user_id=user_id,
        amount=amount,
        reason=reason,
        admin_id=admin.id,
    )

    if error:
        await callback.message.edit_text(f"❌ **Ошибка:** {error}", parse_mode="Markdown")
        await callback.answer("Ошибка!", show_alert=True)
        return

    await session.commit()

    safe_username = escape_markdown(state_data.get("target_username", ""))
    roi_cap = amount * 5

    text = (
        f"✅ **Бонус успешно начислен!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Получатель: @{safe_username}\n"
        f"💰 Сумма: **{format_usdt(amount)} USDT**\n"
        f"🎯 ROI Cap: **{format_usdt(roi_cap)} USDT**\n"
        f"📝 Причина: {reason}\n\n"
        f"🆔 ID бонуса: `{bonus.id}`\n\n"
        f"ℹ️ _Бонус начнёт участвовать в начислении ROI со следующего расчётного периода._"
    )

    await state.set_state(BonusStates.menu)
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.answer(
        "Выберите следующее действие:",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )

    logger.info(
        f"Admin {admin.telegram_id} (@{admin.username}) granted bonus {amount} USDT to user {user_id}: {reason}"
    )

    await callback.answer("✅ Бонус начислен!")


@router.callback_query(BonusStates.grant_confirm, F.data == "bonus_edit")
async def edit_grant_data(
    callback: CallbackQuery,
    state: FSMContext,
    **data: Any,
) -> None:
    """Вернуться к редактированию."""
    await state.set_state(BonusStates.grant_user)
    await callback.message.edit_text(
        "✏️ **Редактирование**\n\nНачните заново — введите @username или Telegram ID пользователя:",
        parse_mode="Markdown",
    )
    await callback.message.answer(
        "Введите данные пользователя:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(BonusStates.grant_confirm, F.data == "bonus_cancel_grant")
async def cancel_grant(
    callback: CallbackQuery,
    state: FSMContext,
    **data: Any,
) -> None:
    """Отменить начисление."""
    admin_role = (await state.get_data()).get("admin_role", "admin")
    await state.set_state(BonusStates.menu)
    await callback.message.edit_text("❌ Начисление бонуса отменено.")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=bonus_main_menu_keyboard(admin_role),
    )
    await callback.answer()


# ============ SEARCH USER ============


@router.message(BonusStates.menu, F.text == "🔍 Найти пользователя")
async def start_search_user(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать поиск бонусов пользователя."""
    await state.set_state(BonusStates.search_user)

    await message.answer(
        "🔍 **Поиск бонусов пользователя**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Введите @username или Telegram ID пользователя:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(BonusStates.search_user, F.text != "❌ Отмена")
async def process_search_user(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Показать бонусы найденного пользователя."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    user_input = message.text.strip()
    user_service = UserService(session)
    user = None

    if user_input.startswith("@"):
        user = await user_service.get_by_username(user_input[1:])
    elif user_input.isdigit():
        user = await user_service.get_by_telegram_id(int(user_input))
    else:
        user = await user_service.get_by_username(user_input)

    if not user:
        await message.answer(
            f"❌ Пользователь `{escape_markdown(user_input)}` не найден.",
            parse_mode="Markdown",
        )
        return

    bonus_service = BonusService(session)
    user_stats = await bonus_service.get_user_bonus_stats(user.id)

    safe_username = escape_markdown(user.username) if user.username else str(user.telegram_id)

    text = (
        f"👤 **Бонусы пользователя @{safe_username}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Бонусный баланс: **{format_usdt(user_stats['total_bonus_balance'])} USDT**\n"
        f"📈 Заработано ROI: **{format_usdt(user_stats['total_bonus_roi_earned'])} USDT**\n"
        f"🟢 Активных: **{user_stats['active_bonuses_count']}**\n"
        f"📋 Всего: **{user_stats['total_bonuses_count']}**\n\n"
    )

    if user_stats.get("active_bonuses"):
        text += "**Активные бонусы:**\n"
        for bonus in user_stats["active_bonuses"][:5]:
            progress = bonus.roi_progress_percent if hasattr(bonus, "roi_progress_percent") else 0
            text += f"• ID `{bonus.id}`: {format_usdt(bonus.amount)} USDT (ROI: {progress:.0f}%)\n"

    await state.set_state(BonusStates.menu)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )


# ============ CANCEL HANDLERS ============


@router.message(BonusStates.grant_user, F.text == "❌ Отмена")
@router.message(BonusStates.grant_amount, F.text == "❌ Отмена")
@router.message(BonusStates.grant_reason, F.text == "❌ Отмена")
@router.message(BonusStates.search_user, F.text == "❌ Отмена")
async def handle_cancel(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать отмену на любом шаге."""
    admin = await get_admin_or_deny(message, session, **data)
    role = admin.role if admin else "admin"

    await state.set_state(BonusStates.menu)
    await message.answer(
        "❌ Операция отменена.",
        reply_markup=bonus_main_menu_keyboard(role),
    )


# ============ BACK TO ADMIN ============


@router.message(BonusStates.menu, F.text == "◀️ Назад в админку")
async def back_to_admin(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Вернуться в админ-панель."""
    from bot.utils.admin_utils import clear_state_preserve_admin_token

    await clear_state_preserve_admin_token(state)
    await message.answer(
        "👑 Возвращаюсь в админ-панель...",
        reply_markup=get_admin_keyboard_from_data(data),
    )


@router.callback_query(F.data == "bonus_back_to_menu")
async def callback_back_to_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Вернуться в меню бонусов."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    role = admin.role if admin else "admin"

    await state.set_state(BonusStates.menu)
    await callback.message.edit_text("◀️ Возврат в меню бонусов...")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=bonus_main_menu_keyboard(role),
    )
    await callback.answer()


# ============ CANCEL BONUS (SUPER ADMIN ONLY) ============


@router.message(BonusStates.menu, F.text == "⚠️ Отмена бонусов")
async def start_cancel_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать процесс отмены бонуса (только супер-админ)."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if admin.role != "super_admin":
        await message.answer(
            "❌ **Недостаточно прав**\n\nОтмена бонусов доступна только супер-администратору.",
            parse_mode="Markdown",
        )
        return

    # Показать активные бонусы для отмены
    bonus_service = BonusService(session)
    recent = await bonus_service.get_recent_bonuses(limit=20)
    active_bonuses = [b for b in recent if get_bonus_status(b) == "active"]

    if not active_bonuses:
        await message.answer(
            "⚠️ **Отмена бонусов**\n\nНет активных бонусов для отмены.",
            parse_mode="Markdown",
        )
        return

    text = "⚠️ **Отмена бонусов**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n**Активные бонусы:**\n\n"

    buttons = []
    for b in active_bonuses[:10]:
        user_name = b.user.username if b.user else f"ID:{b.user_id}"
        safe_user = escape_markdown(user_name)
        progress = b.roi_progress_percent if hasattr(b, "roi_progress_percent") else 0

        text += (
            f"🟢 **ID {b.id}:** {format_usdt(b.amount)} USDT → @{safe_user}\n"
            f"   ROI: {progress:.0f}% | _{(b.reason or '')[:20]}..._\n\n"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"❌ Отменить #{b.id} ({format_usdt(b.amount)})", callback_data=f"bonus_do_cancel:{b.id}"
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="bonus_back_to_menu")])

    text += "\n⚠️ _Выберите бонус для отмены:_"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("bonus_do_cancel:"))
async def confirm_cancel_bonus(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Подтвердить отмену бонуса."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin or admin.role != "super_admin":
        await callback.answer("❌ Только супер-админ", show_alert=True)
        return

    bonus_id = int(callback.data.split(":")[1])

    bonus_service = BonusService(session)
    bonuses = await bonus_service.get_recent_bonuses(limit=100)
    bonus = next((b for b in bonuses if b.id == bonus_id), None)

    if not bonus:
        await callback.answer("❌ Бонус не найден", show_alert=True)
        return

    if get_bonus_status(bonus) != "active":
        await callback.answer("❌ Бонус уже неактивен", show_alert=True)
        return

    await state.update_data(cancel_bonus_id=bonus_id)
    await state.set_state(BonusStates.cancel_reason)

    user_name = bonus.user.username if bonus.user else f"ID:{bonus.user_id}"
    safe_user = escape_markdown(user_name)

    await callback.message.edit_text(
        f"⚠️ **Отмена бонуса #{bonus_id}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Получатель: @{safe_user}\n"
        f"💰 Сумма: **{format_usdt(bonus.amount)} USDT**\n"
        f"📝 Причина начисления: _{escape_markdown(bonus.reason or 'не указана')}_\n\n"
        f"⚠️ **Введите причину отмены:**",
        parse_mode="Markdown",
    )
    await callback.message.answer(
        "Введите причину отмены бонуса:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(BonusStates.cancel_reason, F.text != "❌ Отмена")
async def execute_cancel_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Выполнить отмену бонуса."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin or admin.role != "super_admin":
        await message.answer("❌ Только супер-админ может отменять бонусы")
        return

    cancel_reason = message.text.strip()
    if len(cancel_reason) < 5:
        await message.answer("❌ Причина слишком короткая. Минимум 5 символов.")
        return

    state_data = await state.get_data()
    bonus_id = state_data.get("cancel_bonus_id")

    if not bonus_id:
        await message.answer("❌ ID бонуса не найден. Попробуйте заново.")
        await state.set_state(BonusStates.menu)
        return

    bonus_service = BonusService(session)
    success, error = await bonus_service.cancel_bonus(
        bonus_id=bonus_id,
        admin_id=admin.id,
        reason=cancel_reason,
    )

    if not success:
        await message.answer(f"❌ **Ошибка:** {error}", parse_mode="Markdown")
        await state.set_state(BonusStates.menu)
        await message.answer(
            "Выберите действие:",
            reply_markup=bonus_main_menu_keyboard(admin.role),
        )
        return

    await session.commit()

    await state.set_state(BonusStates.menu)
    await message.answer(
        f"✅ **Бонус #{bonus_id} успешно отменён!**\n\n"
        f"📝 Причина: {cancel_reason}\n"
        f"👤 Отменил: @{escape_markdown(admin.username or str(admin.telegram_id))}",
        parse_mode="Markdown",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )

    logger.info(f"Super admin {admin.telegram_id} cancelled bonus {bonus_id}: {cancel_reason}")


@router.message(BonusStates.cancel_reason, F.text == "❌ Отмена")
async def cancel_cancel_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Отменить процесс отмены бонуса."""
    admin = await get_admin_or_deny(message, session, **data)
    role = admin.role if admin else "super_admin"

    await state.set_state(BonusStates.menu)
    await message.answer(
        "❌ Отмена бонуса прервана.",
        reply_markup=bonus_main_menu_keyboard(role),
    )


# ============ VIEW BONUS DETAILS ============


@router.message(BonusStates.menu, F.text.regexp(r"^bonus:\d+$"))
async def view_bonus_details(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Показать детали бонуса по ID."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    bonus_id = int(message.text.split(":")[1])

    bonus_service = BonusService(session)
    bonuses = await bonus_service.get_recent_bonuses(limit=100)
    bonus = next((b for b in bonuses if b.id == bonus_id), None)

    if not bonus:
        await message.answer(f"❌ Бонус #{bonus_id} не найден.")
        return

    # Статус
    bonus_status = get_bonus_status(bonus)
    status_text = {
        "active": "🟢 Активен",
        "completed": "✅ Завершён (ROI выплачен)",
        "cancelled": "❌ Отменён",
    }.get(bonus_status, bonus_status)

    user_name = bonus.user.username if bonus.user else f"ID:{bonus.user_id}"
    admin_name = bonus.admin.username if bonus.admin else "система"
    safe_user = escape_markdown(user_name)
    safe_admin = escape_markdown(admin_name)

    progress = bonus.roi_progress_percent if hasattr(bonus, "roi_progress_percent") else 0
    remaining = bonus.roi_remaining if hasattr(bonus, "roi_remaining") else bonus.roi_cap_amount

    text = (
        f"🎁 **Бонус #{bonus.id}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Статус:** {status_text}\n\n"
        f"👤 **Получатель:** @{safe_user}\n"
        f"💰 **Сумма:** {format_usdt(bonus.amount)} USDT\n"
        f"🎯 **ROI Cap:** {format_usdt(bonus.roi_cap_amount)} USDT\n"
        f"📈 **ROI выплачено:** {format_usdt(bonus.roi_paid_amount)} USDT ({progress:.1f}%)\n"
        f"💵 **Осталось:** {format_usdt(remaining)} USDT\n\n"
        f"📝 **Причина:** _{escape_markdown(bonus.reason or 'не указана')}_\n"
        f"👤 **Начислил:** @{safe_admin}\n"
        f"📅 **Дата:** {bonus.created_at.strftime('%d.%m.%Y %H:%M') if bonus.created_at else 'н/д'}"
    )

    # Кнопка отмены только для супер-админа и активных бонусов
    can_cancel = admin.role == "super_admin" and get_bonus_status(bonus) == "active"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=bonus_details_keyboard(bonus.id, can_cancel),
    )


@router.callback_query(F.data.startswith("bonus_cancel:"))
async def callback_start_cancel(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать отмену бонуса через callback."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin or admin.role != "super_admin":
        await callback.answer("❌ Только супер-админ", show_alert=True)
        return

    bonus_id = int(callback.data.split(":")[1])
    await state.update_data(cancel_bonus_id=bonus_id)
    await state.set_state(BonusStates.cancel_reason)

    await callback.message.edit_text(
        f"⚠️ **Отмена бонуса #{bonus_id}**\n\nВведите причину отмены:",
        parse_mode="Markdown",
    )
    await callback.message.answer(
        "Введите причину отмены:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()
