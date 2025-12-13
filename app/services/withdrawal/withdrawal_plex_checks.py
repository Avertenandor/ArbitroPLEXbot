"""
Withdrawal PLEX checks module.

Contains PLEX-specific validation checks:
- Daily PLEX payment requirements
- PLEX wallet minimum balance requirements
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.business_constants import MINIMUM_PLEX_BALANCE
from app.models.user import User
from app.utils.security import mask_address


class PlexChecksMixin:
    """Mixin providing PLEX-related validation checks."""

    session: AsyncSession

    async def check_plex_payments(
        self, user_id: int
    ) -> tuple[bool, str | None]:
        """Check if user has paid required daily PLEX for active deposits.

        Business rule:
        - For every active deposit (bonus or main) user must pay
          10 PLEX per $ of deposit per day.
        - Until the required daily PLEX payment is made, USDT
          withdrawals must be blocked.

        Args:
            user_id: User ID

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            from app.services.plex_payment_service import (
                PlexPaymentService,
            )

            plex_service = PlexPaymentService(self.session)
            status = await plex_service.get_user_payment_status(user_id)

            active_deposits = int(status.get("active_deposits", 0) or 0)

            # No active deposits -> no daily PLEX obligation
            if active_deposits == 0:
                return True, None

            has_debt = bool(status.get("has_debt"))
            has_recent_issue = bool(status.get("has_recent_issue"))

            # Блокируем вывод только при наличии долга по PLEX
            # (включая текущие сутки). Факт того, что последний
            # платёж был более 24 часов назад, сам по себе не
            # блокирует вывод, если долг полностью погашен и
            # предоплата покрывает сегодня.
            if has_debt:
                required = status.get("total_daily_plex")

                # Format required PLEX amount safely
                try:
                    required_str = (
                        f"{required.normalize()}"
                        if hasattr(required, "normalize")
                        else str(required)
                    )
                except (
                    AttributeError,
                    ValueError,
                    TypeError,
                ) as e:  # pragma: no cover - defensive formatting
                    logger.debug(
                        f"Failed to format required PLEX amount: {e}"
                    )
                    required_str = str(required)

                logger.warning(
                    "Withdrawal blocked: user has unpaid PLEX requirement",
                    extra={
                        "user_id": user_id,
                        "active_deposits": active_deposits,
                        "daily_plex_required": required_str,
                        "has_debt": has_debt,
                        "has_recent_issue": has_recent_issue,
                        "historical_debt_plex": str(
                            status.get("historical_debt_plex")
                        ),
                    },
                )

                # Причину формируем вокруг факта долга; информацию
                # о давности последнего платежа можно использовать
                # только как вспомогательную.
                reason_text = (
                    "— есть задолженность по ежедневным PLEX-платежам "
                    "(за прошлые дни и/или текущие сутки);"
                )

                error_msg = (
                    "🚫 Вывод USDT временно недоступен.\n\n"
                    "По правилам системы, при активных депозитах "
                    "необходимо ежедневно оплачивать 10 PLEX за "
                    "каждый $ депозита.\n\n"
                    f"Текущий суточный платёж за обслуживание ваших "
                    f"депозитов: {required_str} PLEX.\n\n"
                    f"Причина блокировки:\n{reason_text}\n\n"
                    "После полной оплаты задолженности и актуального "
                    "суточного платежа вывод USDT будет разблокирован."
                )
                return False, error_msg

            return True, None

        except (
            ImportError,
            ModuleNotFoundError,
        ) as exc:  # pragma: no cover - defensive
            # В случае ошибок импорта не блокируем вывод жёстко
            logger.error(
                f"PLEX payment service import failed "
                f"for user {user_id}: {exc}",
                exc_info=True,
            )
            return True, None
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:  # pragma: no cover - defensive
            # В случае ошибок обработки данных не блокируем
            # вывод жёстко
            logger.error(
                f"PLEX payment data processing failed "
                f"for user {user_id}: {exc}",
                exc_info=True,
            )
            return True, None
        except Exception as exc:  # pragma: no cover - defensive
            # В случае прочих непредвиденных ошибок не блокируем
            # вывод жёстко, чтобы технический сбой не ставил
            # систему на стоп.
            logger.error(
                f"Unexpected error in PLEX payment check "
                f"for user {user_id}: {exc}",
                exc_info=True,
            )
            return True, None

    async def check_plex_wallet_balance(
        self, user_id: int
    ) -> tuple[bool, str | None]:
        """Check if user has minimum required PLEX balance on wallet.

        Business rule:
        - User must have at least 5000 PLEX on their wallet at all
          times.
        - This is a "non-burnable minimum" (несгораемый минимум).
        - If balance is below 5000 PLEX, withdrawals are blocked.

        Args:
            user_id: User ID

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            from app.services.blockchain import get_blockchain_service

            # Get user's wallet address
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return False, "Пользователь не найден"

            if not user.wallet_address:
                logger.warning(f"User {user_id} has no wallet address")
                return False, (
                    "Кошелек не привязан. Обратитесь в поддержку."
                )

            # Get PLEX balance from blockchain
            blockchain_service = get_blockchain_service()
            plex_balance = await blockchain_service.get_plex_balance(
                user.wallet_address
            )

            if plex_balance is None:
                # If we can't get balance due to blockchain issues,
                # don't block withdrawal
                logger.warning(
                    f"Could not get PLEX balance for user {user_id}, "
                    f"wallet {mask_address(user.wallet_address)}"
                )
                return True, None

            # Check minimum balance requirement
            if plex_balance < MINIMUM_PLEX_BALANCE:
                logger.warning(
                    "Withdrawal blocked: insufficient PLEX wallet balance",
                    extra={
                        "user_id": user_id,
                        "wallet_address": mask_address(
                            user.wallet_address
                        ),
                        "plex_balance": str(plex_balance),
                        "minimum_required": str(MINIMUM_PLEX_BALANCE),
                    },
                )
                return False, (
                    f"🚫 Вывод USDT временно недоступен.\n\n"
                    f"На вашем кошельке недостаточно монет PLEX.\n\n"
                    f"📊 Текущий баланс: "
                    f"{plex_balance:,.0f} PLEX\n"
                    f"📊 Требуемый минимум: "
                    f"{MINIMUM_PLEX_BALANCE:,} PLEX\n\n"
                    f"🔴 **{MINIMUM_PLEX_BALANCE:,} PLEX** — это "
                    f"несгораемый минимум, который всегда должен "
                    f"быть на вашем кошельке.\n\n"
                    f"Пополните баланс PLEX на кошельке до минимума "
                    f"для разблокировки вывода."
                )

            logger.debug(
                f"PLEX wallet balance check passed for user {user_id}: "
                f"balance={plex_balance}, minimum={MINIMUM_PLEX_BALANCE}"
            )
            return True, None

        except (
            ImportError,
            ModuleNotFoundError,
        ) as exc:  # pragma: no cover - defensive
            # В случае ошибок импорта не блокируем вывод жёстко
            logger.error(
                f"Blockchain service import failed "
                f"for user {user_id}: {exc}",
                exc_info=True,
            )
            return True, None
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:  # pragma: no cover - defensive
            # В случае ошибок обработки данных не блокируем
            # вывод жёстко
            logger.error(
                f"PLEX wallet balance data processing failed "
                f"for user {user_id}: {exc}",
                exc_info=True,
            )
            return True, None
        except Exception as exc:  # pragma: no cover - defensive
            # В случае прочих непредвиденных ошибок не блокируем
            # вывод жёстко, чтобы технический сбой не ставил
            # систему на стоп.
            logger.error(
                f"Unexpected error in PLEX wallet balance check "
                f"for user {user_id}: {exc}",
                exc_info=True,
            )
            return True, None
