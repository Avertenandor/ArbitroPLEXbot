#!/usr/bin/env python3
"""
Simple Dev Chat - Send messages directly without DB dependency.

Usage:
    python scripts/dev_chat_simple.py send <telegram_id> "message"
    python scripts/dev_chat_simple.py broadcast "message"
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot

from app.config.settings import settings


# Known admin telegram IDs
ADMIN_IDS = {
    1040687384: "VladarevInvestBrok",  # Командир
    241568583: "natder",  # Наташа
    6540613027: "ded_vtapkax",  # Влад
    1691026253: "AI_XAN",  # Саша
}


async def send_message(telegram_id: int, message: str, sender: str = "Copilot"):
    """Send a message to specific admin."""
    bot = Bot(token=settings.telegram_bot_token)

    try:
        formatted_msg = (
            f"💬 **Сообщение от разработчика ({sender})**\n\n"
            f"{message}\n\n"
            f"_Ответьте командой /dev\\_reply <ваш ответ> или через 🤖 AI Помощник._"
        )

        await bot.send_message(
            telegram_id,
            formatted_msg,
            parse_mode="Markdown",
        )
        print(f"✅ Отправлено {ADMIN_IDS.get(telegram_id, telegram_id)}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()


async def broadcast_message(message: str, sender: str = "Copilot"):
    """Broadcast message to all admins."""
    bot = Bot(token=settings.telegram_bot_token)

    try:
        formatted_msg = (
            f"💬 **Сообщение от разработчика ({sender})**\n\n"
            f"{message}\n\n"
            f"_Ответьте командой /dev\\_reply <ваш ответ> или через 🤖 AI Помощник._"
        )

        sent = 0
        for tid, username in ADMIN_IDS.items():
            try:
                await bot.send_message(tid, formatted_msg, parse_mode="Markdown")
                print(f"✅ Отправлено @{username}")
                sent += 1
                await asyncio.sleep(0.2)
            except Exception as e:
                print(f"❌ @{username}: {e}")

        print(f"\n📤 Отправлено {sent}/{len(ADMIN_IDS)} админам")

    finally:
        await bot.session.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Simple Dev Chat")
    subparsers = parser.add_subparsers(dest="command")

    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("telegram_id", type=int)
    send_parser.add_argument("message")
    send_parser.add_argument("--sender", default="Copilot")

    broadcast_parser = subparsers.add_parser("broadcast")
    broadcast_parser.add_argument("message")
    broadcast_parser.add_argument("--sender", default="Copilot")

    args = parser.parse_args()

    if args.command == "send":
        asyncio.run(send_message(args.telegram_id, args.message, args.sender))
    elif args.command == "broadcast":
        asyncio.run(broadcast_message(args.message, args.sender))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
