"""
Bonus V2 handlers module.

This module contains all handlers for bonus management functionality.
"""

from .menu import router as menu_router
from .grant import router as grant_router
from .cancel import router as cancel_router
from .search import router as search_router
from .view import router as view_router


def setup_handlers() -> list:
    """Return all routers for bonus handlers."""
    return [
        menu_router,
        grant_router,
        cancel_router,
        search_router,
        view_router,
    ]


__all__ = [
    "menu_router",
    "grant_router",
    "cancel_router",
    "search_router",
    "view_router",
    "setup_handlers",
]
