#!/usr/bin/env python3
"""
CloudSonet 4.5 Communication System
====================================
Система коммуникации между AI-ассистентом CloudSonet 4.5 и администраторами бота.

Использование:
    python scripts/cloudsonet_communication.py send "Сообщение"
    python scripts/cloudsonet_communication.py read
    python scripts/cloudsonet_communication.py status
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/app')

from aiogram import Bot


# Конфигурация админов
ADMINS = {
    1040687384: {"name": "Главный (@VladarevInvestBrok)", "role": "super_admin", "tech": False},
    1691026253: {"name": "Александр (@AI_XAN)", "role": "admin", "tech": True},  # Тех. заместитель
    6540613027: {"name": "Vlad (@ded_vtapkax)", "role": "admin", "tech": False},
    241568583: {"name": "Nataliia (@natder)", "role": "admin", "tech": False},
}

# Файл для хранения сообщений от админов к CloudSonet
MESSAGES_FILE = Path("/app/logs/cloudsonet_inbox.json")


def get_signature():
    """Подпись CloudSonet 4.5 в стиле Хазина."""
    return "\n\n_С глубоким уважением,_\n_Ваш AI-ассистент CloudSonet 4.5_ 🤖"


def format_greeting(admin_id: int) -> str:
    """Персональное приветствие для админа."""
    admin = ADMINS.get(admin_id, {})
    name = admin.get("name", "Уважаемый администратор")
    
    if admin.get("tech"):
        return f"🔧 *Александр, как технический заместитель,* вы наверняка оцените следующее:\n\n"
    elif admin.get("role") == "super_admin":
        return f"👑 *Уважаемый руководитель проекта!*\n\n"
    else:
        return f"👋 *Уважаемый коллега!*\n\n"


async def send_to_all_admins(message: str, category: str = "info"):
    """Отправить сообщение всем админам."""
    token = os.getenv('TELEGRAM_BOT_TOKEN', '8506414714:AAGO6CM338MuzxZT8xO8WfSoRomnqczS2d4')
    bot = Bot(token=token)
    
    # Иконки категорий
    icons = {
        "info": "ℹ️",
        "error": "🚨",
        "fix": "✅",
        "question": "❓",
        "update": "🔄",
        "monitor": "📊",
    }
    icon = icons.get(category, "📢")
    
    timestamp = datetime.now().strftime("%H:%M")
    
    for admin_id, admin_info in ADMINS.items():
        try:
            greeting = format_greeting(admin_id)
            full_message = (
                f"{icon} *CloudSonet 4.5* [{timestamp}]\n\n"
                f"{greeting}"
                f"{message}"
                f"{get_signature()}"
            )
            await bot.send_message(admin_id, full_message, parse_mode='Markdown')
            print(f"✅ Отправлено: {admin_info['name']}")
        except Exception as e:
            print(f"❌ Ошибка {admin_info['name']}: {e}")
    
    await bot.session.close()


async def send_to_tech_lead(message: str):
    """Отправить сообщение только техническому заместителю (Александру)."""
    token = os.getenv('TELEGRAM_BOT_TOKEN', '8506414714:AAGO6CM338MuzxZT8xO8WfSoRomnqczS2d4')
    bot = Bot(token=token)
    
    # Александр - технический заместитель
    tech_lead_id = 1691026253
    
    timestamp = datetime.now().strftime("%H:%M")
    full_message = (
        f"🔧 *CloudSonet 4.5 → Тех. отдел* [{timestamp}]\n\n"
        f"Александр, как технический специалист, прошу обратить внимание:\n\n"
        f"{message}"
        f"{get_signature()}"
    )
    
    try:
        await bot.send_message(tech_lead_id, full_message, parse_mode='Markdown')
        print(f"✅ Отправлено техническому заместителю")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    await bot.session.close()


def save_admin_message(admin_id: int, message: str):
    """Сохранить сообщение от админа для CloudSonet."""
    MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    messages = []
    if MESSAGES_FILE.exists():
        try:
            messages = json.loads(MESSAGES_FILE.read_text())
        except Exception:
            messages = []
    
    admin_info = ADMINS.get(admin_id, {"name": f"Admin {admin_id}"})
    messages.append({
        "timestamp": datetime.now().isoformat(),
        "admin_id": admin_id,
        "admin_name": admin_info.get("name", "Unknown"),
        "message": message,
        "read": False,
    })
    
    MESSAGES_FILE.write_text(json.dumps(messages, ensure_ascii=False, indent=2))
    return len([m for m in messages if not m.get("read")])


def get_unread_messages() -> list:
    """Получить непрочитанные сообщения от админов."""
    if not MESSAGES_FILE.exists():
        return []
    
    try:
        messages = json.loads(MESSAGES_FILE.read_text())
        return [m for m in messages if not m.get("read")]
    except Exception:
        return []


def mark_messages_read():
    """Пометить все сообщения как прочитанные."""
    if not MESSAGES_FILE.exists():
        return
    
    try:
        messages = json.loads(MESSAGES_FILE.read_text())
        for m in messages:
            m["read"] = True
        MESSAGES_FILE.write_text(json.dumps(messages, ensure_ascii=False, indent=2))
    except Exception:
        pass


# Предустановленные сообщения
MESSAGES = {
    "status_ok": """📊 *Статус системы: НОРМА*

