"""Script to fix verify_plex_payment function."""
import re

# Read file
with open('app/services/blockchain_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# New function implementation
new_function = '''    async def verify_plex_payment(
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

        decimals = 18
        target_wei = int(target_amount * (10 ** decimals))
        
        logger.info(
            f"[PLEX Verify] Searching: sender={sender[:10]}..., "
            f"receiver={receiver[:10]}..., required={target_amount} PLEX"
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
            return {"success": False, "error": str(e)}'''

# Pattern to match old function (from 'async def verify_plex_payment' to next method)
pattern = r'(    async def verify_plex_payment\([\s\S]*?return \{"success": False, "error": str\(e\)\})'

# Replace
new_content = re.sub(pattern, new_function, content)

# Write back
with open('app/services/blockchain_service.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done! verify_plex_payment updated.")

