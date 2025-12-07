#!/usr/bin/env python3
"""
Sync Users Deposits Script.

Syncs all users' total_deposited_usdt with blockchain cache.
Should be run periodically or after deep_history_sync.
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.models.user import User
from app.models.blockchain_tx_cache import BlockchainTxCache


MINIMUM_DEPOSIT_FOR_ACTIVE = Decimal("70")


async def sync_user_deposits():
    """Sync all users' deposits from blockchain cache."""
    
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with session_maker() as session:
        # Get all users
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()
        
        updated_count = 0
        
        for user in users:
            if not user.wallet_address:
                continue
            
            wallet = user.wallet_address.lower()
            
            # Get sum of incoming USDT from cache
            sum_query = select(func.coalesce(func.sum(BlockchainTxCache.amount), 0)).where(
                func.lower(BlockchainTxCache.from_address) == wallet,
                BlockchainTxCache.token_type == "USDT",
                BlockchainTxCache.direction == "incoming",
            )
            
            result = await session.execute(sum_query)
            cache_total = result.scalar() or Decimal("0")
            
            # Get transaction count
            count_query = select(func.count(BlockchainTxCache.id)).where(
                func.lower(BlockchainTxCache.from_address) == wallet,
                BlockchainTxCache.token_type == "USDT",
                BlockchainTxCache.direction == "incoming",
            )
            count_result = await session.execute(count_query)
            tx_count = count_result.scalar() or 0
            
            # Check if update needed
            old_total = user.total_deposited_usdt or Decimal("0")
            
            if old_total != cache_total:
                user.total_deposited_usdt = cache_total
                user.is_active_depositor = cache_total >= MINIMUM_DEPOSIT_FOR_ACTIVE
                user.deposit_tx_count = tx_count
                
                logger.info(
                    f"Updated {user.username}: "
                    f"{old_total} -> {cache_total} USDT "
                    f"(active: {user.is_active_depositor})"
                )
                updated_count += 1
        
        await session.commit()
        logger.info(f"Sync complete. Updated {updated_count} users.")
    
    await engine.dispose()
    return updated_count


if __name__ == "__main__":
    logger.info("Starting user deposits sync...")
    result = asyncio.run(sync_user_deposits())
    logger.info(f"Done. Updated {result} users.")
