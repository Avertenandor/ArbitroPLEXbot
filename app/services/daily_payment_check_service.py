"""
Daily payment check service.

Checks if user has paid for the current day based on their deposits.
Shows payment status message with QR code if not paid.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.business_constants import PLEX_PER_DOLLAR_DAILY
from app.config.settings import settings
from app.models.user import User
from app.repositories.plex_payment_repository import PlexPaymentRepository
from app.repositories.user_repository import UserRepository
from app.services.blockchain_service import get_blockchain_service


class DailyPaymentCheckService:
    """
    Service for checking daily PLEX payment status.

    Formula: daily_plex_required = (total_deposited_usdt + bonus_balance) * 10

    Checks if user has made PLEX payment within the last 24 hours.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self._session = session
        self._user_repo = UserRepository(session)
        self._plex_repo = PlexPaymentRepository(session)

    async def check_daily_payment_status(self, user_id: int) -> dict:
        """
        Check if user has paid for the current day.

        Args:
            user_id: User ID

        Returns:
            Dict with:
                - is_paid: bool - True if paid for today
                - required_plex: Decimal - Required daily PLEX amount
                - total_deposited: Decimal - User's total deposits
                - bonus_balance: Decimal - User's bonus balance
                - last_payment_at: datetime | None - Last payment timestamp
                - hours_since_payment: float | None - Hours since last payment
                - wallet_address: str - System wallet for payment
                - user_wallet: str - User's wallet address
                - plex_balance: Decimal | None - User's current PLEX balance
                - error: str | None - Error message if any
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return {
                "is_paid": False,
                "required_plex": Decimal("0"),
                "total_deposited": Decimal("0"),
                "bonus_balance": Decimal("0"),
                "last_payment_at": None,
                "hours_since_payment": None,
                "wallet_address": settings.auth_system_wallet_address,
                "user_wallet": "",
                "plex_balance": None,
                "error": "User not found",
            }

        # Calculate required daily PLEX based on formula:
        # daily_plex_required = (total_deposited_usdt + bonus_balance) * 10
        total_deposited = user.total_deposited_usdt or Decimal("0")
        bonus_balance = user.bonus_balance or Decimal("0")
        total_investment = total_deposited + bonus_balance
        required_plex = total_investment * Decimal(str(PLEX_PER_DOLLAR_DAILY))

        # If no deposits or investments, user doesn't need to pay
        if required_plex <= 0:
            return {
                "is_paid": True,  # No payment required
                "required_plex": Decimal("0"),
                "total_deposited": total_deposited,
                "bonus_balance": bonus_balance,
                "last_payment_at": None,
                "hours_since_payment": None,
                "wallet_address": settings.auth_system_wallet_address,
                "user_wallet": user.wallet_address,
                "plex_balance": None,
                "error": None,
                "no_deposits": True,
            }

        # Get all active PLEX payment requirements for user
        payments = await self._plex_repo.get_active_by_user_id(user_id)

        now = datetime.now(UTC)
        is_paid = True
        last_payment_at = None
        hours_since_payment = None

        # Check if any payment is overdue (no payment in last 24 hours)
        for payment in payments:
            if payment.last_payment_at:
                if last_payment_at is None or payment.last_payment_at > last_payment_at:
                    last_payment_at = payment.last_payment_at

            # Check if payment is missing for last 24 hours
            if not payment.last_payment_at:
                is_paid = False
            else:
                time_since_payment = now - payment.last_payment_at
                if time_since_payment > timedelta(hours=24):
                    is_paid = False

        # Calculate hours since last payment
        if last_payment_at:
            hours_since_payment = (now - last_payment_at).total_seconds() / 3600

        # Get user's current PLEX balance
        plex_balance = None
        try:
            blockchain = get_blockchain_service()
            plex_balance = await blockchain.get_plex_balance(user.wallet_address)
        except Exception as e:
            logger.warning(f"Failed to get PLEX balance for user {user_id}: {e}")

        return {
            "is_paid": is_paid,
            "required_plex": required_plex,
            "total_deposited": total_deposited,
            "bonus_balance": bonus_balance,
            "last_payment_at": last_payment_at,
            "hours_since_payment": hours_since_payment,
            "wallet_address": settings.auth_system_wallet_address,
            "user_wallet": user.wallet_address,
            "plex_balance": plex_balance,
            "error": None,
        }


def format_daily_payment_message(status: dict, language: str = "ru") -> str:
    """
    Format daily payment status message.

    Args:
        status: Payment status dict from check_daily_payment_status
        language: Language code for translations

    Returns:
        Formatted message string
    """
    if status.get("error"):
        return f"⚠️ Ошибка проверки: {status['error']}"

    if status.get("no_deposits"):
        return ""  # No message needed if no deposits

    is_paid = status.get("is_paid", False)
    required_plex = status.get("required_plex", Decimal("0"))
    total_deposited = status.get("total_deposited", Decimal("0"))
    bonus_balance = status.get("bonus_balance", Decimal("0"))
    wallet_address = status.get("wallet_address", "")
    plex_balance = status.get("plex_balance")
    hours_since_payment = status.get("hours_since_payment")

    total_investment = total_deposited + bonus_balance

    if is_paid:
        # Payment is current
        message = (
            "✅ **ОПЛАТА ТЕКУЩИХ СУТОК**\n\n"
            f"💰 Ваши депозиты: **{total_deposited:.2f}** USDT\n"
        )
        if bonus_balance > 0:
            message += f"🎁 Бонусный баланс: **{bonus_balance:.2f}** USDT\n"
        message += (
            f"📊 Всего инвестиций: **{total_investment:.2f}** USDT\n"
            f"💎 Требуется PLEX в сутки: **{int(required_plex):,}** PLEX\n\n"
            "✅ **Текущие сутки оплачены!**\n"
        )
        if hours_since_payment is not None:
            message += f"⏱ Последний платёж: {hours_since_payment:.1f} ч. назад\n"
        if plex_balance is not None:
            message += f"💼 Ваш баланс PLEX: **{int(plex_balance):,}** PLEX"
    else:
        # Payment is overdue
        message = (
            "❌ **ОПЛАТА ТЕКУЩИХ СУТОК**\n\n"
            f"💰 Ваши депозиты: **{total_deposited:.2f}** USDT\n"
        )
        if bonus_balance > 0:
            message += f"🎁 Бонусный баланс: **{bonus_balance:.2f}** USDT\n"
        message += (
            f"📊 Всего инвестиций: **{total_investment:.2f}** USDT\n"
            f"💎 Требуется PLEX в сутки: **{int(required_plex):,}** PLEX\n\n"
            "❌ **Текущие сутки НЕ оплачены!**\n\n"
        )
        if plex_balance is not None:
            message += f"💼 Ваш баланс PLEX: **{int(plex_balance):,}** PLEX\n\n"

        message += (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📱 **Для оплаты отправьте PLEX на кошелёк:**\n\n"
            f"`{wallet_address}`\n\n"
            f"💳 **Сумма к оплате:** **{int(required_plex):,}** PLEX\n\n"
            "⚠️ Без оплаты работа депозитов приостановлена!"
        )

    return message
