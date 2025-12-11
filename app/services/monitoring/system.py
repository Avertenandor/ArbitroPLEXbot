"""
System monitoring for health checks and server metrics.

Provides system health indicators and server resource metrics
including CPU, memory, disk usage, and database connectivity.
"""

import os
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SystemMonitor:
    """
    Monitor system health and server metrics.

    Provides database health checks and server resource monitoring
    including CPU, memory, disk usage, and process information.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the SystemMonitor.

        Args:
            session: Async database session for health checks
        """
        self.session = session

    async def get_health(self) -> dict[str, Any]:
        """
        Get system health indicators.

        Performs a database connectivity check and returns overall system status.

        Returns:
            Dict containing:
                - database: "OK" if database is accessible, "ERROR" otherwise
                - timestamp: Current time in ISO format
                - status: Overall status ("healthy" if all checks pass,
                         "degraded" if some checks fail, "error" on exception)

        Example:
            {
                "database": "OK",
                "timestamp": "2025-12-11T13:30:00.000000+00:00",
                "status": "healthy"
            }
        """
        try:
            # Database connectivity check
            db_ok = True
            try:
                await self.session.execute(text("SELECT 1"))
            except Exception:
                db_ok = False

            # Get current timestamp
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

        Collects comprehensive server metrics including CPU usage, memory usage,
        disk usage, and bot process memory consumption.

        Returns:
            Dict containing server metrics:
                - cpu_percent: CPU utilization percentage (float, 1 decimal)
                - cpu_cores: Number of CPU cores (int)
                - memory_total_gb: Total system memory in GB (float, 1 decimal)
                - memory_used_gb: Used system memory in GB (float, 1 decimal)
                - memory_percent: Memory utilization percentage (float, 1 decimal)
                - disk_total_gb: Total disk space in GB (float, 1 decimal)
                - disk_used_gb: Used disk space in GB (float, 1 decimal)
                - disk_percent: Disk utilization percentage (float, 1 decimal)
                - bot_memory_mb: Bot process memory in MB (float, 1 decimal)

            If psutil is not available, returns:
                {"error": "psutil not available"}

            On other errors, returns:
                {"error": "<error message>"}

        Example:
            {
                "cpu_percent": 45.2,
                "cpu_cores": 8,
                "memory_total_gb": 16.0,
                "memory_used_gb": 8.5,
                "memory_percent": 53.1,
                "disk_total_gb": 500.0,
                "disk_used_gb": 250.3,
                "disk_percent": 50.1,
                "bot_memory_mb": 145.2
            }
        """
        try:
            # Import psutil conditionally (may not be available in all environments)
            import psutil

            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            memory_percent = memory.percent

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_total_gb = disk.total / (1024**3)
            disk_used_gb = disk.used / (1024**3)
            disk_percent = disk.percent

            # Process memory info
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
