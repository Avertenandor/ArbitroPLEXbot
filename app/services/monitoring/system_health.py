"""System health monitoring module for MonitoringService."""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SystemHealthService:
    """Service for checking system health and server metrics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize system health service."""
        self.session = session

    async def get_system_health(self) -> dict[str, Any]:
        """
        Get system health indicators.

        Returns:
            Dict with health metrics
        """
        try:
            # Database check
            db_ok = True
            try:
                await self.session.execute(text("SELECT 1"))
            except Exception:
                db_ok = False

            # Get some basic metrics
            now = datetime.now(UTC)

            return {
                "database": "OK" if db_ok else "ERROR",
                "timestamp": now.isoformat(),
                "status": "healthy" if db_ok else "degraded",
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"status": "error", "error": str(e)}

    async def get_server_metrics(self) -> dict[str, Any]:
        """
        Get server resource metrics (CPU, RAM, disk).

        Returns:
            Dict with server metrics
        """
        try:
            import os

            import psutil

            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Memory
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            memory_percent = memory.percent

            # Disk
            disk = psutil.disk_usage("/")
            disk_total_gb = disk.total / (1024**3)
            disk_used_gb = disk.used / (1024**3)
            disk_percent = disk.percent

            # Process info
            process = psutil.Process(os.getpid())
            process_memory_mb = process.memory_info().rss / (1024**2)

            return {
                "cpu_percent": round(cpu_percent, 1),
                "cpu_cores": cpu_count,
                "memory_total_gb": round(memory_total_gb, 1),
                "memory_used_gb": round(memory_used_gb, 1),
                "memory_percent": round(memory_percent, 1),
                "disk_total_gb": round(disk_total_gb, 1),
                "disk_used_gb": round(disk_used_gb, 1),
                "disk_percent": round(disk_percent, 1),
                "bot_memory_mb": round(process_memory_mb, 1),
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            logger.error(f"Error getting server metrics: {e}")
            return {"error": str(e)}
