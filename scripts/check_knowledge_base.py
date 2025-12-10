#!/usr/bin/env python3
"""Check knowledge base entries."""

import asyncio
import os
import sys


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def check_knowledge_base():
    """Check last entries in knowledge base."""
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://bot:bot_password@postgres:5432/bot")

    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if table exists
        result = await session.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'knowledge_base'
            )
        """)
        )
        exists = result.scalar()

        if not exists:
            print("❌ Table 'knowledge_base' does not exist!")
            return

        # Get count
        result = await session.execute(text("SELECT COUNT(*) FROM knowledge_base"))
        count = result.scalar()
        print(f"📊 Total entries in knowledge_base: {count}")

        # Get last 10 entries
        result = await session.execute(
            text("""
            SELECT id, question, LEFT(answer, 200) as answer_preview, created_at
            FROM knowledge_base
            ORDER BY created_at DESC
            LIMIT 10
        """)
        )
        rows = result.fetchall()

        print("\n📚 Last 10 entries:")
        print("-" * 80)
        for row in rows:
            print(f"ID: {row[0]} | Created: {row[3]}")
            print(f"Q: {row[1][:100]}...")
            print(f"A: {row[2]}...")
            print("-" * 80)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_knowledge_base())
