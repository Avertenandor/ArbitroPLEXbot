"""
Health Check Module.

Contains health check functionality for the BlockchainService.
"""

from typing import Any

from loguru import logger


class HealthCheck:
    """
    Handles health check operations.

    Features:
    - Provider health checks
    - Balance queries
    - Monitoring status
    """

    def __init__(
        self,
        provider_manager,
        balance_operations,
        event_monitor,
        system_wallet_address: str,
        payout_wallet_address: str,
    ):
        """
        Initialize health check.

        Args:
            provider_manager: Provider manager instance
            balance_operations: Balance operations instance
            event_monitor: Event monitor instance
            system_wallet_address: System wallet address
            payout_wallet_address: Payout wallet address
        """
        self.provider_manager = provider_manager
        self.balance_operations = balance_operations
        self.event_monitor = event_monitor
        self.system_wallet_address = system_wallet_address
        self.payout_wallet_address = payout_wallet_address

    async def health_check(self, initialized: bool) -> dict[str, Any]:
        """
        Perform health check on blockchain service.

        Args:
            initialized: Whether the service is initialized

        Returns:
            Dict with health status
        """
        if not initialized:
            return {
                "initialized": False,
                "providers": {},
                "balances": {},
            }

        # Check providers
        provider_health = await self.provider_manager.health_check()

        # Check balances
        try:
            payout_usdt = await self.balance_operations.get_usdt_balance()
            payout_bnb = await self.balance_operations.get_bnb_balance()
            system_usdt = await self.balance_operations.get_usdt_balance(
                self.system_wallet_address
            )
        except Exception as e:
            logger.error(f"Error checking balances: {e}")
            payout_usdt = None
            payout_bnb = None
            system_usdt = None

        return {
            "initialized": True,
            "providers": provider_health,
            "balances": {
                "payout_wallet": {
                    "address": self.payout_wallet_address,
                    "usdt": float(payout_usdt) if payout_usdt else None,
                    "bnb": float(payout_bnb) if payout_bnb else None,
                },
                "system_wallet": {
                    "address": self.system_wallet_address,
                    "usdt": float(system_usdt) if system_usdt else None,
                },
            },
            "monitoring_active": (
                self.event_monitor.is_monitoring
                if self.event_monitor
                else False
            ),
        }
