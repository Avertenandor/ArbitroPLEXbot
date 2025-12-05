"""
Blockchain service.

Full Web3.py implementation for BSC blockchain operations
(USDT transfers, monitoring) with Dual-Core engine (QuickNode + NodeReal).
"""

import asyncio
import ctypes
import time
import warnings
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any, TypeVar

# Suppress eth_utils network warnings about invalid ChainId
warnings.filterwarnings(
    "ignore",
    message=".*does not have a valid ChainId.*",
    category=UserWarning,
    module="eth_utils.network",
)
warnings.filterwarnings(
    "ignore",
    message=".*does not have a valid ChainId.*",
    category=UserWarning,
)

from eth_account import Account
from eth_utils import is_address, to_checksum_address
from loguru import logger
from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception
from web3.middleware import geth_poa_middleware

from app.config.constants import BLOCKCHAIN_EXECUTOR_TIMEOUT
from app.config.settings import Settings
from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.utils.encryption import get_encryption_service
from app.utils.exceptions import SecurityError
from app.utils.security import mask_address, mask_tx_hash

# USDT contract ABI (ERC-20 standard functions)
USDT_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
]

# USDT decimals (BEP-20 USDT uses 18 decimals)
USDT_DECIMALS = 18

# Gas settings for BSC
# 0.1 Gwei = 100_000_000 Wei (1 Gwei = 10^9 Wei)
# User requirement: Max 0.1 Gwei, try lower if possible
MIN_GAS_PRICE_GWEI = Decimal("0.01")
MAX_GAS_PRICE_GWEI = Decimal("0.1")
MIN_GAS_PRICE_WEI = int(MIN_GAS_PRICE_GWEI * 10**9)
MAX_GAS_PRICE_WEI = int(MAX_GAS_PRICE_GWEI * 10**9)

T = TypeVar("T")


def secure_zero_memory(secret: str) -> None:
    """
    Securely overwrite memory containing secret data.

    NOTE: This provides best-effort memory clearing in Python.
    Python's memory management makes true secure erasure impossible,
    but this reduces the window of exposure.
    """
    if not secret:
        return

    try:
        # Convert to bytes if string
        secret_bytes = secret.encode() if isinstance(secret, str) else secret
        # Overwrite with zeros
        # This is a best-effort approach - Python's GC may have copies
        ctypes.memset(id(secret_bytes) + 32, 0, len(secret_bytes))
    except Exception:
        # Fail silently - this is best-effort security
        pass


