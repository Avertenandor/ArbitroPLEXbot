"""
Cabinet menu handlers (compatibility wrapper).

This module re-exports handlers from cabinet_submenu for backward compatibility.
"""

from bot.handlers.menu.cabinet_submenu import router, show_cabinet_submenu


__all__ = ['router', 'show_cabinet_submenu']
