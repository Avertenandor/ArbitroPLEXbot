"""
Admin Security Monitor.

R10-3: Monitors admin actions for suspicious patterns and automatically
blocks compromised admins.

This module maintains backward compatibility by re-exporting
from the refactored modular structure.
"""

# Re-export from modular structure for backward compatibility
from app.services.admin_security_monitor import AdminSecurityMonitor

__all__ = ['AdminSecurityMonitor']
