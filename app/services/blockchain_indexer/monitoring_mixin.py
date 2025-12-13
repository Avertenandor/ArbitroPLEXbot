"""
Blockchain Indexer Monitoring Mixin.

Provides real-time monitoring of new blocks.
"""

from loguru import logger


class MonitoringMixin:
    """Mixin providing block monitoring functionality."""

    async def monitor_new_blocks(self) -> dict:
        """
        Monitor and index new blocks since last indexed.

        Should be called frequently (every 10-30 seconds).
        Only processes NEW blocks, so very fast and cheap.

        Returns:
            Dict with monitoring results including:
            - success: Whether monitoring succeeded
            - usdt: Number of USDT transactions indexed
            - plex: Number of PLEX transactions indexed
            - errors: List of any errors encountered
            - latest_block: Current blockchain block number
        """
        results = {"usdt": 0, "plex": 0, "errors": []}

        if not self.system_wallet:
            return {
                "success": False,
                "error": "System wallet not configured"
            }

        try:
            latest_block = self.w3.eth.block_number

            # Monitor USDT
            if self.usdt_address:
                try:
                    last_usdt = await self.get_last_indexed_block("USDT")
                    if last_usdt > 0 and last_usdt < latest_block:
                        result = await self._index_block_range(
                            token_type="USDT",
                            token_address=self.usdt_address,
                            from_block=last_usdt + 1,
                            to_block=latest_block,
                        )
                        results["usdt"] = result.get("indexed", 0)
                except Exception as e:
                    results["errors"].append(f"USDT: {e}")

            # Monitor PLEX
            if self.plex_address:
                try:
                    last_plex = await self.get_last_indexed_block("PLEX")
                    if last_plex > 0 and last_plex < latest_block:
                        result = await self._index_block_range(
                            token_type="PLEX",
                            token_address=self.plex_address,
                            from_block=last_plex + 1,
                            to_block=latest_block,
                        )
                        results["plex"] = result.get("indexed", 0)
                except Exception as e:
                    results["errors"].append(f"PLEX: {e}")

            await self.session.commit()

            new_txs = results["usdt"] + results["plex"]
            if new_txs > 0:
                logger.info(
                    f"[Indexer] New transactions: "
                    f"USDT={results['usdt']}, PLEX={results['plex']}"
                )

            results["success"] = True
            results["latest_block"] = latest_block

        except Exception as e:
            logger.error(f"[Indexer] Monitor error: {e}")
            results["success"] = False
            results["error"] = str(e)

        return results
