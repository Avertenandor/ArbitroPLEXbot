"""
Admin Messages Module
Contains message templates and formatting functions for admin operations
"""

from typing import Any

# Admin Panel Messages
ADMIN_PANEL_WELCOME = """
👑 **Панель администратора**

Добро пожаловать в панель управления ArbitroPLEXbot Bot.

Выберите действие:
""".strip()

ADMIN_NOT_FOUND = "❌ Администратор не найден"

ADMIN_ACCESS_DENIED = "❌ Эта функция доступна только администраторам"

# User Management Messages
USER_NOT_FOUND = "❌ Пользователь не найден"

USER_BLOCKED_SUCCESS = "✅ Пользователь заблокирован"

USER_UNBLOCKED_SUCCESS = "✅ Пользователь разблокирован"

# Operation Messages
OPERATION_CANCELLED = "❌ Операция отменена"

# Button Labels
BACK_TO_PANEL_BUTTON = "◀️ Назад в админ-панель"

CANCEL_BUTTON = "❌ Отмена"


def format_user_profile(user: Any, stats: dict[str, Any]) -> str:
    """
    Format user profile information for admin display.

    Args:
        user: User model instance
        stats: Dictionary containing user statistics
            - total_balance: User's total balance
            - total_deposits: Total deposits amount
            - total_withdrawals: Total withdrawals amount
            - total_earnings: Total earnings amount
            - referral_count: Number of referrals
            - transaction_count: Number of transactions

    Returns:
        Formatted markdown string with user profile information
    """
    # Status indicators
    status_emoji = "🚫" if user.is_banned else "✅"
    status_text = "Заблокирован" if user.is_banned else "Активен"

    # Username display
    username_display = f"@{user.username}" if user.username else "Не указан"

    # Verification status
    verification_status = "✅ Да" if user.is_verified else "❌ Нет"

    # Financial password status
    fin_pass_status = "🔑 Установлен" if user.financial_password else "❌ Не установлен"

    # Contact information
    phone = user.phone if user.phone else "Не указан"
    email = user.email if user.email else "Не указан"
    wallet = f"`{user.wallet_address}`" if user.wallet_address else "Не указан"

    # Activity timestamps
    created_at = user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else "Неизвестно"
    last_active = user.last_active.strftime('%d.%m.%Y %H:%M') if user.last_active else "Неизвестно"

    # Special flags
    flags = []
    if user.is_admin:
        flags.append("👑 Админ")
    if hasattr(user, 'earnings_blocked') and user.earnings_blocked:
        flags.append("⛔️ Начисления заблокированы")
    if hasattr(user, 'withdrawal_blocked') and user.withdrawal_blocked:
        flags.append("⛔️ Вывод заблокирован")
    if hasattr(user, 'suspicious') and user.suspicious:
        flags.append("⚠️ Подозрительный")
    flags_text = ", ".join(flags) if flags else "Нет особых отметок"

    # Build profile text
    text = (
        f"👤 **Личное дело пользователя**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{user.id}`\n"
        f"📱 Telegram ID: `{user.telegram_id}`\n"
        f"👤 Username: {username_display}\n"
        f"📅 Регистрация: {created_at}\n"
        f"🕒 Последняя активность: {last_active}\n"
        f"📊 Статус: {status_emoji} **{status_text}**\n"
        f"✅ Верификация: {verification_status}\n"
        f"🏷 Язык: {user.language or 'ru'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔐 **Безопасность:**\n"
        f"• Фин. пароль: {fin_pass_status}\n"
        f"• Особые отметки: {flags_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📞 **Контакты:**\n"
        f"• Телефон: {phone}\n"
        f"• Email: {email}\n"
        f"• Кошелек: {wallet}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Финансы:**\n"
        f"• Баланс: `{stats.get('total_balance', 0):.2f} USDT`\n"
        f"• Депозиты: `{stats.get('total_deposits', 0):.2f} USDT`\n"
        f"• Выводы: `{stats.get('total_withdrawals', 0):.2f} USDT`\n"
        f"• Заработано: `{stats.get('total_earnings', 0):.2f} USDT`\n"
    )

    # Add deposit info if available
    if hasattr(user, 'total_deposited_usdt'):
        deposit_status = getattr(user, 'deposit_status_text', 'Неизвестен')
        required_plex = int(getattr(user, 'required_daily_plex', 0))
        tx_count = getattr(user, 'deposit_tx_count', 0)
        last_scan = (
            user.last_deposit_scan_at.strftime('%d.%m.%Y %H:%M')
            if hasattr(user, 'last_deposit_scan_at') and user.last_deposit_scan_at
            else 'Не сканировался'
        )

        text += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💎 **Депозит (из блокчейна):**\n"
            f"• Всего внесено: `{user.total_deposited_usdt:.2f} USDT`\n"
            f"• Статус: {deposit_status}\n"
            f"• PLEX в сутки: `{required_plex:,}`\n"
            f"• Транзакций: `{tx_count}`\n"
            f"• Последнее сканирование: {last_scan}\n"
        )

    # Add referral info if available
    if 'referral_count' in stats:
        text += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👥 **Рефералы:**\n"
            f"• Всего приглашено: {stats['referral_count']}\n"
        )

    # Add transaction info if available
    if 'transaction_count' in stats:
        text += f"• Транзакций: {stats['transaction_count']}\n"

    text += "\nВыберите действие:"

    return text


def format_admin_list(admins: list[Any]) -> str:
    """
    Format list of admins for display.

    Args:
        admins: List of Admin model instances

    Returns:
        Formatted markdown string with admin list
    """
    if not admins:
        return "👥 **Список администраторов**\n\n_Нет администраторов в системе_"

    text = "👥 **Список администраторов**\n\n"

    for admin in admins:
        # Role emoji and text
        role_emoji = "👑" if admin.is_super_admin else "⭐" if admin.is_extended_admin else "👤"
        role_text = (
            "Супер-админ" if admin.is_super_admin
            else "Расширенный админ" if admin.is_extended_admin
            else "Админ"
        )

        # Status
        status_emoji = "✅" if admin.is_active else "❌"
        status_text = "Активен" if admin.is_active else "Неактивен"

        # Username
        username = f"@{admin.username}" if admin.username else f"ID {admin.telegram_id}"

        # Last login
        last_login = "Никогда"
        if hasattr(admin, 'last_login_at') and admin.last_login_at:
            last_login = admin.last_login_at.strftime('%d.%m.%Y %H:%M')

        # Created at
        created_at = admin.created_at.strftime('%d.%m.%Y') if admin.created_at else "Неизвестно"

        text += (
            f"{role_emoji} **{username}**\n"
            f"├ Роль: {role_text}\n"
            f"├ Статус: {status_emoji} {status_text}\n"
            f"├ Последний вход: {last_login}\n"
            f"└ Создан: {created_at}\n\n"
        )

    return text.strip()
