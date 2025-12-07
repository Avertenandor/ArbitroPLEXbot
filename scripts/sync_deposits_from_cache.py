#!/usr/bin/env python3
"""
Sync Deposits from Blockchain Cache.

This script:
1. Links blockchain_tx_cache records to users by wallet_address
2. Creates deposits from incoming USDT transactions
3. Updates user.total_deposited_usdt

Run after full_history_sync.py or deep_history_sync.py to create deposits
from cached blockchain transactions.

Usage:
    python scripts/sync_deposits_from_cache.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger  # noqa: E402
from sqlalchemy import func, select, update  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from app.config.settings import settings  # noqa: E402
from app.models.blockchain_tx_cache import BlockchainTxCache  # noqa: E402
from app.models.deposit import Deposit  # noqa: E402
from app.models.user import User  # noqa: E402

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)

# Minimum deposit to be active depositor
MINIMUM_DEPOSIT_FOR_ACTIVE = Decimal("70")


async def link_transactions_to_users(session: AsyncSession) -> int:
    """
    Link blockchain_tx_cache records to users by wallet_address.
    
    Returns:
        Number of records linked
    """
    logger.info("Phase 1: Linking transactions to users by wallet_address...")
    
    # Update incoming transactions (from_address = user's wallet)
    # Use LIMIT 1 in case of duplicate wallets
    incoming_stmt = (
        update(BlockchainTxCache)
        .where(
            BlockchainTxCache.user_id.is_(None),
            BlockchainTxCache.direction == "incoming",
        )
        .values(
            user_id=select(User.id)
            .where(func.lower(User.wallet_address) == func.lower(BlockchainTxCache.from_address))
            .correlate(BlockchainTxCache)
            .limit(1)
            .scalar_subquery()
        )
    )
    
    result = await session.execute(incoming_stmt)
    incoming_linked = result.rowcount
    
    # Update outgoing transactions (to_address = user's wallet)
    outgoing_stmt = (
        update(BlockchainTxCache)
        .where(
            BlockchainTxCache.user_id.is_(None),
            BlockchainTxCache.direction == "outgoing",
        )
        .values(
            user_id=select(User.id)
            .where(func.lower(User.wallet_address) == func.lower(BlockchainTxCache.to_address))
            .correlate(BlockchainTxCache)
            .limit(1)
            .scalar_subquery()
        )
    )
    
    result = await session.execute(outgoing_stmt)
    outgoing_linked = result.rowcount
    
    await session.commit()
    
    total_linked = incoming_linked + outgoing_linked
    logger.info(f"Linked {incoming_linked} incoming + {outgoing_linked} outgoing = {total_linked} total")
    
    return total_linked


async def create_deposits_from_cache(session: AsyncSession, dry_run: bool = False) -> int:
    """
    Create deposit records from incoming USDT transactions.
    
    Returns:
        Number of deposits created
    """
    logger.info("Phase 2: Creating deposits from incoming USDT transactions...")
    
    # Get all incoming USDT transactions that have user_id but no deposit_id
    stmt = select(BlockchainTxCache).where(
        BlockchainTxCache.token_type == "USDT",
        BlockchainTxCache.direction == "incoming",
        BlockchainTxCache.user_id.isnot(None),
        BlockchainTxCache.deposit_id.is_(None),
    ).order_by(BlockchainTxCache.block_number)
    
    result = await session.execute(stmt)
    transactions = result.scalars().all()
    
    logger.info(f"Found {len(transactions)} USDT transactions to process")
    
    deposits_created = 0
    
    for tx in transactions:
        # Check if deposit with this tx_hash already exists
        existing_stmt = select(Deposit).where(Deposit.tx_hash == tx.tx_hash)
        existing_result = await session.execute(existing_stmt)
        existing_deposit = existing_result.scalar_one_or_none()
        
        if existing_deposit:
            # Link tx to existing deposit
            tx.deposit_id = existing_deposit.id
            logger.debug(f"TX {tx.tx_hash[:16]}... already has deposit {existing_deposit.id}")
            continue
        
        # Create new deposit
        now = datetime.now(UTC)
        
        # Determine level based on amount
        level = _determine_level(tx.amount)
        deposit_type = f"level_{level}" if level > 0 else "test"
        
        if not dry_run:
            deposit = Deposit(
                user_id=tx.user_id,
                level=max(level, 1),  # At least level 1
                amount=tx.amount,
                tx_hash=tx.tx_hash,
                block_number=tx.block_number,
                wallet_address=tx.from_address,
                status="confirmed",
                deposit_type=deposit_type,
                min_amount=Decimal("0"),
                max_amount=Decimal("0"),
                usdt_confirmed=True,
                usdt_confirmed_at=tx.block_timestamp or now,
                roi_cap_amount=tx.amount * Decimal("2"),  # 200% ROI cap
                roi_paid_amount=Decimal("0"),
                is_roi_completed=False,
                created_at=tx.block_timestamp or now,
                confirmed_at=tx.block_timestamp or now,
                is_consolidated=False,
                plex_cycle_start=now,
            )
            session.add(deposit)
            await session.flush()
            
            # Link tx_cache to deposit
            tx.deposit_id = deposit.id
            
        deposits_created += 1
        
        if deposits_created % 10 == 0:
            logger.info(f"Created {deposits_created} deposits...")
    
    if not dry_run:
        await session.commit()
    
    logger.info(f"Created {deposits_created} deposits from transactions")
    
    return deposits_created


def _determine_level(amount: Decimal) -> int:
    """Determine deposit level based on amount."""
    # Standard levels from deposit_validation_service
    if amount >= Decimal("3000"):
        return 5
    elif amount >= Decimal("1000"):
        return 4
    elif amount >= Decimal("500"):
        return 3
    elif amount >= Decimal("200"):
        return 2
    elif amount >= Decimal("70"):
        return 1
    else:
        return 0  # Test deposit


async def update_user_totals(session: AsyncSession, dry_run: bool = False) -> int:
    """
    Update user.total_deposited_usdt from confirmed deposits.
    
    Returns:
        Number of users updated
    """
    logger.info("Phase 3: Updating user total_deposited_usdt...")
    
    # Get all users with their deposit sums
    users_stmt = select(User)
    result = await session.execute(users_stmt)
    users = result.scalars().all()
    
    updated = 0
    
    for user in users:
        # Calculate total from confirmed deposits
        deposit_sum_stmt = select(func.coalesce(func.sum(Deposit.amount), 0)).where(
            Deposit.user_id == user.id,
            Deposit.status == "confirmed",
        )
        deposit_result = await session.execute(deposit_sum_stmt)
        deposit_total = deposit_result.scalar() or Decimal("0")
        
        # Also check blockchain_tx_cache for any unlinked transactions
        cache_sum_stmt = select(func.coalesce(func.sum(BlockchainTxCache.amount), 0)).where(
            func.lower(BlockchainTxCache.from_address) == func.lower(user.wallet_address),
            BlockchainTxCache.token_type == "USDT",
            BlockchainTxCache.direction == "incoming",
        )
        cache_result = await session.execute(cache_sum_stmt)
        cache_total = cache_result.scalar() or Decimal("0")
        
        # Use the larger of the two (deposits table is authoritative, but cache may have more)
        new_total = max(deposit_total, cache_total)
        
        if new_total != user.total_deposited_usdt:
            old_total = user.total_deposited_usdt
            
            if not dry_run:
                user.total_deposited_usdt = new_total
                user.is_active_depositor = new_total >= MINIMUM_DEPOSIT_FOR_ACTIVE
            
            updated += 1
            logger.info(
                f"User {user.id} ({user.username}): "
                f"{old_total} -> {new_total} USDT "
                f"(active: {new_total >= MINIMUM_DEPOSIT_FOR_ACTIVE})"
            )
    
    if not dry_run:
        await session.commit()
    
    logger.info(f"Updated {updated} users")
    
    return updated


async def sync_deposits(dry_run: bool = False) -> dict:
    """
    Main synchronization function.
    
    Returns:
        Dict with statistics
    """
    logger.info("=" * 60)
    logger.info("DEPOSIT SYNC FROM BLOCKCHAIN CACHE")
    logger.info(f"Dry Run: {dry_run}")
    logger.info("=" * 60)
    
    # Create database connection
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    stats = {
        "transactions_linked": 0,
        "deposits_created": 0,
        "users_updated": 0,
    }
    
    async with session_factory() as session:
        # Phase 1: Link transactions to users
        if not dry_run:
            stats["transactions_linked"] = await link_transactions_to_users(session)
        else:
            # Count how many would be linked
            count_stmt = select(func.count(BlockchainTxCache.id)).where(
                BlockchainTxCache.user_id.is_(None),
            )
            result = await session.execute(count_stmt)
            stats["transactions_linked"] = result.scalar() or 0
            logger.info(f"Would link ~{stats['transactions_linked']} transactions")
        
        # Phase 2: Create deposits
        stats["deposits_created"] = await create_deposits_from_cache(session, dry_run)
        
        # Phase 3: Update user totals
        stats["users_updated"] = await update_user_totals(session, dry_run)
    
    await engine.dispose()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SYNC SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Transactions linked: {stats['transactions_linked']}")
    logger.info(f"Deposits created: {stats['deposits_created']}")
    logger.info(f"Users updated: {stats['users_updated']}")
    
    if dry_run:
        logger.info("\n⚠️ DRY RUN - No changes were made")
    
    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync deposits from blockchain cache"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate sync without making changes",
    )
    
    args = parser.parse_args()
    
    asyncio.run(sync_deposits(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
