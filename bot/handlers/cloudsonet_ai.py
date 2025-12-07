"""
CloudSonet 4.5 AI Assistant Handler
=====================================
Обработчик команд для взаимодействия админов с AI-ассистентом CloudSonet 4.5.

Команды:
    /ai <сообщение> - Отправить сообщение CloudSonet 4.5
    /ai status - Запросить статус системы
    /ai help - Справка по командам
"""
import json
from datetime import datetime
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="cloudsonet_ai")

# Файл для хранения сообщений от админов
MESSAGES_FILE = Path("/app/logs/cloudsonet_inbox.json")

# ID админов
ADMIN_IDS = {5186268007, 1691026253, 6540613027, 241568583}

HELP_TEXT = """🤖 *CloudSonet 4.5 - AI Ассистент*

Я - ваш AI-помощник для мониторинга и разработки бота.

*Доступные команды:*
• `/ai <сообщение>` - Отправить мне сообщение или вопрос
• `/ai status` - Запросить текущий статус системы  
• `/ai help` - Показать эту справку

*Примеры использования:*
• `/ai Проверь логи за последний час`
• `/ai Есть ли ошибки в worker?`
• `/ai Добавь новую функцию X`

Ваши сообщения сохраняются и будут обработаны в порядке очереди.

_CloudSonet 4.5 - кластер AI агентов_"""

STATUS_TEXT = """📊 *Запрос статуса принят*

Ваш запрос на проверку статуса системы зарегистрирован.

CloudSonet 4.5 проведёт анализ:
• Состояние контейнеров
• Логи за последний период
• Ошибки и предупреждения
• Синхронизация блокчейна

Результат будет отправлен в ближайшее время.

_Спасибо за обращение!_"""


def save_message(admin_id: int, admin_name: str, message: str) -> int:
    """Сохранить сообщение от админа."""
    MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    messages = []
    if MESSAGES_FILE.exists():
        try:
            messages = json.loads(MESSAGES_FILE.read_text())
        except Exception:
            messages = []
    
    messages.append({
        "timestamp": datetime.now().isoformat(),
        "admin_id": admin_id,
        "admin_name": admin_name,
        "message": message,
        "read": False,
    })
    
    MESSAGES_FILE.write_text(json.dumps(messages, ensure_ascii=False, indent=2))
    return len([m for m in messages if not m.get("read")])


@router.message(Command("ai"))
async def handle_ai_command(message: Message):
    """Обработка команды /ai для взаимодействия с CloudSonet 4.5."""
    user_id = message.from_user.id
    
    # Проверка что пользователь - админ
    if user_id not in ADMIN_IDS:
        await message.answer(
            "⚠️ Эта команда доступна только администраторам.",
            parse_mode="Markdown"
        )
        return
    
    # Получаем текст после /ai
    text = message.text
    if text.startswith("/ai "):
        text = text[4:].strip()
    elif text == "/ai":
        text = ""
    else:
        text = text.replace("/ai", "").strip()
    
    # Если пустое сообщение - показываем справку
    if not text:
        await message.answer(HELP_TEXT, parse_mode="Markdown")
        return
    
    # Обработка специальных команд
    if text.lower() in ("help", "помощь", "?"):
        await message.answer(HELP_TEXT, parse_mode="Markdown")
        return
    
    if text.lower() in ("status", "статус"):
        save_message(
            user_id,
            message.from_user.full_name or message.from_user.username or str(user_id),
            "[STATUS REQUEST]"
        )
        await message.answer(STATUS_TEXT, parse_mode="Markdown")
        return
    
    # Сохраняем обычное сообщение
    admin_name = message.from_user.full_name or message.from_user.username or str(user_id)
    unread_count = save_message(user_id, admin_name, text)
    
    await message.answer(
        f"✅ *Сообщение принято*\n\n"
        f"Ваше сообщение сохранено и будет обработано CloudSonet 4.5.\n\n"
        f"📬 Всего в очереди: {unread_count} сообщений\n\n"
        f"_Спасибо за обращение!_",
        parse_mode="Markdown"
    )
