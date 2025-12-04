#!/usr/bin/env python3
"""Initialize database tables."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, "/app")

from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base

# Configure logger for script
logger.remove()
logger.add(sys.stderr, level="INFO")


async def init_database() -> None:
    """Create all database tables."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    logger.info("Connecting to database...")
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        logger.info("Creating tables (checkfirst=True)...")
        await conn.run_sync(
            Base.metadata.create_all,
            checkfirst=True
        )

    await engine.dispose()
    logger.success("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())