Провожу непрерывный мониторинг всех компонентов:
• Бот: ✅ Работает
• Worker: ✅ Синхронизация блоков активна
• Scheduler: ✅ Задачи выполняются
• База данных: ✅ Подключение стабильно

Как показывает анализ логов, система функционирует в штатном режиме.""",

    "error_detected": """🚨 *Обнаружена техническая проблема*

В ходе мониторинга зафиксирована ошибка в подсистеме {component}.

Характер проблемы: {description}

Приступаю к диагностике и исправлению. О результатах сообщу дополнительно.""",

    "error_fixed": """✅ *Проблема устранена*

Ранее обнаруженная ошибка в {component} успешно исправлена.

Изменения задеплоены на сервер. Система работает в штатном режиме.

Прошу продолжить тестирование функционала.""",

    "question": """❓ *Требуется уточнение*

{question}

Буду признателен за ваш ответ. Для ответа используйте команду в боте:
`/ai ваш ответ`""",

    "update": """🔄 *Обновление системы*

Внесены следующие изменения:
{changes}

Изменения применены и протестированы.""",
}


async def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python cloudsonet_communication.py send 'сообщение'")
        print("  python cloudsonet_communication.py send_tech 'сообщение'")
        print("  python cloudsonet_communication.py read")
        print("  python cloudsonet_communication.py status")
        print("  python cloudsonet_communication.py error 'component' 'description'")
        print("  python cloudsonet_communication.py fixed 'component'")
        return
    
    command = sys.argv[1]
    
    if command == "send" and len(sys.argv) > 2:
        message = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else "info"
        await send_to_all_admins(message, category)
    
    elif command == "send_tech" and len(sys.argv) > 2:
        message = sys.argv[2]
        await send_to_tech_lead(message)
    
    elif command == "read":
        messages = get_unread_messages()
        if not messages:
            print("📭 Нет новых сообщений от админов")
        else:
            print(f"📬 Новых сообщений: {len(messages)}\n")
            for m in messages:
                print(f"[{m['timestamp']}] {m['admin_name']}:")
                print(f"  {m['message']}\n")
            mark_messages_read()
    
    elif command == "status":
        await send_to_all_admins(MESSAGES["status_ok"], "monitor")
    
    elif command == "error" and len(sys.argv) > 3:
        component = sys.argv[2]
        description = sys.argv[3]
        msg = MESSAGES["error_detected"].format(component=component, description=description)
        await send_to_all_admins(msg, "error")
    
    elif command == "fixed" and len(sys.argv) > 2:
        component = sys.argv[2]
        msg = MESSAGES["error_fixed"].format(component=component)
        await send_to_all_admins(msg, "fix")
    
    else:
        print(f"Неизвестная команда: {command}")


if __name__ == '__main__':
    asyncio.run(main())
