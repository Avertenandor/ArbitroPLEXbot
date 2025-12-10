#!/usr/bin/env python3
"""Script to add or update super admin."""
import asyncio
import sys

from sqlalchemy import text


# Add parent directory to path
sys.path.insert(0, "/app")

from app.config.database import async_session_maker


async def update_super_admin():
    """Update super admin telegram_id."""
    async with async_session_maker() as session:
        # First check current admins
        result = await session.execute(text("SELECT * FROM admins"))
        admins = result.fetchall()
        print(f"Current admins: {admins}")

        # Delete the fake admin with wrong ID
        await session.execute(
            text("DELETE FROM admins WHERE telegram_id = 1234567890")
        )
        await session.commit()

        # Verify
        result = await session.execute(text("SELECT * FROM admins"))
        admins = result.fetchall()
        print(f"Updated admins: {admins}")
        print("Fake admin removed! You are now the only super admin.")


if __name__ == "__main__":
    asyncio.run(update_super_admin())
