"""
Service Registry for AI Tool Executor.

Provides lazy initialization of all AI services to avoid circular imports
and improve startup performance.
"""

from typing import Any

from loguru import logger

__all__ = ["ServiceRegistry"]


class ServiceRegistry:
    """
    Lazy service registry for AI tool execution.

    Initializes all AI services on-demand to:
    1. Avoid circular import issues
    2. Improve startup performance
    3. Ensure proper dependency injection

    Example:
        >>> registry = ServiceRegistry(session, bot, admin_data)
        >>> broadcast_service = registry.get_broadcast_service()
        >>> users_service = registry.get_users_service()
    """

    def __init__(self, session: Any, bot: Any, admin_data: dict[str, Any]) -> None:
        """
        Initialize the service registry.

        Args:
            session: SQLAlchemy AsyncSession for database operations
            bot: Aiogram Bot instance for Telegram operations
            admin_data: Dictionary containing admin information with keys:
                - ID: Admin Telegram ID
                - username: Admin username
                - Имя: Admin display name (optional)
        """
        self._session = session
        self._bot = bot
        self._admin_data = admin_data
        self._initialized = False

        # Service references (initialized lazily)
        self._broadcast_service = None
        self._bonus_service = None
        self._appeals_service = None
        self._inquiries_service = None
        self._users_service = None
        self._stats_service = None
        self._withdrawals_service = None
        self._deposits_service = None
        self._roi_service = None
        self._blacklist_service = None
        self._finpass_service = None
        self._referral_service = None
        self._logs_service = None
        self._settings_service = None
        self._rate_limiter = None

    def init_services(self) -> None:
        """
        Initialize all services lazily.

        Uses lazy imports to avoid circular dependencies.
        This method is idempotent - calling it multiple times is safe.
        """
        if self._initialized:
            return

        logger.debug("Initializing AI services lazily...")

        # Lazy imports to avoid circular dependencies
        from app.services.ai_appeals_service import AIAppealsService
        from app.services.ai_blacklist_service import AIBlacklistService
        from app.services.ai_bonus_service import AIBonusService
        from app.services.ai_broadcast_service import AIBroadcastService
        from app.services.ai_deposits_service import AIDepositsService
        from app.services.ai_finpass_service import AIFinpassService
        from app.services.ai_inquiries_service import AIInquiriesService
        from app.services.ai_logs_service import AILogsService
        from app.services.ai_referral_service import AIReferralService
        from app.services.ai_roi_service import AIRoiService
        from app.services.ai_settings_service import AISettingsService
        from app.services.ai_statistics_service import AIStatisticsService
        from app.services.ai_users_service import AIUsersService
        from app.services.ai_withdrawals_service import AIWithdrawalsService
        from app.services.aria_security_defense import get_rate_limiter

        # Extract admin credentials for broadcast service
        admin_telegram_id = self._admin_data.get("ID")
        admin_username = self._admin_data.get("username") or self._admin_data.get("Имя")

        # Initialize broadcast service (has special parameters)
        self._broadcast_service = AIBroadcastService(
            session=self._session,
            bot=self._bot,
            admin_telegram_id=admin_telegram_id,
            admin_username=admin_username,
        )

        # Initialize all other services (follow standard pattern)
        self._bonus_service = AIBonusService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._appeals_service = AIAppealsService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._inquiries_service = AIInquiriesService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._users_service = AIUsersService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._stats_service = AIStatisticsService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._withdrawals_service = AIWithdrawalsService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._deposits_service = AIDepositsService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._roi_service = AIRoiService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._blacklist_service = AIBlacklistService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._finpass_service = AIFinpassService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._referral_service = AIReferralService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._logs_service = AILogsService(
            session=self._session,
            admin_data=self._admin_data,
        )

        self._settings_service = AISettingsService(
            session=self._session,
            admin_data=self._admin_data,
        )

        # Initialize rate limiter singleton
        self._rate_limiter = get_rate_limiter()

        self._initialized = True
        logger.debug("AI services initialized successfully")

    def get_broadcast_service(self):
        """
        Get the AI Broadcast Service instance.

        Returns:
            AIBroadcastService: Service for sending messages and broadcasts

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._broadcast_service

    def get_bonus_service(self):
        """
        Get the AI Bonus Service instance.

        Returns:
            AIBonusService: Service for managing user bonuses

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._bonus_service

    def get_appeals_service(self):
        """
        Get the AI Appeals Service instance.

        Returns:
            AIAppealsService: Service for managing user appeals

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._appeals_service

    def get_inquiries_service(self):
        """
        Get the AI Inquiries Service instance.

        Returns:
            AIInquiriesService: Service for managing user inquiries

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._inquiries_service

    def get_users_service(self):
        """
        Get the AI Users Service instance.

        Returns:
            AIUsersService: Service for user management operations

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._users_service

    def get_stats_service(self):
        """
        Get the AI Statistics Service instance.

        Returns:
            AIStatisticsService: Service for retrieving statistics

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._stats_service

    def get_withdrawals_service(self):
        """
        Get the AI Withdrawals Service instance.

        Returns:
            AIWithdrawalsService: Service for managing withdrawals

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._withdrawals_service

    def get_deposits_service(self):
        """
        Get the AI Deposits Service instance.

        Returns:
            AIDepositsService: Service for managing deposits

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._deposits_service

    def get_roi_service(self):
        """
        Get the AI ROI Service instance.

        Returns:
            AIRoiService: Service for ROI corridor management

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._roi_service

    def get_blacklist_service(self):
        """
        Get the AI Blacklist Service instance.

        Returns:
            AIBlacklistService: Service for blacklist management

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._blacklist_service

    def get_finpass_service(self):
        """
        Get the AI Financial Password Service instance.

        Returns:
            AIFinpassService: Service for financial password recovery

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._finpass_service

    def get_referral_service(self):
        """
        Get the AI Referral Service instance.

        Returns:
            AIReferralService: Service for referral statistics

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._referral_service

    def get_logs_service(self):
        """
        Get the AI Logs Service instance.

        Returns:
            AILogsService: Service for admin log management

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._logs_service

    def get_settings_service(self):
        """
        Get the AI Settings Service instance.

        Returns:
            AISettingsService: Service for system settings management

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._settings_service

    def get_rate_limiter(self):
        """
        Get the rate limiter instance.

        Returns:
            ToolRateLimiter: Rate limiter for tool execution

        Raises:
            RuntimeError: If services haven't been initialized
        """
        if not self._initialized:
            self.init_services()
        return self._rate_limiter
