#!/usr/bin/env python3
"""Debug script for PLEX payment verification."""

import asyncio
import sys


sys.path.insert(0, '/app')

from loguru import logger
from web3 import Web3


# Configure logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")


async def main():
    """Test PLEX verification."""
    from app.config.settings import settings

    print("=" * 60)
    print("PLEX Payment Verification Debug")
    print("=" * 60)

    print(f"\nPLEX Token Address: {settings.auth_plex_token_address}")
    print(f"System Wallet Address: {settings.auth_system_wallet_address}")
    print(f"Auth Price PLEX: {settings.auth_price_plex}")

    # Direct Web3 test
    print("\n--- Direct Web3 Test ---")
    w3 = Web3(Web3.HTTPProvider('https://bsc-dataseed1.binance.org'))
    print(f"Connected: {w3.is_connected()}")
    print(f"Latest block: {w3.eth.block_number}")

    # Check PLEX token contract
    PLEX = w3.to_checksum_address(settings.auth_plex_token_address)
    SYSTEM = w3.to_checksum_address(settings.auth_system_wallet_address)

    ABI = [
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
        {
            "constant": True,
            "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    contract = w3.eth.contract(address=PLEX, abi=ABI)

    # Check decimals
    try:
        decimals = contract.functions.decimals().call()
        print(f"PLEX Decimals: {decimals}")
    except Exception as e:
        print(f"Error getting decimals: {e}")
        decimals = 9

    # Check system wallet balance
    try:
        balance = contract.functions.balanceOf(SYSTEM).call()
        balance_formatted = balance / (10 ** decimals)
        print(f"System Wallet PLEX Balance: {balance_formatted}")
    except Exception as e:
        print(f"Error getting balance: {e}")

    latest = w3.eth.block_number

    # Check recent transfers TO system wallet - scan in chunks
    print("\n--- Scanning for transfers to system wallet (in chunks) ---")
    chunk_size = 100
    total_blocks = 1000

    all_logs = []
    for offset in range(0, total_blocks, chunk_size):
        from_blk = max(0, latest - offset - chunk_size)
        to_blk = latest - offset
        if from_blk >= to_blk:
            continue
        try:
            logs = contract.events.Transfer.get_logs(
                fromBlock=from_blk,
                toBlock=to_blk,
                argument_filters={'to': SYSTEM}
            )
            chunk_logs = list(logs)
            all_logs.extend(chunk_logs)
            print(f"  Blocks {from_blk}-{to_blk}: {len(chunk_logs)} logs")
        except Exception as e:
            print(f"  Blocks {from_blk}-{to_blk}: Error - {e}")

    print(f"\nTotal found: {len(all_logs)} transfers TO system wallet")

    if all_logs:
        print("\nRecent transfers:")
        for log in all_logs[:5]:
            args = log.get('args', {})
            from_addr = args.get('from', '')
            value = args.get('value', 0)
            tx_hash = log.get('transactionHash', b'').hex()
            amount = value / (10 ** decimals)
            print(f"  - From: {from_addr[:10]}... Amount: {amount} PLEX")
            print(f"    TX: {tx_hash}")

    print("\n" + "=" * 60)
    print("Debug complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
