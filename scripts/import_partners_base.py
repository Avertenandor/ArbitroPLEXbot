#!/usr/bin/env python3
"""
Import initial partners database from CSV file.

This script imports users from the legacy partner database and establishes
referral relationships between them.

CSV Structure:
- user_id: Legacy system ID (not used as our ID)
- tg_id: Telegram ID (unique identifier)
- username: Telegram username
- first_name: First name
- last_name: Last name
- lang: Language code
- is_bot: Bot flag (always 0)
- created_at: Registration date
- referrer_tg_id: Referrer's Telegram ID (who invited)
- primary_wallet: BSC wallet address

Usage:
    python scripts/import_partners_base.py [--dry-run]

Arguments:
    --dry-run: Simulate import without making changes
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import secrets
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt  # noqa: E402
from loguru import logger  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import settings  # noqa: E402
from app.models.referral import Referral  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.referral.config import REFERRAL_DEPTH  # noqa: E402


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)


def generate_referral_code(telegram_id: int) -> str:
    """Generate unique referral code from telegram ID."""
    hash_input = f"{telegram_id}_{secrets.token_hex(4)}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()


def generate_temp_password() -> str:
    """Generate temporary financial password."""
    password = secrets.token_hex(4)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def load_csv_data(csv_path: str) -> list[dict]:
    """Load and parse CSV file."""
    logger.info(f"Loading CSV from: {csv_path}")

    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cleaned_row = {k.strip(): v for k, v in row.items()}
            rows.append(cleaned_row)

    logger.info(f"Loaded {len(rows)} rows from CSV")
    return rows


async def get_existing_users(session: AsyncSession) -> dict[int, User]:
    """Get all existing users by telegram_id."""
    result = await session.execute(select(User))
    users = result.scalars().all()
    return {u.telegram_id: u for u in users}


def create_user_from_row(row: dict, referrer_id: int | None) -> User:
    """Create a User object from CSV row."""
    telegram_id = int(row["tg_id"])
    wallet = row.get("primary_wallet", "").strip()

    # If no wallet, generate unique placeholder based on telegram_id
    if not wallet or len(wallet) < 42:
        # Generate unique placeholder: 0xPLACEHOLDER + telegram_id in hex
        wallet = f"0xplaceholder{telegram_id:032x}"[-42:]

    # Parse created_at
    created_at_str = row.get("created_at", "")
    try:
        created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        created_at = datetime.utcnow()

    # Create user
    user = User(
        telegram_id=telegram_id,
        username=row.get("username") or None,
        wallet_address=wallet.lower() if wallet.startswith("0x") else wallet,
        financial_password=generate_temp_password(),
        referral_code=generate_referral_code(telegram_id),
        referrer_id=referrer_id,
        language=row.get("lang", "ru") or "ru",
        is_active=True,
        is_verified=False,
        balance=Decimal("0"),
        total_earned=Decimal("0"),
        pending_earnings=Decimal("0"),
    )
    user.created_at = created_at

    return user


async def create_referral_chain(
    session: AsyncSession,
    new_user_id: int,
    direct_referrer_id: int,
) -> int:
    """
    Create referral relationships for a user.

    Returns number of referral records created.
    """
    created_count = 0
    current_user_id = direct_referrer_id
    level = 1

    while current_user_id and level <= REFERRAL_DEPTH:
        # Check if referral already exists
        exists = await session.execute(
            select(Referral).where(
                Referral.referrer_id == current_user_id,
                Referral.referral_id == new_user_id,
            )
        )
        if not exists.scalar_one_or_none():
            # Create referral record
            referral = Referral(
                referrer_id=current_user_id,
                referral_id=new_user_id,
                level=level,
                total_earned=Decimal("0"),
            )
            session.add(referral)
            created_count += 1

        # Move up the chain
        stmt = select(User).where(User.id == current_user_id)
        result = await session.execute(stmt)
        current_user = result.scalar_one_or_none()

        if current_user and current_user.referrer_id:
            current_user_id = current_user.referrer_id
            level += 1
        else:
            break

    return created_count


async def _phase1_create_users(
    session: AsyncSession,
    rows: list[dict],
    existing_users: dict[int, User],
    dry_run: bool,
) -> tuple[dict[int, User], int, int]:
    """Phase 1: Create all users without referrer_id."""
    logger.info("\n--- PHASE 1: Creating users ---")
    tg_to_new_user: dict[int, User] = {}
    users_created = 0
    errors = 0

    for row in rows:
        tg_id = int(row["tg_id"])
        if tg_id in existing_users:
            logger.debug(f"User {tg_id} already exists, skipping")
            continue

        try:
            user = create_user_from_row(row, None)
            if not dry_run:
                session.add(user)
            tg_to_new_user[tg_id] = user
            users_created += 1
            if users_created % 100 == 0:
                logger.info(f"Created {users_created} users...")
        except Exception as e:
            logger.error(f"Error creating user {tg_id}: {e}")
            errors += 1

    if not dry_run:
        await session.commit()
        for user in tg_to_new_user.values():
            await session.refresh(user)

    logger.info(f"Created {users_created} new users")
    return tg_to_new_user, users_created, errors


async def _phase2_set_referrers(
    session: AsyncSession,
    rows: list[dict],
    all_users: dict[int, User],
    dry_run: bool,
) -> int:
    """Phase 2: Set referrer_id for all new users."""
    logger.info("\n--- PHASE 2: Setting referrer_id ---")
    referrer_set_count = 0

    for row in rows:
        tg_id = int(row["tg_id"])
        referrer_tg_id_str = row.get("referrer_tg_id", "").strip()
        if not referrer_tg_id_str:
            continue

        try:
            referrer_tg_id = int(referrer_tg_id_str)
        except ValueError:
            continue

        user = all_users.get(tg_id)
        referrer = all_users.get(referrer_tg_id)
        if not user or not referrer:
            if not referrer:
                logger.warning(f"Referrer {referrer_tg_id} not found for user {tg_id}")
            continue

        if user.referrer_id is None and referrer.id:
            if not dry_run:
                user.referrer_id = referrer.id
            referrer_set_count += 1

    if not dry_run:
        await session.commit()

    logger.info(f"Set referrer_id for {referrer_set_count} users")
    return referrer_set_count


async def _phase3_create_referral_chains(
    session: AsyncSession,
    rows: list[dict],
    all_users: dict[int, User],
    dry_run: bool,
) -> tuple[int, int]:
    """Phase 3: Create referral chain records."""
    logger.info("\n--- PHASE 3: Creating referral chains ---")
    referrals_created = 0
    errors = 0

    for row in rows:
        tg_id = int(row["tg_id"])
        referrer_tg_id_str = row.get("referrer_tg_id", "").strip()
        if not referrer_tg_id_str:
            continue

        try:
            referrer_tg_id = int(referrer_tg_id_str)
        except ValueError:
            continue

        user = all_users.get(tg_id)
        referrer = all_users.get(referrer_tg_id)
        if not user or not referrer or not user.id or not referrer.id:
            continue

        try:
            if not dry_run:
                count = await create_referral_chain(session, user.id, referrer.id)
                referrals_created += count
            else:
                referrals_created += 1
        except Exception as e:
            logger.error(f"Error creating referral chain for {tg_id}: {e}")
            errors += 1

    if not dry_run:
        await session.commit()

    logger.info(f"Created {referrals_created} referral records")
    return referrals_created, errors


async def import_partners(csv_path: str, dry_run: bool = False) -> tuple[int, int, int]:
    """
    Import partners from CSV file.

    Returns:
        Tuple of (users_created, referrals_created, errors)
    """
    logger.info("=" * 60)
    logger.info("PARTNER DATABASE IMPORT")
    logger.info(f"CSV File: {csv_path}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info("=" * 60)

    rows = await load_csv_data(csv_path)

    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        existing_users = await get_existing_users(session)
        logger.info(f"Found {len(existing_users)} existing users in database")

        # Phase 1: Create users
        tg_to_new_user, users_created, errors = await _phase1_create_users(
            session, rows, existing_users, dry_run
        )

        # Build complete mapping
        all_users: dict[int, User] = {**existing_users, **tg_to_new_user}

        # Phase 2: Set referrer_id
        await _phase2_set_referrers(session, rows, all_users, dry_run)

        # Phase 3: Create referral chains
        referrals_created, phase3_errors = await _phase3_create_referral_chains(
            session, rows, all_users, dry_run
        )
        errors += phase3_errors

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("IMPORT SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Users created: {users_created}")
    logger.info(f"Referral records created: {referrals_created}")
    logger.info(f"Errors: {errors}")

    if dry_run:
        logger.info("\n⚠️ DRY RUN - No changes were made to the database")

    await engine.dispose()

    return users_created, referrals_created, errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Import partners database from CSV")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate import without making changes",
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default="первичная база партнеров.csv",
        help="Path to CSV file (default: первичная база партнеров.csv)",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        csv_path = Path(__file__).parent.parent / args.csv_path

    if not csv_path.exists():
        logger.error(f"CSV file not found: {args.csv_path}")
        sys.exit(1)

    users, referrals, errors = asyncio.run(
        import_partners(
            str(csv_path),
            dry_run=args.dry_run,
        )
    )

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
