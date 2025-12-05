"""
Help menu handlers (compatibility wrapper).

This module re-exports handlers from help_submenu for backward compatibility.
"""

from bot.handlers.menu.help_submenu import router, show_faq, show_help_submenu, show_support_contact

__all__ = ['router', 'show_help_submenu', 'show_faq', 'show_support_contact']
