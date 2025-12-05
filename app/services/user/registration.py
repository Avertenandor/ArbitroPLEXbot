"""
User registration functionality.

Handles new user registration with referral support and fraud detection.
"""

import secrets

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.repositories.user_repository import UserRepository


class UserRegistrationMixin:
    """
    Mixin for user registration functionality.

    Handles new user registration with referral support.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user registration mixin."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.blacklist_repo = BlacklistRepository(session)

    async def register_user(
        self,
        telegram_id: int,
        wallet_address: str,
        financial_password: str,
        username: str | None = None,
        referrer_telegram_id: int | None = None,
    ) -> User:
        """
        Register new user with referral support.

        Args:
            telegram_id: Telegram user ID
            wallet_address: User's wallet address
            financial_password: Plain text password (will be hashed with bcrypt)
            username: Telegram username (optional)
            referrer_telegram_id: Referrer's Telegram ID

        Returns:
            Created user

        Raises:
            ValueError: If user already exists or blacklisted
        """
        import bcrypt

        # Check if blacklisted
        blacklist_entry = await self.blacklist_repo.get_by_telegram_id(
            telegram_id
        )
        if blacklist_entry and blacklist_entry.is_active:
            # Raise specific error with action type for proper message handling
            raise ValueError(
                f"BLACKLISTED:"
                f"{blacklist_entry.action_type or 'REGISTRATION_DENIED'}"
            )

        # Check if already exists
        existing = await self.user_repo.get_by_telegram_id(
            telegram_id
        )
        if existing:
            raise ValueError("User already registered")

        # Find referrer if provided
        referrer_id = None
        if referrer_telegram_id:
            referrer = await self.user_repo.get_by_telegram_id(
                referrer_telegram_id
            )
            if referrer:
                referrer_id = referrer.id

        # Generate unique referral code
        while True:
            referral_code = secrets.token_urlsafe(8)
            # Check if exists (unlikely collision but safe to check)
            exists = await self.user_repo.get_by_referral_code(referral_code)
            if not exists:
                break

        # Hash financial password
        hashed_password = bcrypt.hashpw(
            financial_password.encode(), bcrypt.gensalt()
        ).decode()

        # Create user
        user = await self.user_repo.create(
            telegram_id=telegram_id,
            username=username,
            wallet_address=wallet_address,
            financial_password=hashed_password,
            referrer_id=referrer_id,
            referral_code=referral_code,
        )

        await self.session.commit()

        # R10-1: Check fraud risk after registration
        from app.services.fraud_detection_service import (
            FraudDetectionService,
        )

        fraud_service = FraudDetectionService(self.session)
        await fraud_service.check_and_block_if_needed(user.id)

        # Create referral relationships if referrer exists
        if referrer_id:
            from app.services.referral_service import ReferralService

            referral_service = ReferralService(self.session)
            result = (
                await referral_service.create_referral_relationships(
                    new_user_id=user.id,
                    direct_referrer_id=referrer_id,
                )
            )
            success, error_msg = result
            if not success:
                logger.warning(
                    "Failed to create referral relationships",
                    extra={
                        "new_user_id": user.id,
                        "referrer_id": referrer_id,
                        "error": error_msg,
                    },
                )
            else:
                logger.info(
                    "Referral relationships created",
                    extra={
                        "new_user_id": user.id,
                        "referrer_id": referrer_id,
                    },
                )

        logger.info(
            "User registered",
            extra={
                "user_id": user.id,
                "telegram_id": telegram_id,
                "has_referrer": referrer_id is not None,
            },
        )

        return user
