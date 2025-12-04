"""
Health check server for scheduler monitoring.

Provides HTTP endpoint for health checks and monitoring.
"""

import asyncio

from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

# Global scheduler reference for health checks
_scheduler: AsyncIOScheduler | None = None


def set_scheduler(scheduler: AsyncIOScheduler) -> None:
    """
    Set the scheduler instance for health checks.

    Args:
        scheduler: AsyncIOScheduler instance to monitor
    """
    global _scheduler
    _scheduler = scheduler
    logger.info("Scheduler registered for health checks")


async def health_handler(request: web.Request) -> web.Response:
    """
    Health check endpoint.

    Returns:
        JSON response with scheduler status
    """
    if _scheduler is None:
        return web.json_response(
            {
                "status": "unhealthy",
                "error": "Scheduler not initialized",
            },
            status=503,
        )

    try:
        is_running = _scheduler.running
        jobs = _scheduler.get_jobs()
        job_info = [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in jobs
        ]

        return web.json_response(
            {
                "status": "healthy" if is_running else "stopped",
                "scheduler_running": is_running,
                "jobs_count": len(jobs),
                "jobs": job_info,
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response(
            {
                "status": "unhealthy",
                "error": str(e),
            },
            status=503,
        )


async def readiness_handler(request: web.Request) -> web.Response:
    """
    Readiness check endpoint.

    Returns:
        JSON response indicating if scheduler is ready to accept traffic
    """
    if _scheduler is None or not _scheduler.running:
        return web.json_response(
            {
                "status": "not_ready",
                "ready": False,
            },
            status=503,
        )

    return web.json_response(
        {
            "status": "ready",
            "ready": True,
        }
    )


async def liveness_handler(request: web.Request) -> web.Response:
    """
    Liveness check endpoint.

    Returns:
        JSON response indicating if the process is alive
    """
    return web.json_response(
        {
            "status": "alive",
            "alive": True,
        }
    )


async def start_health_server(
    host: str = "0.0.0.0",
    port: int = 8081,
) -> tuple[web.AppRunner, web.TCPSite]:
    """
    Start health check server.

    Args:
        host: Host to bind to
        port: Port to bind to

    Returns:
        Tuple of (AppRunner, TCPSite) for cleanup
    """
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/readiness", readiness_handler)
    app.router.add_get("/liveness", liveness_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"Health check server started on {host}:{port}")
    logger.info(f"  - Health: http://{host}:{port}/health")
    logger.info(f"  - Readiness: http://{host}:{port}/readiness")
    logger.info(f"  - Liveness: http://{host}:{port}/liveness")

    return runner, site


async def stop_health_server(
    runner: web.AppRunner,
    timeout: int = 5,
) -> None:
    """
    Stop health check server gracefully.

    Args:
        runner: AppRunner to cleanup
        timeout: Maximum time to wait for cleanup in seconds
    """
    logger.info("Stopping health check server...")
    try:
        await asyncio.wait_for(runner.cleanup(), timeout=timeout)
        logger.info("Health check server stopped successfully")
    except TimeoutError:
        logger.warning(f"Health check server cleanup timed out after {timeout}s")
    except Exception as e:
        logger.error(f"Error stopping health check server: {e}")
