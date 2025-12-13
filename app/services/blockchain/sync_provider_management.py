"""
Synchronous Web3 provider management with failover support.

This module handles:
- Multiple RPC provider initialization (QuickNode, NodeReal)
- Automatic failover between providers
- Provider health monitoring
- Settings synchronization with database

Note: This is separate from the async provider_manager.py which handles AsyncWeb3.
"""

import asyncio
import threading
import time
from collections.abc import Callable
from typing import Any

import aiohttp
from loguru import logger
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.config.settings import Settings
from app.repositories.global_settings_repository import GlobalSettingsRepository


class SyncProviderManager:
    """
    Manages synchronous Web3 providers with automatic failover.

    Supports multiple RPC providers (QuickNode, NodeReal) and automatically
    switches between them if one fails.
    """

    def __init__(
        self,
        settings: Settings,
        session_factory: Any | None = None,
    ) -> None:
        """
        Initialize provider manager.

        Args:
            settings: Application settings containing RPC URLs
            session_factory: Optional async session factory for DB access
        """
        self.settings = settings
        self.session_factory = session_factory

        # Providers storage
        self.providers: dict[str, Web3] = {}
        self._provider_lock = threading.Lock()
        self.active_provider_name = "quicknode"
        self.is_auto_switch_enabled = True

        # Settings cache
        self._last_settings_update = 0.0
        self._settings_cache_ttl = 30.0  # Check DB every 30 seconds

        # Initialize providers
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize Web3 providers based on settings."""
        from app.config.constants import BLOCKCHAIN_RPC_TIMEOUT

        # RPC timeout in seconds
        rpc_timeout = BLOCKCHAIN_RPC_TIMEOUT

        # 1. QuickNode
        qn_url = self.settings.rpc_quicknode_http or self.settings.rpc_url
        if qn_url:
            try:
                w3_qn = Web3(Web3.HTTPProvider(
                    qn_url,
                    request_kwargs={'timeout': rpc_timeout}
                ))
                w3_qn.middleware_onion.inject(geth_poa_middleware, layer=0)
                if w3_qn.is_connected():
                    self.providers["quicknode"] = w3_qn
                    logger.info("✅ QuickNode provider connected (timeout=30s)")
                else:
                    logger.warning("❌ QuickNode provider failed to connect")
            except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
                logger.error(f"Failed to init QuickNode (network error): {e}")
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"Failed to init QuickNode (data error): {e}")

        # 2. NodeReal
        nr_url = self.settings.rpc_nodereal_http
        if nr_url:
            try:
                w3_nr = Web3(Web3.HTTPProvider(
                    nr_url,
                    request_kwargs={'timeout': rpc_timeout}
                ))
                w3_nr.middleware_onion.inject(geth_poa_middleware, layer=0)
                if w3_nr.is_connected():
                    self.providers["nodereal"] = w3_nr
                    logger.info("✅ NodeReal provider connected (timeout=30s)")
                else:
                    logger.warning("❌ NodeReal provider failed to connect")
            except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
                logger.error(f"Failed to init NodeReal (network error): {e}")
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"Failed to init NodeReal (data error): {e}")

        # 3. NodeReal2 (Backup node - switch only by super admin)
        nr2_url = self.settings.rpc_nodereal2_http
        if nr2_url:
            try:
                w3_nr2 = Web3(Web3.HTTPProvider(
                    nr2_url,
                    request_kwargs={'timeout': rpc_timeout}
                ))
                w3_nr2.middleware_onion.inject(geth_poa_middleware, layer=0)
                if w3_nr2.is_connected():
                    self.providers["nodereal2"] = w3_nr2
                    logger.info("✅ NodeReal2 (backup) provider connected (timeout=30s)")
                else:
                    logger.warning("❌ NodeReal2 (backup) provider failed to connect")
            except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:
                logger.error(f"Failed to init NodeReal2 (network error): {e}")
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"Failed to init NodeReal2 (data error): {e}")

        if not self.providers:
            logger.error("🔥 NO BLOCKCHAIN PROVIDERS AVAILABLE! Service will fail.")

    def get_active_web3(self) -> Web3:
        """
        Get the currently active Web3 instance.

        Returns:
            Web3: Active Web3 provider instance

        Raises:
            ConnectionError: If no providers are available
        """
        with self._provider_lock:
            provider = self.providers.get(self.active_provider_name)
            if not provider:
                # Fallback to any available
                if self.providers:
                    fallback_name = next(iter(self.providers))
                    logger.warning(
                        f"Active provider '{self.active_provider_name}' not found, "
                        f"falling back to '{fallback_name}'"
                    )
                    return self.providers[fallback_name]
                raise ConnectionError("No blockchain providers available")
            return provider

    async def _update_settings_from_db(self) -> None:
        """Update active provider and auto-switch settings from DB."""
        if not self.session_factory:
            return

        now = time.time()
        if now - self._last_settings_update < self._settings_cache_ttl:
            return

        try:
            async with self.session_factory() as session:
                repo = GlobalSettingsRepository(session)
                settings = await repo.get_settings()
                with self._provider_lock:
                    self.active_provider_name = settings.active_rpc_provider
                    self.is_auto_switch_enabled = settings.is_auto_switch_enabled
                    self._last_settings_update = now
        except Exception as e:
            logger.warning(f"Failed to update blockchain settings from DB: {e}")

    async def _execute_with_failover(self, func: Callable[[Web3], Any]) -> Any:
        """
        Execute a function with automatic failover to backup provider.

        Args:
            func: Function that takes Web3 instance and returns result

        Returns:
            Result from the function

        Raises:
            Exception: If all providers fail
        """
        await self._update_settings_from_db()

        with self._provider_lock:
            current_name = self.active_provider_name
            is_auto_switch = self.is_auto_switch_enabled
        providers_list = list(self.providers.keys())

        # Try current provider first
        try:
            w3 = self.get_active_web3()
            return func(w3)
        except (ConnectionError, TimeoutError, aiohttp.ClientError, ValueError, KeyError, TypeError) as e:
            if not is_auto_switch:
                raise e

            # Determine error type for logging
            if isinstance(e, (ConnectionError, TimeoutError, aiohttp.ClientError)):
                error_type = "network error"
            else:
                error_type = "data error"

            logger.warning(
                f"Provider '{current_name}' failed ({error_type}): {e}. Attempting failover..."
            )

            # Find backup provider
            backup_name = None
            for name in providers_list:
                if name != current_name:
                    backup_name = name
                    break

            if not backup_name:
                logger.error("No backup provider available.")
                raise e

            logger.info(f"Switching to backup provider: {backup_name}")
            try:
                with self._provider_lock:
                    self.active_provider_name = backup_name
                w3_backup = self.providers[backup_name]
                result = func(w3_backup)

                # If successful, persist the switch asynchronously with error handling
                if self.session_factory:
                    asyncio.create_task(self._safe_persist_provider_switch(backup_name))

                return result
            except (ConnectionError, TimeoutError, aiohttp.ClientError) as e2:
                logger.error(f"Backup provider '{backup_name}' also failed (network error): {e2}")
                raise e2
            except (ValueError, KeyError, TypeError) as e2:
                logger.error(f"Backup provider '{backup_name}' also failed (data error): {e2}")
                raise e2

    async def _safe_persist_provider_switch(self, new_provider: str) -> None:
        """Wrapper for safe provider switch persistence."""
        try:
            await self._persist_provider_switch(new_provider)
        except Exception as e:
            logger.error(
                f"Background task failed to persist provider switch: {e}",
                exc_info=True
            )

    async def _persist_provider_switch(self, new_provider: str) -> None:
        """Persist the provider switch to DB."""
        if not self.session_factory:
            return
        try:
            async with self.session_factory() as session:
                repo = GlobalSettingsRepository(session)
                await repo.update_settings(active_rpc_provider=new_provider)
                await session.commit()
                logger.success(f"Persisted active provider switch to: {new_provider}")
        except Exception as e:
            # Note: session context manager handles rollback automatically on exception
            logger.error(f"Failed to persist provider switch: {e}", exc_info=True)
            raise

    async def force_refresh_settings(self) -> None:
        """Force update settings from DB."""
        self._last_settings_update = 0
        await self._update_settings_from_db()

    async def get_providers_status(self) -> dict[str, Any]:
        """
        Get status of all providers.

        Returns:
            Dict with provider status information
        """
        from concurrent.futures import ThreadPoolExecutor

        status = {}
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="web3") as executor:
            for name, w3 in self.providers.items():
                try:
                    loop = asyncio.get_running_loop()
                    # Run ping in executor with timeout
                    from app.config.constants import BLOCKCHAIN_EXECUTOR_TIMEOUT
                    try:
                        bn = await asyncio.wait_for(
                            loop.run_in_executor(
                                executor, lambda: w3.eth.block_number
                            ),
                            timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                        )
                        with self._provider_lock:
                            is_active = name == self.active_provider_name
                        status[name] = {
                            "connected": True,
                            "block": bn,
                            "active": is_active
                        }
                    except TimeoutError:
                        logger.warning(f"Timeout checking provider '{name}' status")
                        with self._provider_lock:
                            is_active = name == self.active_provider_name
                        status[name] = {
                            "connected": False,
                            "error": "Timeout",
                            "active": is_active
                        }
                except (ConnectionError, aiohttp.ClientError) as e:
                    logger.warning(f"Network error checking provider '{name}' status: {e}")
                    with self._provider_lock:
                        is_active = name == self.active_provider_name
                    status[name] = {
                        "connected": False,
                        "error": f"Network error: {str(e)}",
                        "active": is_active
                    }
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Data error checking provider '{name}' status: {e}")
                    with self._provider_lock:
                        is_active = name == self.active_provider_name
                    status[name] = {
                        "connected": False,
                        "error": f"Data error: {str(e)}",
                        "active": is_active
                    }
        return status
