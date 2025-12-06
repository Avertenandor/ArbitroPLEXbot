"""
Referral code parsing utilities.

Handles both legacy telegram ID format and new base64 referral codes.
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService


async def parse_referral_code(
    ref_arg: str,
    session: AsyncSession,
) -> int | None:
    """
    Parse referral code from /start command argument.

    Supports formats:
    - ref123456 (legacy telegram ID)
    - ref_123456 (legacy with underscore)
    - ref-123456 (legacy with dash)
    - ref_CODE (new base64 referral code)

    Args:
        ref_arg: Referral argument from /start command
        session: Database session

    Returns:
        Referrer telegram_id if found, None otherwise
    """
    if not ref_arg.startswith("ref"):
        logger.warning(f"Invalid referral format: {ref_arg}")
        return None

    try:
        # Better parsing strategy:
        # 1. Remove 'ref' prefix
        # 2. If starts with '_' or '-', remove ONE leading separator.
        clean_arg = ref_arg[3:]  # Remove 'ref'
        if clean_arg.startswith("_") or clean_arg.startswith("-"):
            clean_arg = clean_arg[1:]

        if clean_arg.isdigit():
            # Legacy ID
            referrer_telegram_id = int(clean_arg)
            logger.info(
                "Legacy referral ID detected",
                extra={
                    "ref_arg": ref_arg,
                    "referrer_telegram_id": referrer_telegram_id,
                },
            )
            return referrer_telegram_id
        else:
            # New Referral Code
            user_service = UserService(session)
            referrer = await user_service.get_by_referral_code(clean_arg)

            if referrer:
                referrer_telegram_id = referrer.telegram_id
                logger.info(
                    "Referral code detected",
                    extra={
                        "ref_code": clean_arg,
                        "referrer_telegram_id": referrer_telegram_id,
                    },
                )
                return referrer_telegram_id
            else:
                logger.warning(
                    "Referral code not found",
                    extra={"ref_code": clean_arg},
                )
                return None

    except (ValueError, AttributeError) as e:
        logger.warning(
            f"Invalid referral code format: {e}",
            extra={"ref_code": ref_arg},
        )
        return None
