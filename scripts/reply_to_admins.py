#!/usr/bin/env python3
"""Send responses to admins from Darya."""

import asyncio
import sys


sys.path.insert(0, "/app")

from aiogram import Bot

from app.config.settings import settings


async def main():
    bot = Bot(token=settings.telegram_bot_token)

    # Reply to Natasha
    try:
        await bot.send_message(
            241568583,
            "Наташа, это Дарья! Получила твои сообщения:\n\n"
            "1. Интервью от Командира - ищу и исправлю\n"
            "2. Кнопка Назад пропадает - это баг, уже работаю!\n\n"
            "Спасибо за обратную связь! 🙏",
        )
        print("✅ Sent to @natder")
    except Exception as e:
        print(f"❌ Failed @natder: {e}")

    # Reply to Commander
    try:
        await bot.send_message(
            1040687384,
            "Командир, связь работает! ✅\n\nКанал «Написать Дарье» настроен. Жду ваших задач и предложений!",
        )
        print("✅ Sent to @VladarevInvestBrok")
    except Exception as e:
        print(f"❌ Failed @VladarevInvestBrok: {e}")

    # Reply to Sasha
    try:
        await bot.send_message(
            1691026253,
            "Саша, отлично! 👍\n\n"
            "ARIA готова задавать вопросы. Используй 🤖 AI Помощник - "
            "ARIA проведет интервью и сохранит ответы в базу знаний.",
        )
        print("✅ Sent to @AI_XAN")
    except Exception as e:
        print(f"❌ Failed @AI_XAN: {e}")

    await bot.session.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
