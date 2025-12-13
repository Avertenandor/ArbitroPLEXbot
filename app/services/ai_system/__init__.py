"""
AI System Administration Service.

Provides system-level management tools for AI assistant:
- Emergency stops (deposits, withdrawals, ROI)
- RPC provider switching
- Global settings management
- Platform health monitoring
- Scheduled tasks management

SECURITY: SUPER_ADMIN only for emergency controls.
Trusted admins for read-only monitoring.
"""
from app.services.ai_system.emergency_controls import (
    EmergencyControlsMixin,
)
from app.services.ai_system.platform_monitoring import (
    PlatformMonitoringMixin,
)
from app.services.ai_system.rpc_management import RPCManagementMixin
from app.services.ai_system.service import (
    AISystemService as BaseAISystemService,
)


class AISystemService(
    BaseAISystemService,
    EmergencyControlsMixin,
    RPCManagementMixin,
    PlatformMonitoringMixin,
):
    """
    Complete AI System Administration Service.

    Combines all functionality:
    - Core service (initialization, authorization)
    - Emergency controls (deposits, withdrawals, ROI stops)
    - RPC management (provider switching, auto-switch)
    - Platform monitoring (settings, health checks)

    SECURITY NOTES:
    - Access is granted to any verified (non-blocked) admin
    - All actions are logged
    - Emergency controls require super-admin privileges
    """

    pass


__all__ = [
    "AISystemService",
]
