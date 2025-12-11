#!/usr/bin/env python3
"""Send notification to all admins about new Darya button."""

import asyncio
import sys

sys.path.insert(0, "/app")

from aiogram import Bot

from app.config.settings import settings


ADMIN_IDS = [1040687384, 241568583, 6540613027, 1691026253]

MESSAGE = """🆕 Новая функция!

В админ-панели появилась кнопка:
💬 Написать Дарье

Дарья — ИИ-разработчик бота (Copilot/Claude).

Через эту кнопку можно:
• Сообщить о багах
• Предложить новые функции
• Попросить улучшения
• Задать технические вопросы

Дарья читает сообщения во время сессий разработки и оперативно вносит изменения.

Зайдите в админ-панель и попробуйте! 🚀"""


async def main():
    bot = Bot(token=settings.telegram_bot_token)
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, MESSAGE)
            print(f"✅ Sent to {admin_id}")
        except Exception as e:
            print(f"❌ Failed {admin_id}: {e}")
    
    await bot.session.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
