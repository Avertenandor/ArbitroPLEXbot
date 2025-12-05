"""
Blacklist Service.

Manages user blacklist for pre-registration and ban prevention.

This module maintains backward compatibility by re-exporting
from the refactored modular structure.
"""

# Re-export from modular structure for backward compatibility
from app.services.blacklist_service import BlacklistService

__all__ = ['BlacklistService']
