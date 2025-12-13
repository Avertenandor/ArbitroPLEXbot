"""
Check for placeholder wallet addresses in the database.

This script identifies users with placeholder wallet addresses
(generated during import for users without real wallets).
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.user import User


async def check_placeholder_wallets():
    """Find all users with placeholder wallet addresses."""
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Count total users
        total_count = await session.scalar(select(func.count(User.id)))
        logger.info(f"📊 Всего пользователей в базе: {total_count}")
        
        # Find users with placeholder wallets
        query = select(User).where(
            User.wallet_address.ilike('%placeholder%')
        ).order_by(User.id)
        
        result = await session.execute(query)
        placeholder_users = result.scalars().all()
        
        if placeholder_users:
            logger.warning(f"⚠️ Найдено {len(placeholder_users)} пользователей с placeholder-адресами:")
            for user in placeholder_users:
                logger.warning(
                    f"  ID={user.id}, TG={user.telegram_id}, "
                    f"@{user.username or 'N/A'}, "
                    f"wallet={user.wallet_address[:30]}..."
                )
        else:
            logger.success("✅ Placeholder-адреса не найдены!")
        
        # Find users with invalid hex wallets (not starting with 0x or not 42 chars)
        all_users = await session.execute(select(User))
        all_users = all_users.scalars().all()
        
        invalid_wallets = []
        for user in all_users:
            wallet = user.wallet_address
            if not wallet:
                invalid_wallets.append((user, "пустой адрес"))
            elif not wallet.startswith("0x"):
                invalid_wallets.append((user, "не начинается с 0x"))
            elif len(wallet) != 42:
                invalid_wallets.append((user, f"длина {len(wallet)}, должна быть 42"))
            else:
                # Check if it's valid hex
                try:
                    int(wallet[2:], 16)
                except ValueError:
                    invalid_wallets.append((user, "содержит не-hex символы"))
        
        if invalid_wallets:
            logger.warning(f"⚠️ Найдено {len(invalid_wallets)} пользователей с невалидными адресами:")
            for user, reason in invalid_wallets:
                logger.warning(
                    f"  ID={user.id}, TG={user.telegram_id}, "
                    f"@{user.username or 'N/A'}, "
                    f"причина: {reason}, "
                    f"wallet={user.wallet_address[:30] if user.wallet_address else 'None'}..."
                )
        else:
            logger.success("✅ Все адреса валидные!")
        
        # Check users with deposits but 0 balance
        users_with_deposits = await session.execute(
            select(User).where(
                User.total_deposited_usdt > 0,
                User.balance == 0
            )
        )
        users_with_deposits = users_with_deposits.scalars().all()
        
        if users_with_deposits:
            logger.info(f"📊 Пользователей с депозитами но 0 балансом: {len(users_with_deposits)}")
            for user in users_with_deposits[:10]:  # First 10
                logger.info(
                    f"  ID={user.id}, TG={user.telegram_id}, "
                    f"@{user.username or 'N/A'}, "
                    f"deposited={user.total_deposited_usdt} USDT"
                )
        
        # Check users marked as active depositors
        active_depositors = await session.execute(
            select(User).where(User.is_active_depositor == True)
        )
        active_depositors = active_depositors.scalars().all()
        logger.info(f"📊 Активных депозиторов (is_active_depositor=True): {len(active_depositors)}")
        
        # Check for bonus credits
        from app.models.bonus_credit import BonusCredit
        bonus_count = await session.scalar(select(func.count(BonusCredit.id)))
        bonus_sum = await session.scalar(
            select(func.sum(BonusCredit.amount)).where(BonusCredit.is_active == True)
        )
        logger.info(f"📊 Бонусных кредитов: {bonus_count}, активная сумма: {bonus_sum or 0} USDT")
        
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_placeholder_wallets())