class BlockchainService:
    """
    Blockchain service for BSC/USDT operations.

    Full Web3.py implementation with:
    - Dual-Core Engine (QuickNode + NodeReal)
    - Automatic Failover
    - Smart Gas Management
    - USDT contract interaction
    - Transaction sending
    - Balance checking
    - Event monitoring
    """

    def __init__(
        self,
        settings: Settings,
        session_factory: Any | None = None,
    ) -> None:
        """
        Initialize blockchain service.

        Args:
            settings: Application settings
            session_factory: Async session factory for DB access (optional)
        """
        self.settings = settings
        self.session_factory = session_factory

        self.usdt_contract_address = to_checksum_address(settings.usdt_contract_address)
        self.wallet_private_key = settings.wallet_private_key
        self.system_wallet_address = settings.system_wallet_address

        # Initialize RPC rate limiter
        from app.services.blockchain.rpc_rate_limiter import RPCRateLimiter
        self.rpc_limiter = RPCRateLimiter(max_concurrent=10, max_rps=25)

        # Thread pool executor
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="web3"
        )

        # Nonce lock for preventing race conditions in parallel transactions
        self._nonce_lock = asyncio.Lock()

        # Providers storage
        self.providers: dict[str, Web3] = {}
        self.active_provider_name = "quicknode"
        self.is_auto_switch_enabled = True
        self._last_settings_update = 0.0
        self._settings_cache_ttl = 30.0  # Check DB every 30 seconds

        # Initialize Providers
        self._init_providers()

        # Initialize Wallet
        self._init_wallet()

        logger.success(
            f"BlockchainService initialized successfully\n"
            f"  Active Provider: {self.active_provider_name}\n"
            f"  Providers: {list(self.providers.keys())}\n"
            f"  USDT Contract: {self.usdt_contract_address}\n"
            f"  Wallet: {mask_address(self.wallet_address) if self.wallet_address else 'Not configured'}"
        )

    def get_optimal_gas_price(self, w3: Web3) -> int:
        """
        Calculate optimal gas price with Smart Gas strategy.

        Logic:
        1. Get current RPC gas price.
        2. Clamp between MIN (0.1 Gwei) and MAX (5.0 Gwei).

        Args:
            w3: Web3 instance

        Returns:
            Gas price in Wei
        """
        try:
            rpc_gas = w3.eth.gas_price

            # Clamp logic
            final_gas = max(MIN_GAS_PRICE_WEI, min(MAX_GAS_PRICE_WEI, rpc_gas))

            # Log if capped
            if rpc_gas > MAX_GAS_PRICE_WEI:
                logger.warning(
                    f"Gas price capped! RPC: {rpc_gas / 1e9:.2f} Gwei, "
                    f"Used: {final_gas / 1e9:.2f} Gwei"
                )

            return int(final_gas)
        except Exception as e:
            logger.warning(f"Failed to get gas price, using MIN: {e}")
            return int(MIN_GAS_PRICE_WEI)

    def _init_providers(self) -> None:
        """Initialize Web3 providers based on settings."""
        # RPC timeout in seconds
        rpc_timeout = 30

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
                    logger.info("вњ… QuickNode provider connected (timeout=30s)")
                else:
                    logger.warning("вќЊ QuickNode provider failed to connect")
            except Exception as e:
                logger.error(f"Failed to init QuickNode: {e}")

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
                    logger.info("вњ… NodeReal provider connected (timeout=30s)")
                else:
                    logger.warning("вќЊ NodeReal provider failed to connect")
            except Exception as e:
                logger.error(f"Failed to init NodeReal: {e}")

        if not self.providers:
            logger.error("рџ”Ґ NO BLOCKCHAIN PROVIDERS AVAILABLE! Service will fail.")

    def _init_wallet(self) -> None:
        """
        Initialize wallet account.

        SECURITY: Automatically decrypts private key if it was encrypted.
        Private key is kept in memory only for signing - cleared immediately after use.
        """
        if self.wallet_private_key:
            private_key = None
            try:
                # CRITICAL: Decrypt private key if it's encrypted
                private_key = self.wallet_private_key
                encryption_service = get_encryption_service()

                if not encryption_service or not encryption_service.enabled:
                    raise SecurityError(
                        "EncryptionService not available or disabled. "
                        "Cannot decrypt private key without encryption. "
                        "Ensure ENCRYPTION_KEY is set correctly."
                    )

                # Try to decrypt - raises SecurityError on failure
                decrypted = encryption_service.decrypt(private_key)
                if not decrypted:
                    raise SecurityError(
                        "Failed to decrypt private key. "
                        "Ensure ENCRYPTION_KEY is set correctly and key is encrypted."
                    )

                private_key = decrypted
                logger.info("Private key decrypted successfully")

                # Initialize wallet account with decrypted key
                self.wallet_account = Account.from_key(private_key)
                self.wallet_address = to_checksum_address(self.wallet_account.address)

            except SecurityError:
                # Re-raise security errors without catching
                raise
            except Exception as e:
                logger.error(f"Failed to init wallet: {e}")
                self.wallet_account = None
                self.wallet_address = None
            finally:
                # SECURITY: Clear decrypted private key from memory
                if private_key and private_key != self.wallet_private_key:
                    secure_zero_memory(private_key)
                    del private_key
        else:
            self.wallet_account = None
            self.wallet_address = None

    def _get_safe_nonce(self, w3: Web3, address: str) -> int:
        """
        Get nonce with stuck transaction detection.

        SYNC method - runs in executor.

        Args:
            w3: Web3 instance
            address: Wallet address

        Returns:
            Safe nonce to use
        """
        # Get pending nonce (includes pending transactions)
        pending_nonce = w3.eth.get_transaction_count(address, 'pending')
        # Get confirmed nonce (only confirmed transactions)
        confirmed_nonce = w3.eth.get_transaction_count(address, 'latest')

        # If there are too many stuck transactions (pending > confirmed + threshold)
        stuck_threshold = 5
        if pending_nonce > confirmed_nonce + stuck_threshold:
            logger.warning(
                f"Possible stuck transactions detected: "
                f"pending={pending_nonce}, confirmed={confirmed_nonce}, "
                f"stuck={pending_nonce - confirmed_nonce}"
            )

        return pending_nonce

    async def _get_nonce_with_distributed_lock(self, address: str) -> int:
        """
        Get nonce with distributed lock for multi-instance protection.

        Uses Redis-based distributed lock to prevent nonce conflicts
        when multiple bot instances are running.

        Args:
            address: Wallet address

        Returns:
            Safe nonce to use
        """
        from app.utils.distributed_lock import get_distributed_lock

        # Create lock key specific to this address
        lock_key = f"nonce_lock:{address}"

        # Get Web3 instance
        w3 = self.get_active_web3()

        # Try to get distributed lock with Redis
        # If Redis is unavailable, fallback to PostgreSQL or local lock
        if self.session_factory:
            async with self.session_factory() as session:
                distributed_lock = get_distributed_lock(session=session)

                # Acquire distributed lock with timeout
                async with distributed_lock.lock(
                    key=lock_key,
                    timeout=30,  # Lock expires after 30 seconds
                    blocking=True,
                    blocking_timeout=10.0  # Wait max 10 seconds for lock
                ):
                    # Get nonce inside the lock
                    loop = asyncio.get_event_loop()
                    nonce = await loop.run_in_executor(
                        self._executor,
                        lambda: self._get_safe_nonce(w3, address)
                    )
                    return nonce
        else:
            # Fallback to local lock if no session factory
            logger.warning("No session factory available, using local lock only")
            loop = asyncio.get_event_loop()
            nonce = await loop.run_in_executor(
                self._executor,
                lambda: self._get_safe_nonce(w3, address)
            )
            return nonce

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
                self.active_provider_name = settings.active_rpc_provider
                self.is_auto_switch_enabled = settings.is_auto_switch_enabled
                self._last_settings_update = now
        except Exception as e:
            logger.warning(f"Failed to update blockchain settings from DB: {e}")

    def get_active_web3(self) -> Web3:
        """Get the currently active Web3 instance."""
        provider = self.providers.get(self.active_provider_name)
        if not provider:
            # Fallback to any available
            if self.providers:
                fallback_name = next(iter(self.providers))
                logger.warning(f"Active provider '{self.active_provider_name}' not found, falling back to '{fallback_name}'")
                return self.providers[fallback_name]
            raise ConnectionError("No blockchain providers available")
        return provider

    @property
    def web3(self) -> Web3:
        """Backward compatibility property."""
        return self.get_active_web3()

    @property
    def usdt_contract(self):
        """Get USDT contract on active provider."""
        w3 = self.get_active_web3()
        return w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)

    async def _execute_with_failover(self, func: Callable[[Web3], Any]) -> Any:
        """
        Execute a function with automatic failover to the backup provider.
        """
        await self._update_settings_from_db()

        current_name = self.active_provider_name
        providers_list = list(self.providers.keys())

        # Try current provider first
        try:
            w3 = self.get_active_web3()
            return func(w3)
        except Exception as e:
            if not self.is_auto_switch_enabled:
                raise e

            logger.warning(f"Provider '{current_name}' failed: {e}. Attempting failover...")

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
                self.active_provider_name = backup_name
                w3_backup = self.providers[backup_name]
                result = func(w3_backup)

                # If successful, persist the switch asynchronously with error handling
                if self.session_factory:
                    asyncio.create_task(self._safe_persist_provider_switch(backup_name))

                return result
            except Exception as e2:
                logger.error(f"Backup provider '{backup_name}' also failed: {e2}")
                raise e2

    async def _safe_persist_provider_switch(self, new_provider: str) -> None:
        """Wrapper for safe provider switch persistence."""
        try:
            await self._persist_provider_switch(new_provider)
        except Exception as e:
            logger.error(f"Background task failed to persist provider switch: {e}", exc_info=True)

    async def _persist_provider_switch(self, new_provider: str):
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
            await session.rollback()
            logger.error(f"Failed to persist provider switch: {e}", exc_info=True)
            raise

    async def force_refresh_settings(self):
        """Force update settings from DB."""
        self._last_settings_update = 0
        await self._update_settings_from_db()

    def get_rpc_stats(self) -> dict[str, Any]:
        return self.rpc_limiter.get_stats()

    def close(self) -> None:
        """Clean up resources and clear sensitive data."""
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=True)

        # SECURITY: Clear sensitive data on shutdown
        if hasattr(self, 'wallet_private_key') and self.wallet_private_key:
            secure_zero_memory(self.wallet_private_key)
        if hasattr(self, 'wallet_account'):
            self.wallet_account = None

    async def get_block_number(self) -> int:
        loop = asyncio.get_event_loop()
        async with self.rpc_limiter:
            return await loop.run_in_executor(
                self._executor,
                lambda: asyncio.run(self._execute_with_failover(
                    lambda w3: w3.eth.block_number
                ))
            )

    async def _run_async_failover(self, sync_func: Callable[[Web3], Any]) -> Any:
        """
        Runs a synchronous Web3 function in the thread pool,
        with failover logic handled in the main async loop.
        """
        await self._update_settings_from_db()
        loop = asyncio.get_event_loop()

        current_name = self.active_provider_name

        # Try primary
        try:
            # Check primary provider exists logic handled by get_active_web3 inside executor or here
            # Actually better to get w3 instance here
            if current_name not in self.providers and self.providers:
                current_name = next(iter(self.providers))

            if current_name not in self.providers:
                raise ConnectionError("No providers available")

            w3 = self.providers[current_name]

            async with self.rpc_limiter:
                try:
                    return await asyncio.wait_for(
                        loop.run_in_executor(
                            self._executor,
                            lambda: sync_func(w3)
                        ),
                        timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                    )
                except TimeoutError:
                    logger.error(f"Timeout in blockchain operation on provider '{current_name}'")
                    raise TimeoutError(f"Blockchain operation timeout on {current_name}")
        except Exception as e:
            if not self.is_auto_switch_enabled:
                raise e

            logger.warning(f"Primary provider '{current_name}' failed: {e}. Trying failover...")

            # Find backup
            backup_name = next((n for n in self.providers if n != current_name), None)
            if not backup_name:
                raise e

            # Try backup
            try:
                logger.info(f"Switching to backup: {backup_name}")
                w3_backup = self.providers[backup_name]

                async with self.rpc_limiter:
                    try:
                        result = await asyncio.wait_for(
                            loop.run_in_executor(
                                self._executor,
                                lambda: sync_func(w3_backup)
                            ),
                            timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                        )
                    except TimeoutError:
                        logger.error(f"Timeout in blockchain operation on backup provider '{backup_name}'")
                        raise TimeoutError(f"Blockchain operation timeout on backup {backup_name}")

                # If success, switch permanent
                self.active_provider_name = backup_name
                if self.session_factory:
                    asyncio.create_task(self._safe_persist_provider_switch(backup_name))

                return result
            except Exception as e2:
                logger.error(f"Backup provider failed: {e2}")
                raise e

    async def send_payment(self, to_address: str, amount: Decimal) -> dict[str, Any]:
        """
        Send USDT payment.

        Args:
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal for precision)

        Returns:
            Dict with success, tx_hash, error
        """
        try:
            if not self.wallet_account:
                return {"success": False, "error": "Wallet not configured"}

            if not await self.validate_wallet_address(to_address):
                return {"success": False, "error": f"Invalid address: {to_address}"}

            to_address = to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            from decimal import ROUND_DOWN
            amount_wei = int((Decimal(str(amount)) * Decimal(10 ** USDT_DECIMALS)).to_integral_value(ROUND_DOWN))

            # Get nonce with async lock BEFORE entering executor
            # This prevents race conditions in parallel transactions
            async with self._nonce_lock:
                nonce = await self._get_nonce_with_distributed_lock(self.wallet_address)

                # Now execute transaction with pre-acquired nonce
                def _send_tx(w3: Web3, nonce: int):
                    contract = w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)
                    func = contract.functions.transfer(to_address, amount_wei)

                    # Use Smart Gas
                    gas_price = self.get_optimal_gas_price(w3)

                    try:
                        gas_est = func.estimate_gas({"from": self.wallet_address})
                    except (Web3Exception, ContractLogicError) as e:
                        logger.warning(f"Gas estimation failed: {e}")
                        gas_est = 100000  # Fallback for USDT transfer

                    txn = func.build_transaction({
                        "from": self.wallet_address,
                        "gas": int(gas_est * 1.2),
                        "gasPrice": gas_price,
                        "nonce": nonce,
                        "chainId": w3.eth.chain_id,
                    })

                    logger.info(
                        f"Sending USDT tx: to={mask_address(to_address)}, amount={amount}, "
                        f"nonce={nonce}, gas_price={gas_price} wei ({gas_price / 10**9} Gwei), "
                        f"gas_limit={int(gas_est * 1.2)}"
                    )

                    signed = self.wallet_account.sign_transaction(txn)
                    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                    return tx_hash.hex()

                # Execute with pre-acquired nonce
                tx_hash_str = await self._run_async_failover(lambda w3: _send_tx(w3, nonce))

            logger.info(f"USDT payment sent: {amount} to {mask_address(to_address)}, hash: {mask_tx_hash(tx_hash_str)}")
            return {"success": True, "tx_hash": tx_hash_str, "error": None}

        except Exception as e:
            logger.error(f"Failed to send payment: {e}")
            return {"success": False, "error": str(e)}

    async def send_native_token(self, to_address: str, amount: Decimal) -> dict[str, Any]:
        """
        Send native token (BNB) to address.

        Args:
            to_address: Recipient wallet address
            amount: Amount in BNB (Decimal for precision)

        Returns:
            Dict with success, tx_hash, error
        """
        try:
            if not self.wallet_account:
                return {"success": False, "error": "Wallet not configured"}

            if not await self.validate_wallet_address(to_address):
                return {"success": False, "error": f"Invalid address: {to_address}"}

            to_address = to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            from decimal import ROUND_DOWN
            amount_wei = int((Decimal(str(amount)) * Decimal(10 ** 18)).to_integral_value(ROUND_DOWN))

            # Get nonce with async lock BEFORE entering executor
            # This prevents race conditions in parallel transactions
            async with self._nonce_lock:
                nonce = await self._get_nonce_with_distributed_lock(self.wallet_address)

                # Now execute transaction with pre-acquired nonce
                def _send_native(w3: Web3, nonce: int):
                    # Use Smart Gas
                    gas_price = self.get_optimal_gas_price(w3)
                    gas_limit = 21000  # Standard native transfer gas

                    txn = {
                        "to": to_address,
                        "value": amount_wei,
                        "gas": gas_limit,
                        "gasPrice": gas_price,
                        "nonce": nonce,
                        "chainId": w3.eth.chain_id,
                    }

                    logger.info(
                        f"Sending BNB tx: to={mask_address(to_address)}, amount={amount}, "
                        f"nonce={nonce}, gas_price={gas_price} wei ({gas_price / 10**9} Gwei)"
                    )

                    signed = self.wallet_account.sign_transaction(txn)
                    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                    return tx_hash.hex()

                # Execute with pre-acquired nonce
                tx_hash_str = await self._run_async_failover(lambda w3: _send_native(w3, nonce))

            logger.info(f"BNB payment sent: {amount} to {mask_address(to_address)}, hash: {mask_tx_hash(tx_hash_str)}")
            return {"success": True, "tx_hash": tx_hash_str, "error": None}

        except Exception as e:
            logger.error(f"Failed to send BNB: {e}")
            return {"success": False, "error": str(e)}

    async def get_native_balance(self, address: str) -> Decimal | None:
        """Get Native Token (BNB) balance."""
        try:
            address = to_checksum_address(address)

            def _get_bal(w3: Web3):
                return w3.eth.get_balance(address)

            wei = await self._run_async_failover(_get_bal)
            return Decimal(wei) / Decimal(10 ** 18)
        except Exception as e:
            logger.error(f"Get BNB balance failed: {e}")
            return None

    async def check_transaction_status(self, tx_hash: str) -> dict[str, Any]:
        try:
            def _check(w3: Web3):
                try:
                    receipt = w3.eth.get_transaction_receipt(tx_hash)
                    current = w3.eth.block_number
                    return receipt, current
                except Web3Exception as e:
                    logger.debug(f"Could not get transaction receipt: {e}")
                    return None, None

            receipt, current_block = await self._run_async_failover(_check)

            if not receipt:
                return {"status": "pending", "confirmations": 0}

            confirmations = max(0, current_block - receipt.blockNumber)
            status = "confirmed" if receipt.status == 1 else "failed"

            return {
                "status": status,
                "confirmations": confirmations,
                "block_number": receipt.blockNumber
            }
        except (TimeoutError, Web3Exception) as e:
            logger.warning(f"Failed to check transaction status: {e}")
            return {"status": "unknown", "confirmations": 0}

    async def get_transaction_details(self, tx_hash: str) -> dict[str, Any] | None:
        try:
            # Just execute directly via failover helper, encapsulating logic
            return await self._run_async_failover(lambda w3: self._fetch_tx_details_sync(w3, tx_hash))
        except (TimeoutError, Web3Exception) as e:
            logger.warning(f"Failed to get transaction details: {e}")
            return None

    def _fetch_tx_details_sync(self, w3: Web3, tx_hash: str):
        try:
            tx = w3.eth.get_transaction(tx_hash)
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
            except Web3Exception as e:
                logger.debug(f"Could not get transaction receipt: {e}")
                receipt = None

            # Parse logic...
            contract = w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)

            from_address = to_checksum_address(tx["from"])
            to_address = to_checksum_address(tx["to"]) if tx["to"] else None
            value = Decimal(0)

            if to_address and to_address.lower() == self.usdt_contract_address.lower():
                try:
                    decoded = contract.decode_function_input(tx["input"])
                    if decoded[0].fn_name == "transfer":
                        amount_wei = decoded[1]["_value"]
                        value = Decimal(amount_wei) / Decimal(10 ** USDT_DECIMALS)
                        to_address = to_checksum_address(decoded[1]["_to"])
                except Exception:
                    pass

            return {
                "from_address": from_address,
                "to_address": to_address,
                "value": value,
                "status": "confirmed" if receipt and receipt.status == 1 else "pending",
            }
        except (Web3Exception, ValueError) as e:
            logger.debug(f"Could not fetch transaction details: {e}")
            return None

    async def validate_wallet_address(self, address: str) -> bool:
        try:
            return is_address(address)
        except (ValueError, TypeError) as e:
            logger.debug(f"Invalid wallet address format: {e}")
            return False

    async def get_usdt_balance(self, address: str) -> Decimal | None:
        try:
            address = to_checksum_address(address)

            def _get_bal(w3: Web3):
                contract = w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)
                return contract.functions.balanceOf(address).call()

            wei = await self._run_async_failover(_get_bal)
            return Decimal(wei) / Decimal(10 ** USDT_DECIMALS)
        except Exception as e:
            logger.error(f"Get balance failed: {e}")
            return None

    async def get_plex_balance(self, address: str) -> Decimal | None:
        """
        Get PLEX token balance for address.

        PLEX token uses 9 decimals (per business rules).

        Args:
            address: Wallet address to check

        Returns:
            PLEX balance in tokens or None on error
        """
        try:
            address = to_checksum_address(address)
            plex_address = to_checksum_address(self.settings.auth_plex_token_address)

            # PLEX uses standard ERC-20 ABI (same as USDT_ABI)
            def _get_bal(w3: Web3):
                contract = w3.eth.contract(address=plex_address, abi=USDT_ABI)
                return contract.functions.balanceOf(address).call()

            raw = await self._run_async_failover(_get_bal)
            # PLEX has 9 decimals
            return Decimal(raw) / Decimal(10**9)
        except Exception as e:
            logger.error(f"Get PLEX balance failed for {mask_address(address)}: {e}")
            return None

    async def estimate_gas_fee(self, to_address: str, amount: Decimal) -> Decimal | None:
        """
        Estimate gas fee for USDT transfer.

        Args:
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal)

        Returns:
            Estimated gas fee in BNB or None
        """
        try:
            to_address = to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            from decimal import ROUND_DOWN
            amount_wei = int((Decimal(str(amount)) * Decimal(10 ** USDT_DECIMALS)).to_integral_value(ROUND_DOWN))

            def _est_gas(w3: Web3):
                contract = w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)
                func = contract.functions.transfer(to_address, amount_wei)
                func_gas = func.estimate_gas({"from": self.wallet_address})
                price = self.get_optimal_gas_price(w3)
                return func_gas * price

            total_wei = await self._run_async_failover(_est_gas)
            return Decimal(total_wei) / Decimal(10 ** 18)
        except Exception:
            return None

    async def get_providers_status(self) -> dict[str, Any]:
        """Get status of all providers."""
        status = {}
        for name, w3 in self.providers.items():
            try:
                loop = asyncio.get_event_loop()
                # Run ping in executor with timeout
                try:
                    bn = await asyncio.wait_for(
                        loop.run_in_executor(
                            self._executor, lambda: w3.eth.block_number
                        ),
                        timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                    )
                    status[name] = {"connected": True, "block": bn, "active": name == self.active_provider_name}
                except TimeoutError:
                    logger.warning(f"Timeout checking provider '{name}' status")
                    status[name] = {"connected": False, "error": "Timeout", "active": name == self.active_provider_name}
            except Exception as e:
                status[name] = {"connected": False, "error": str(e), "active": name == self.active_provider_name}
        return status

    async def verify_plex_payment(
        self,
        sender_address: str,
        amount_plex: float | None = None,
        lookback_blocks: int = 200  # ~10 minutes on BSC (3 sec/block)
    ) -> dict[str, Any]:
        """
        Verify if user paid PLEX tokens to system wallet.

        Algorithm:
        1. Get all incoming PLEX transfers to system wallet (filter by 'to')
        2. Check if any transfer is from the user's wallet (check 'from' in loop)
        3. Verify amount >= required
        """
        if not self.settings.auth_plex_token_address:
            return {"success": False, "error": "PLEX token address not configured"}

        target_amount = amount_plex or self.settings.auth_price_plex
        try:
            sender = to_checksum_address(sender_address)
            receiver = to_checksum_address(self.settings.auth_system_wallet_address)
            token_address = to_checksum_address(self.settings.auth_plex_token_address)
        except ValueError as e:
            return {"success": False, "error": f"Invalid address format: {e}"}

        # PLEX uses 9 decimals
        decimals = 9
        target_wei = int(target_amount * (10 ** decimals))

        logger.info(
            f"[PLEX Verify] Searching: sender={mask_address(sender)}, "
            f"receiver={mask_address(receiver)}, required={target_amount} PLEX"
        )

        def _scan(w3: Web3):
            latest = w3.eth.block_number
            from_block = max(0, latest - lookback_blocks)

            logger.info(f"[PLEX Verify] Scanning blocks {from_block} to {latest}")

            contract = w3.eth.contract(address=token_address, abi=USDT_ABI)

            # Filter ONLY by receiver - simpler and more reliable
            logs = contract.events.Transfer.get_logs(
                fromBlock=from_block,
                toBlock='latest',
                argument_filters={'to': receiver}
            )

            logs = list(logs)
            logger.info(f"[PLEX Verify] Found {len(logs)} incoming transfers")

            logs.sort(key=lambda x: x.get('blockNumber', 0), reverse=True)

            for log in logs:
                args = log.get('args', {})
                tx_from = str(args.get('from', ''))
                value = args.get('value', 0)
                tx_hash = log.get('transactionHash', b'').hex()
                block_num = log.get('blockNumber', 0)

                # Compare addresses case-insensitive
                if tx_from.lower() == sender.lower():
                    logger.info(f"[PLEX Verify] Found TX from user: {tx_hash}")

                    if value >= target_wei:
                        amount_found = Decimal(value) / Decimal(10**decimals)
                        logger.success(
                            f"[PLEX Verify] VERIFIED! TX={tx_hash}, "
                            f"amount={amount_found} PLEX"
                        )
                        return {
                            "success": True,
                            "tx_hash": tx_hash,
                            "amount": amount_found,
                            "block": block_num
                        }
                    else:
                        logger.warning(
                            f"[PLEX Verify] Amount insufficient: {value} < {target_wei}"
                        )

            logger.warning(f"[PLEX Verify] No payment found from {sender[:10]}...")
            return {"success": False, "error": "Transaction not found"}

        try:
            return await self._run_async_failover(_scan)
        except Exception as e:
            logger.error(f"[PLEX Verify] Error: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_usdt_deposits(
        self,
        user_wallet: str,
        max_blocks: int = 100000,
    ) -> dict:
        """
        Scan all USDT Transfer events from user wallet to system wallet.

        Used to detect user's total deposit amount from blockchain history.

        Args:
            user_wallet: User's wallet address
            max_blocks: Maximum number of blocks to scan back

        Returns:
            Dict with:
            - total_amount: Decimal - sum of all USDT transfers
            - tx_count: int - number of transactions found
            - transactions: list - list of transaction details
            - success: bool
            - error: str (if failed)
        """
        try:
            sender = to_checksum_address(user_wallet)
            receiver = to_checksum_address(self.system_wallet_address)
            usdt_address = to_checksum_address(self.usdt_contract_address)

            def _scan_all(w3: Web3):
                latest = w3.eth.block_number
                from_block = max(0, latest - max_blocks)

                contract = w3.eth.contract(address=usdt_address, abi=USDT_ABI)

                # Get all Transfer events from user to system wallet
                logs = contract.events.Transfer.get_logs(
                    fromBlock=from_block,
                    toBlock='latest',
                    argument_filters={
                        'from': sender,
                        'to': receiver
                    }
                )

                transactions = []
                total_wei = 0

                for log in logs:
                    args = log.get('args', {})
                    value = args.get('value', 0)
                    total_wei += value

                    transactions.append({
                        'tx_hash': log['transactionHash'].hex(),
                        'amount': Decimal(value) / Decimal(10 ** USDT_DECIMALS),
                        'block': log['blockNumber'],
                    })

                # Sort by block number (oldest first)
                transactions.sort(key=lambda x: x['block'])

                return {
                    'total_amount': Decimal(total_wei) / Decimal(10 ** USDT_DECIMALS),
                    'tx_count': len(transactions),
                    'transactions': transactions,
                    'from_block': from_block,
                    'to_block': latest,
                }

            result = await self._run_async_failover(_scan_all)
            result['success'] = True

            logger.info(
                f"Deposit scan for {mask_address(user_wallet)}: "
                f"found {result['tx_count']} txs, total {result['total_amount']} USDT"
            )

            return result

        except Exception as e:
            logger.error(f"Deposit scan failed for {mask_address(user_wallet)}: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_amount': Decimal("0"),
                'tx_count': 0,
                'transactions': [],
            }


# Singleton initialization
_blockchain_service: BlockchainService | None = None


def get_blockchain_service() -> BlockchainService:
    global _blockchain_service
    if _blockchain_service is None:
        raise RuntimeError("BlockchainService not initialized")
    return _blockchain_service


def init_blockchain_service(settings: Settings, session_factory: Any = None) -> None:
    global _blockchain_service
    _blockchain_service = BlockchainService(settings, session_factory)
