"""
Contract Manager - Centralized contract instantiation and management.

Eliminates repeated contract instantiation across the codebase.
"""

from decimal import Decimal
from typing import Any

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3
from web3.contract import Contract

from .constants import USDT_ABI, USDT_DECIMALS


class ContractManager:
    """
    Manages smart contract instances and interactions.

    Features:
    - Lazy loading of contracts (created only when first accessed)
    - Centralized contract instantiation
    - Token balance queries
    - Event decoding utilities
    """

    # Token decimals
    USDT_DECIMALS = USDT_DECIMALS  # 18
    PLEX_DECIMALS = 9  # PLEX token uses 9 decimals

    def __init__(
        self,
        web3: Web3,
        usdt_address: str,
        plex_address: str | None = None,
    ) -> None:
        """
        Initialize contract manager.

        Args:
            web3: Web3 instance
            usdt_address: USDT contract address
            plex_address: PLEX contract address (optional)
        """
        self.web3 = web3

        # Store addresses as checksummed
        self.usdt_address = to_checksum_address(usdt_address)
        self.plex_address = (
            to_checksum_address(plex_address) if plex_address else None
        )

        # Lazy-loaded contract instances
        self._usdt_contract: Contract | None = None
        self._plex_contract: Contract | None = None

        logger.debug(
            f"ContractManager initialized: USDT={self.usdt_address}, "
            f"PLEX={self.plex_address or 'Not configured'}"
        )

    @property
    def usdt_contract(self) -> Contract:
        """
        Get USDT contract instance (lazy loaded).

        Returns:
            USDT Contract instance
        """
        if self._usdt_contract is None:
            self._usdt_contract = self._create_usdt_contract()
            logger.debug(f"USDT contract created: {self.usdt_address}")
        return self._usdt_contract

    @property
    def plex_contract(self) -> Contract:
        """
        Get PLEX contract instance (lazy loaded).

        Returns:
            PLEX Contract instance

        Raises:
            ValueError: If PLEX address not configured
        """
        if self.plex_address is None:
            raise ValueError("PLEX contract address not configured")

        if self._plex_contract is None:
            self._plex_contract = self._create_plex_contract()
            logger.debug(f"PLEX contract created: {self.plex_address}")
        return self._plex_contract

    def _create_usdt_contract(self) -> Contract:
        """
        Create USDT contract instance.

        Returns:
            USDT Contract
        """
        return self.web3.eth.contract(
            address=self.usdt_address,
            abi=USDT_ABI,
        )

    def _create_plex_contract(self) -> Contract:
        """
        Create PLEX contract instance.

        PLEX uses the same ERC-20 ABI as USDT.

        Returns:
            PLEX Contract
        """
        return self.web3.eth.contract(
            address=self.plex_address,
            abi=USDT_ABI,  # PLEX uses standard ERC-20
        )

    def get_token_contract(self, token_address: str) -> Contract:
        """
        Get contract instance for any ERC-20 token.

        Args:
            token_address: Token contract address

        Returns:
            Contract instance
        """
        checksum_address = to_checksum_address(token_address)
        return self.web3.eth.contract(
            address=checksum_address,
            abi=USDT_ABI,  # Use standard ERC-20 ABI
        )

    async def get_usdt_balance(self, address: str) -> Decimal:
        """
        Get USDT balance for address.

        Args:
            address: Wallet address

        Returns:
            USDT balance in tokens

        Raises:
            Exception: If balance query fails
        """
        try:
            checksum_address = to_checksum_address(address)
            balance_wei = self.usdt_contract.functions.balanceOf(
                checksum_address
            ).call()
            return Decimal(balance_wei) / Decimal(10**self.USDT_DECIMALS)
        except Exception as e:
            logger.error(f"Failed to get USDT balance for {address}: {e}")
            raise

    async def get_plex_balance(self, address: str) -> Decimal:
        """
        Get PLEX balance for address.

        Args:
            address: Wallet address

        Returns:
            PLEX balance in tokens

        Raises:
            Exception: If balance query fails
        """
        try:
            checksum_address = to_checksum_address(address)
            balance_wei = self.plex_contract.functions.balanceOf(
                checksum_address
            ).call()
            return Decimal(balance_wei) / Decimal(10**self.PLEX_DECIMALS)
        except Exception as e:
            logger.error(f"Failed to get PLEX balance for {address}: {e}")
            raise

    async def get_token_balance(
        self,
        token_address: str,
        wallet: str,
        decimals: int = 18,
    ) -> Decimal:
        """
        Get balance for any ERC-20 token.

        Args:
            token_address: Token contract address
            wallet: Wallet address to check
            decimals: Token decimals (default: 18)

        Returns:
            Token balance

        Raises:
            Exception: If balance query fails
        """
        try:
            contract = self.get_token_contract(token_address)
            checksum_wallet = to_checksum_address(wallet)

            balance_wei = contract.functions.balanceOf(checksum_wallet).call()
            return Decimal(balance_wei) / Decimal(10**decimals)
        except Exception as e:
            logger.error(
                f"Failed to get token balance for {wallet} "
                f"(token={token_address}): {e}"
            )
            raise

    def decode_transfer_event(self, log: dict[str, Any]) -> dict[str, Any]:
        """
        Decode Transfer event from transaction log.

        Args:
            log: Transaction log entry

        Returns:
            Dict with:
            - from_address: Sender address
            - to_address: Recipient address
            - value: Amount in wei
            - value_decimal: Amount in tokens (for USDT, using 18 decimals)
            - tx_hash: Transaction hash
            - block_number: Block number

        Raises:
            Exception: If decoding fails
        """
        try:
            args = log.get("args", {})
            value_wei = args.get("value", 0)

            return {
                "from_address": to_checksum_address(args.get("from", "")),
                "to_address": to_checksum_address(args.get("to", "")),
                "value": value_wei,
                "value_decimal": Decimal(value_wei)
                / Decimal(10**self.USDT_DECIMALS),
                "tx_hash": log.get("transactionHash", b"").hex()
                if isinstance(log.get("transactionHash"), bytes)
                else log.get("transactionHash", ""),
                "block_number": log.get("blockNumber", 0),
            }
        except Exception as e:
            logger.error(f"Failed to decode transfer event: {e}")
            raise

    def decode_plex_transfer_event(
        self, log: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Decode PLEX Transfer event from transaction log.

        Args:
            log: Transaction log entry

        Returns:
            Dict with decoded event data (using PLEX 9 decimals)
        """
        try:
            args = log.get("args", {})
            value_wei = args.get("value", 0)

            return {
                "from_address": to_checksum_address(args.get("from", "")),
                "to_address": to_checksum_address(args.get("to", "")),
                "value": value_wei,
                "value_decimal": Decimal(value_wei)
                / Decimal(10**self.PLEX_DECIMALS),
                "tx_hash": log.get("transactionHash", b"").hex()
                if isinstance(log.get("transactionHash"), bytes)
                else log.get("transactionHash", ""),
                "block_number": log.get("blockNumber", 0),
            }
        except Exception as e:
            logger.error(f"Failed to decode PLEX transfer event: {e}")
            raise

    def decode_token_transfer_event(
        self,
        log: dict[str, Any],
        decimals: int = 18,
    ) -> dict[str, Any]:
        """
        Decode Transfer event for any token.

        Args:
            log: Transaction log entry
            decimals: Token decimals

        Returns:
            Dict with decoded event data
        """
        try:
            args = log.get("args", {})
            value_wei = args.get("value", 0)

            return {
                "from_address": to_checksum_address(args.get("from", "")),
                "to_address": to_checksum_address(args.get("to", "")),
                "value": value_wei,
                "value_decimal": Decimal(value_wei) / Decimal(10**decimals),
                "tx_hash": log.get("transactionHash", b"").hex()
                if isinstance(log.get("transactionHash"), bytes)
                else log.get("transactionHash", ""),
                "block_number": log.get("blockNumber", 0),
            }
        except Exception as e:
            logger.error(
                f"Failed to decode token transfer event (decimals={decimals}): {e}"
            )
            raise

    def get_transfer_logs(
        self,
        from_address: str | None = None,
        to_address: str | None = None,
        from_block: int = 0,
        to_block: int | str = "latest",
        token_contract: Contract | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get Transfer event logs from blockchain.

        Args:
            from_address: Filter by sender address (optional)
            to_address: Filter by recipient address (optional)
            from_block: Starting block number
            to_block: Ending block number or 'latest'
            token_contract: Contract to query (defaults to USDT)

        Returns:
            List of Transfer event logs
        """
        contract = token_contract or self.usdt_contract

        # Build argument filters
        argument_filters = {}
        if from_address:
            argument_filters["from"] = to_checksum_address(from_address)
        if to_address:
            argument_filters["to"] = to_checksum_address(to_address)

        try:
            logs = contract.events.Transfer.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters=argument_filters if argument_filters else None,
            )
            return list(logs)
        except Exception as e:
            logger.error(
                f"Failed to get transfer logs "
                f"(from={from_address}, to={to_address}): {e}"
            )
            raise

    def decode_function_input(
        self, transaction_input: str, contract: Contract | None = None
    ) -> tuple[Any, dict[str, Any]] | None:
        """
        Decode function call from transaction input data.

        Args:
            transaction_input: Transaction input data (hex string)
            contract: Contract instance (defaults to USDT)

        Returns:
            Tuple of (function, parameters) or None if decoding fails
        """
        contract = contract or self.usdt_contract

        try:
            decoded = contract.decode_function_input(transaction_input)
            return decoded
        except Exception as e:
            logger.debug(f"Failed to decode function input: {e}")
            return None

    def reset_contracts(self) -> None:
        """
        Reset cached contract instances.

        Useful when Web3 instance changes.
        """
        self._usdt_contract = None
        self._plex_contract = None
        logger.debug("Contract instances reset")
