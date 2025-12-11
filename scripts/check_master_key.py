#!/usr/bin/env python3
"""Script to check and generate master key.

SECURITY NOTE: This script properly hashes master keys using bcrypt
before storing them. The plain text key is shown ONCE during generation
and must be saved immediately.
"""
import asyncio
import secrets
import sys

import bcrypt
from sqlalchemy import text


sys.path.insert(0, "/app")

from app.config.database import async_session_maker


def hash_master_key(plain_key: str) -> str:
    """Hash master key using bcrypt for secure storage."""
    return bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()


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
            # SECURITY: Do not print actual master key hash
            has_key = "SET (hashed)" if admin[4] else "NOT SET"
            print(f"Master Key: {has_key}")
            print("-" * 40)

            # If super_admin has no master key, generate one
            if admin[3] == 'super_admin' and not admin[4]:
                # Generate secure random key
                plain_key = secrets.token_hex(32)  # 256-bit key
                # Hash before storing
                hashed_key = hash_master_key(plain_key)

                await session.execute(
                    text("UPDATE admins SET master_key = :key WHERE id = :id"),
                    {"key": hashed_key, "id": admin[0]}
                )
                await session.commit()

                # SECURITY: Show key only once, then clear from output
                print("\n" + "=" * 60)
                print("🔐 MASTER KEY GENERATED (SHOWN ONLY ONCE!)")
                print("=" * 60)
                print(f"\nAdmin ID: {admin[0]}")
                print(f"Username: @{admin[2] or 'N/A'}")
                print("\n⚠️ SAVE THIS KEY IMMEDIATELY - IT CANNOT BE RECOVERED!")
                print("-" * 60)
                # Note: In production, consider writing to a secure file instead
                print(f"\n{plain_key}\n")
                print("-" * 60)
                print("\n✅ Key has been hashed and stored securely.")
                print("⚠️ The plain key above will NOT be shown again!")
                print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(check_master_key())
