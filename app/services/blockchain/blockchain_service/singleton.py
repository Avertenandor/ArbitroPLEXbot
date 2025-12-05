"""
Singleton Module.

Contains singleton pattern implementation for the BlockchainService.
"""

from loguru import logger


# Module-level singleton instance
_blockchain_service = None


def get_blockchain_service():
    """
    Get blockchain service singleton.

    Returns:
        BlockchainService instance

    Raises:
        RuntimeError: If not initialized
    """
    global _blockchain_service

    if _blockchain_service is None:
        raise RuntimeError(
            "BlockchainService not initialized. "
            "Call init_blockchain_service() first."
        )

    return _blockchain_service


def init_blockchain_service(
    https_url: str,
    wss_url: str,
    usdt_contract_address: str,
    system_wallet_address: str,
    payout_wallet_address: str,
    payout_wallet_private_key: str | None = None,
    chain_id: int = 56,
    confirmation_blocks: int = 12,
    poll_interval: int = 3,
):
    """
    Initialize blockchain service singleton.

    Args:
        https_url: QuickNode HTTPS URL
        wss_url: QuickNode WebSocket URL
        usdt_contract_address: USDT contract address
        system_wallet_address: System deposit wallet
        payout_wallet_address: Payout wallet
        payout_wallet_private_key: Private key for payouts
        chain_id: BSC chain ID
        confirmation_blocks: Required confirmations
        poll_interval: Event polling interval

    Returns:
        BlockchainService instance
    """
    global _blockchain_service

    # Import here to avoid circular import
    from .service import BlockchainService

    _blockchain_service = BlockchainService(
        https_url=https_url,
        wss_url=wss_url,
        usdt_contract_address=usdt_contract_address,
        system_wallet_address=system_wallet_address,
        payout_wallet_address=payout_wallet_address,
        payout_wallet_private_key=payout_wallet_private_key,
        chain_id=chain_id,
        confirmation_blocks=confirmation_blocks,
        poll_interval=poll_interval,
    )

    logger.info("BlockchainService singleton initialized")

    return _blockchain_service
