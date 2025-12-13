#!/usr/bin/env python3
"""
Script to clean up placeholder wallet addresses in the database.

This script:
1. Finds all users with placeholder wallet addresses
2. Clears their wallet_address field (sets to a special marker or null-like value)
3. Marks them as needing wallet verification
4. Logs all changes for audit

Usage:
    python scripts/cleanup_placeholder_wallets.py --dry-run  # Preview changes
    python scripts/cleanup_placeholder_wallets.py            # Apply changes

NOTE: Run this on the server where database is accessible!
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.user import User


# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


async def find_placeholder_wallets(session: AsyncSession) -> list[User]:
    """Find all users with placeholder wallet addresses."""
    result = await session.execute(
        select(User).where(
            User.wallet_address.ilike('%placeholder%')
        ).order_by(User.id)
    )
    return list(result.scalars().all())


async def find_invalid_wallets(session: AsyncSession) -> list[tuple[User, str]]:
    """Find all users with invalid (non-hex) wallet addresses."""
    result = await session.execute(select(User))
    all_users = result.scalars().all()
    
    invalid = []
    for user in all_users:
        wallet = user.wallet_address
        if not wallet:
            invalid.append((user, "пустой адрес"))
        elif not wallet.startswith("0x"):
            invalid.append((user, "не начинается с 0x"))
        elif len(wallet) != 42:
            invalid.append((user, f"длина {len(wallet)}, должна быть 42"))
        else:
            # Check if it's valid hex
            try:
                int(wallet[2:], 16)
            except ValueError:
                invalid.append((user, "содержит не-hex символы"))
    
    return invalid


async def cleanup_placeholder_wallets(dry_run: bool = True):
    """
    Clean up placeholder wallet addresses.
    
    Strategy:
    - Generate a unique invalid-but-trackable address for each user
    - Format: 0x0000000000000000000000000000000000000000 (zero address)
    - This allows the system to detect "needs wallet binding" state
    """
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    logger.info("=" * 60)
    logger.info("CLEANUP PLACEHOLDER WALLET ADDRESSES")
    logger.info(f"Mode: {'DRY RUN (preview only)' if dry_run else 'APPLY CHANGES'}")
    logger.info("=" * 60)
    
    async with async_session() as session:
        # 1. Find placeholder wallets
        placeholder_users = await find_placeholder_wallets(session)
        logger.info(f"\n📊 Found {len(placeholder_users)} users with placeholder addresses")
        
        if placeholder_users:
            for user in placeholder_users:
                logger.warning(
                    f"  ID={user.id}, TG={user.telegram_id}, "
                    f"@{user.username or 'N/A'}, "
                    f"wallet={user.wallet_address[:35]}..."
                )
                
                # Check if user has deposits or bonuses
                total_dep = user.total_deposited_usdt or 0
                bonus = user.bonus_balance or 0
                if total_dep > 0 or bonus > 0:
                    logger.error(
                        f"    ⚠️ HAS FUNDS! deposits={total_dep}, bonus={bonus}"
                    )
        
        # 2. Find other invalid wallets
        invalid_users = await find_invalid_wallets(session)
        non_placeholder_invalid = [
            (u, r) for u, r in invalid_users 
            if 'placeholder' not in (u.wallet_address or '').lower()
        ]
        
        if non_placeholder_invalid:
            logger.info(f"\n📊 Found {len(non_placeholder_invalid)} OTHER invalid wallet addresses")
            for user, reason in non_placeholder_invalid[:10]:
                logger.warning(
                    f"  ID={user.id}, TG={user.telegram_id}, "
                    f"reason: {reason}, "
                    f"wallet={user.wallet_address[:30] if user.wallet_address else 'None'}..."
                )
        
        # 3. Summary
        total_count = await session.scalar(select(func.count(User.id)))
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"  Total users: {total_count}")
        logger.info(f"  Placeholder wallets: {len(placeholder_users)}")
        logger.info(f"  Other invalid wallets: {len(non_placeholder_invalid)}")
        logger.info(f"  Valid wallets: {total_count - len(placeholder_users) - len(non_placeholder_invalid)}")
        
        if not dry_run and placeholder_users:
            logger.info("\n🔧 APPLYING CHANGES...")
            
            # Use zero address as "no wallet" marker
            # This is a standard practice - zero address is invalid for real transactions
            ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
            
            for user in placeholder_users:
                old_wallet = user.wallet_address
                user.wallet_address = ZERO_ADDRESS
                user.is_verified = False  # Require re-verification
                
                logger.info(
                    f"  Updated user {user.id} (TG={user.telegram_id}): "
                    f"wallet cleared, is_verified=False"
                )
            
            await session.commit()
            logger.success(f"\n✅ Updated {len(placeholder_users)} users")
            logger.info("These users will need to bind a real wallet address.")
        
        elif not dry_run:
            logger.info("\n✅ No placeholder wallets found - nothing to clean up!")
    
    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Clean up placeholder wallet addresses"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (required to make actual changes)"
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("Please specify --dry-run to preview or --apply to make changes")
        print("Example: python scripts/cleanup_placeholder_wallets.py --dry-run")
        sys.exit(1)
    
    dry_run = not args.apply
    asyncio.run(cleanup_placeholder_wallets(dry_run=dry_run))


if __name__ == "__main__":
    main()
