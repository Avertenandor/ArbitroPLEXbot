#!/usr/bin/env python3
"""
Dev Chat CLI - Send messages to admins directly from Copilot.

Usage:
    python scripts/dev_chat.py send @username "Your message here"
    python scripts/dev_chat.py broadcast "Message to all admins"
    python scripts/dev_chat.py read  # Read admin responses
    python scripts/dev_chat.py log   # View conversation log
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime


# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis.asyncio as redis
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.services.dev_chat_service import DevChatService


async def get_redis_client():
    """Get Redis client."""
    # Build Redis URL from settings
    if settings.redis_password:
        redis_url = (
            f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        )
    else:
        redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    return redis.from_url(redis_url)


async def get_db_session():
    """Get database session."""
    engine = create_async_engine(str(settings.database_url))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


async def send_message(admin: str, message: str, sender: str = "Copilot"):
    """Send a message to specific admin."""
    bot = Bot(token=settings.telegram_bot_token)
    redis_client = await get_redis_client()
    session = await get_db_session()

    try:
        service = DevChatService(session, bot, redis_client)
        result = await service.send_dev_message(
            admin_identifier=admin,
            message=message,
            sender=sender,
        )

        if result.get("success"):
            print(f"✅ Message queued for {result.get('to')}")

            # Process outbox immediately
            sent = await service.process_outbox()
            if sent > 0:
                print(f"📤 Sent {sent} message(s)")
        else:
            print(f"❌ Error: {result.get('error')}")

    finally:
        await session.close()
        await redis_client.close()
        await bot.session.close()


async def broadcast_message(message: str, sender: str = "Copilot"):
    """Broadcast message to all admins."""
    bot = Bot(token=settings.telegram_bot_token)
    redis_client = await get_redis_client()
    session = await get_db_session()

    try:
        service = DevChatService(session, bot, redis_client)
        result = await service.broadcast_to_all_admins(
            message=message,
            sender=sender,
        )

        if result.get("success"):
            print(f"✅ Queued for {result.get('queued')}/{result.get('total_admins')} admins")

            # Process outbox
            sent = await service.process_outbox()
            print(f"📤 Sent {sent} message(s)")
        else:
            print(f"❌ Error: {result.get('error')}")

    finally:
        await session.close()
        await redis_client.close()
        await bot.session.close()


async def read_responses():
    """Read unread responses from admins."""
    redis_client = await get_redis_client()
    session = await get_db_session()
    bot = Bot(token=settings.telegram_bot_token)

    try:
        service = DevChatService(session, bot, redis_client)
        responses = await service.get_unread_responses()

        if not responses:
            print("📭 No unread responses")
            return

        print(f"📬 {len(responses)} unread response(s):\n")

        for resp in responses:
            print(f"From: @{resp.get('from_username')} ({resp.get('received_at')})")
            print(f"Message: {resp.get('message')}")
            print("-" * 50)

    finally:
        await session.close()
        await redis_client.close()
        await bot.session.close()


async def view_log(limit: int = 20):
    """View conversation log."""
    redis_client = await get_redis_client()
    session = await get_db_session()
    bot = Bot(token=settings.telegram_bot_token)

    try:
        service = DevChatService(session, bot, redis_client)
        log = await service.get_conversation_log(limit=limit)

        if not log:
            print("📋 No conversation log")
            return

        print(f"📋 Last {len(log)} entries:\n")

        for entry in reversed(log):  # Show oldest first
            direction = "→" if entry.get("direction") == "outgoing" else "←"
            if entry.get("direction") == "outgoing":
                print(f"{direction} To @{entry.get('to_username')}: {entry.get('message')[:100]}...")
            else:
                print(f"{direction} From @{entry.get('from_username')}: {entry.get('message')[:100]}...")

    finally:
        await session.close()
        await redis_client.close()
        await bot.session.close()


def main():
    parser = argparse.ArgumentParser(description="Dev Chat CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Send command
    send_parser = subparsers.add_parser("send", help="Send message to admin")
    send_parser.add_argument("admin", help="@username or telegram_id")
    send_parser.add_argument("message", help="Message text")
    send_parser.add_argument("--sender", default="Copilot", help="Sender name")

    # Broadcast command
    broadcast_parser = subparsers.add_parser("broadcast", help="Send to all admins")
    broadcast_parser.add_argument("message", help="Message text")
    broadcast_parser.add_argument("--sender", default="Copilot", help="Sender name")

    # Read command
    subparsers.add_parser("read", help="Read admin responses")

    # Log command
    log_parser = subparsers.add_parser("log", help="View conversation log")
    log_parser.add_argument("--limit", type=int, default=20, help="Number of entries")

    args = parser.parse_args()

    if args.command == "send":
        asyncio.run(send_message(args.admin, args.message, args.sender))
    elif args.command == "broadcast":
        asyncio.run(broadcast_message(args.message, args.sender))
    elif args.command == "read":
        asyncio.run(read_responses())
    elif args.command == "log":
        asyncio.run(view_log(args.limit))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
