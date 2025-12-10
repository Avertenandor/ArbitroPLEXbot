#!/usr/bin/env python3
"""Script to check and generate master key."""
import asyncio
import secrets
import sys

from sqlalchemy import text


sys.path.insert(0, "/app")

from app.config.database import async_session_maker


async def check_master_key():
    """Check and optionally generate master key."""
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT id, telegram_id, username, role, master_key FROM admins")
        )
        admins = result.fetchall()

        for admin in admins:
            print(f"Admin ID: {admin[0]}")
            print(f"Telegram ID: {admin[1]}")
            print(f"Username: {admin[2]}")
            print(f"Role: {admin[3]}")
            print(f"Master Key: {admin[4] or 'NOT SET'}")
            print("-" * 40)

            # If super_admin has no master key, generate one
            if admin[3] == 'super_admin' and not admin[4]:
                new_key = secrets.token_hex(16).upper()
                await session.execute(
                    text("UPDATE admins SET master_key = :key WHERE id = :id"),
                    {"key": new_key, "id": admin[0]}
                )
                await session.commit()
                print(f"🔑 GENERATED NEW MASTER KEY: {new_key}")
                print("⚠️  SAVE THIS KEY! It's required for sensitive operations.")


if __name__ == "__main__":
    asyncio.run(check_master_key())
