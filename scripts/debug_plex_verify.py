#!/usr/bin/env python3
"""Debug script for PLEX payment verification."""

import asyncio
import sys
sys.path.insert(0, '/app')

from web3 import Web3
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")


async def main():
    """Test PLEX verification."""
    from app.services.blockchain_service import get_blockchain_service
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
    
    # Check recent transfers TO system wallet
    print(f"\n--- Scanning for transfers to system wallet ---")
    print(f"Scanning blocks {latest-2000} to {latest}")
    
    try:
        logs = contract.events.Transfer.get_logs(
            fromBlock=latest-2000,
            toBlock='latest',
            argument_filters={'to': SYSTEM}
        )
        logs_list = list(logs)
        print(f"Found {len(logs_list)} transfers TO system wallet (last 2000 blocks)")
        
        if logs_list:
            for log in logs_list[:5]:
                args = log.get('args', {})
                from_addr = args.get('from', '')
                value = args.get('value', 0)
                tx_hash = log.get('transactionHash', b'').hex()
                amount = value / (10 ** decimals)
                print(f"  - From: {from_addr[:10]}... Amount: {amount} PLEX TX: {tx_hash[:16]}...")
    except Exception as e:
        print(f"Error getting logs: {e}")
    
    # Check ALL recent transfers
    print(f"\n--- Recent transfers on PLEX token (any direction) ---")
    try:
        all_logs = contract.events.Transfer.get_logs(
            fromBlock=latest-100,
            toBlock='latest'
        )
        all_list = list(all_logs)
        print(f"Total transfers (last 100 blocks): {len(all_list)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test through blockchain service
    print("\n--- Testing via BlockchainService ---")
    bs = get_blockchain_service()
    
    # Test with a sample address
    test_wallet = "0x399B2217B6e33d8b7c22de9f0F5F9fFCD17FfFCD"  # From logs
    
    result = await bs.verify_plex_payment(
        sender_address=test_wallet,
        amount_plex=10.0,
        lookback_blocks=2000
    )
    
    print(f"Verification result: {result}")
    
    print("\n" + "=" * 60)
    print("Debug complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
