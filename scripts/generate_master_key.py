"""
Script to generate master key for existing admin.

Usage:
    python scripts/generate_master_key.py <telegram_id>

Example:
    python scripts/generate_master_key.py 123456789

Note:
    Replace 123456789 with your actual Telegram user ID.
    You can find it using @userinfobot on Telegram.
"""

import asyncio
import sys

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.repositories.admin_repository import AdminRepository
from app.services.admin_service import AdminService

# Configure logger for script
logger.remove()
logger.add(sys.stderr, level="INFO")


async def generate_master_key_for_admin(telegram_id: int) -> None:
    """
    Generate and set master key for existing admin.

    Args:
        telegram_id: Telegram ID of the admin
    """
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        admin_repo = AdminRepository(session)
        admin_service = AdminService(session)

        # Find admin
        admin = await admin_repo.get_by_telegram_id(telegram_id)

        if not admin:
            logger.error(f"Админ с Telegram ID {telegram_id} не найден!")
            return

        logger.success(
            f"Найден админ: ID={admin.id}, Role={admin.role}, "
            f"Username=@{admin.username or 'N/A'}"
        )

        # Generate new master key
        plain_master_key = admin_service.generate_master_key()
        hashed_master_key = admin_service.hash_master_key(plain_master_key)

        # Update admin
        admin.master_key = hashed_master_key
        await session.commit()

        # SECURITY: Master key should ONLY be displayed ONCE during generation
        # It will NEVER be stored in plain text or shown again
        # User MUST save it immediately

        print("\n" + "=" * 60)
        print("🔐 МАСТЕР-КЛЮЧ УСПЕШНО СГЕНЕРИРОВАН!")
        print("=" * 60)
        print(f"\nTelegram ID: {telegram_id}")
        print(f"Роль: {admin.role}")
        print(f"Username: @{admin.username or 'N/A'}")
        print("\n" + "-" * 60)
        print("📋 ВАШ МАСТЕР-КЛЮЧ (ПОКАЗАН ТОЛЬКО ОДИН РАЗ!):")
        print("-" * 60)
        print(f"\n{plain_master_key}\n")
        print("-" * 60)
        print("\n⚠️ КРИТИЧЕСКИ ВАЖНО:")
        print("• СКОПИРУЙТЕ этот ключ ПРЯМО СЕЙЧАС - он больше НЕ БУДЕТ ПОКАЗАН!")
        print("• Сохраните его в БЕЗОПАСНОМ месте (менеджер паролей)")
        print("• НЕ передавайте его третьим лицам")
        print("• НЕ храните в открытом виде (скриншоты, текстовые файлы)")
        print("• Используйте его для входа в админ-панель")
        print("• При первом входе введите /admin и затем мастер-ключ")
        print("\nДля входа в админ-панель используйте команду /admin")
        print("=" * 60)
        print("\n⚠️ ВНИМАНИЕ: После закрытия этого окна ключ будет НЕВОЗМОЖНО восстановить!")
        print("Если потеряете ключ, потребуется генерация нового.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python scripts/generate_master_key.py <telegram_id>")
        logger.info("Example: python scripts/generate_master_key.py 123456789")
        logger.info("Note: Replace with your actual Telegram user ID (find it via @userinfobot)")
        sys.exit(1)

    try:
        telegram_id = int(sys.argv[1])
    except ValueError:
        logger.error(f"Неверный Telegram ID: {sys.argv[1]}")
        logger.error("Telegram ID должен быть числом")
        sys.exit(1)

    asyncio.run(generate_master_key_for_admin(telegram_id))
