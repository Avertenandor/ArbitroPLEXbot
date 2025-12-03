#!/usr/bin/env python3
"""Initialize database tables."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, "/app")

from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base


async def init_database() -> None:
    """Create all database tables."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    print("Connecting to database...")
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        print("Creating tables (checkfirst=True)...")
        await conn.run_sync(
            Base.metadata.create_all,
            checkfirst=True
        )

    await engine.dispose()
    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())

