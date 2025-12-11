#!/usr/bin/env python3
"""Read messages from admins (Darya's inbox)."""

import asyncio
import json
import sys


sys.path.insert(0, "/app")

import redis.asyncio as r

from app.config.settings import settings


async def main():
    # Build Redis URL
    if settings.redis_password:
        redis_url = (
            f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        )
    else:
        redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

    client = await r.from_url(redis_url)

    # Read inbox
    msgs = await client.lrange("dev_chat:inbox", 0, 50)

    if not msgs:
        print("📭 Нет новых сообщений")
    else:
        print(f"📬 {len(msgs)} сообщение(й) от админов:\n")
        for m in msgs:
            try:
                data = json.loads(m.decode())
                print(f"От: @{data.get('from_username')}")
                print(f"Время: {data.get('received_at')}")
                print(f"Сообщение: {data.get('message')}")
                print("-" * 50)
            except Exception as e:
                print(f"Error parsing: {e}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
