"""Set global PROJECT_START_AT to now.

This script is meant for production operations when you want to declare
"project start = now" as a single epoch for ROI accruals and PLEX obligations.

It updates GlobalSettings.roi_settings["PROJECT_START_AT"] to current UTC time.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from loguru import logger

from app.config.database import async_session_maker
from app.repositories.global_settings_repository import GlobalSettingsRepository


async def main() -> None:
    async with async_session_maker() as session:
        repo = GlobalSettingsRepository(session)
        settings = await repo.get_settings()

        now = datetime.now(UTC)
        roi_settings = dict(settings.roi_settings or {})
        roi_settings["PROJECT_START_AT"] = now.isoformat()
        settings.roi_settings = roi_settings

        await session.commit()

        logger.info(f"PROJECT_START_AT set to {now.isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
