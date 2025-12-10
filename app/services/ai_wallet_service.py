"""
AI Wallet Service - provides wallet balance checking for ARIA.

This service allows ARIA to:
- Check user wallet balances (BNB, USDT, PLEX)
- Get current PLEX exchange rate
- Make recommendations about PLEX holdings

Uses NodeReal RPC for blockchain data.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deposit_level_config_repository import DepositLevelConfigRepository
from app.repositories.user_repository import UserRepository
from app.services.wallet_info_service import WalletInfoService


# PLEX token economics (from bot/utils/constants.py)
PLEX_PER_DOLLAR_DAILY = 10  # User receives 10 PLEX per $1 deposited per day

# PLEX token contract
PLEX_CONTRACT = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"

# Recommended minimums for comfortable operation
RECOMMENDED_PLEX_MIN = 1000  # Minimum PLEX for basic operations
RECOMMENDED_BNB_MIN = Decimal("0.005")  # Minimum BNB for gas fees


class AIWalletService:
    """
    AI-powered wallet balance service.

    Provides ARIA with tools to check wallet balances and make
    recommendations about PLEX token holdings.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        """
        Initialize service.

        Args:
            session: Database session
            admin_data: Optional admin context (for admin mode)
        """
        self.session = session
        self.admin_data = admin_data
        self.user_repo = UserRepository(session)
        self.wallet_service = WalletInfoService()

    async def check_user_wallet(
        self,
        user_identifier: str | int,
    ) -> dict[str, Any]:
        """
        Check wallet balances for a user.

        Args:
            user_identifier: @username, telegram_id, or wallet address

        Returns:
            Wallet balance information with recommendations
        """
        try:
            # Find user
            user = None
            wallet_address = None

            identifier = str(user_identifier).strip()

            # Check if it's a wallet address
            if identifier.startswith("0x") and len(identifier) == 42:
                wallet_address = identifier
                # Try to find user by wallet
                user = await self.user_repo.get_by_wallet_address(wallet_address)
            elif identifier.startswith("@"):
                user = await self.user_repo.get_by_username(identifier[1:])
            elif identifier.isdigit():
                user = await self.user_repo.get_by_telegram_id(int(identifier))
            else:
                # Try as username without @
                user = await self.user_repo.get_by_username(identifier)

            if not user and not wallet_address:
                return {"success": False, "error": f"❌ Пользователь '{identifier}' не найден"}

            # Get wallet address from user if not provided
            if not wallet_address and user:
                wallet_address = user.wallet_address

            if not wallet_address:
                return {"success": False, "error": "❌ У пользователя не указан кошелёк"}

            # Get balances from blockchain
            balance = await self.wallet_service.get_wallet_balances(wallet_address)

            if not balance:
                return {"success": False, "error": "❌ Не удалось получить балансы кошелька. Попробуйте позже."}

            # Get current PLEX rate
            plex_rate_info = await self.get_plex_rate()
            plex_per_dollar = plex_rate_info.get("plex_per_dollar", PLEX_PER_DOLLAR_DAILY)

            # Calculate recommendations
            plex_balance = balance.plex_balance
            bnb_balance = balance.bnb_balance
            usdt_balance = balance.usdt_balance

            # Build recommendations
            recommendations = []
            warnings = []

            # Check BNB for gas
            if bnb_balance < RECOMMENDED_BNB_MIN:
                warnings.append(
                    f"⚠️ Мало BNB для комиссий! Рекомендуется минимум "
                    f"{RECOMMENDED_BNB_MIN} BNB (сейчас: {bnb_balance:.6f})"
                )

            # Check PLEX balance
            if plex_balance < RECOMMENDED_PLEX_MIN:
                needed = RECOMMENDED_PLEX_MIN - int(plex_balance)
                recommendations.append(f"💎 Рекомендуется докупить минимум {needed:,} PLEX для комфортной работы")

            # Calculate potential earnings context
            daily_plex_per_100 = 100 * plex_per_dollar  # PLEX per $100 deposit per day

            # User info
            user_info = None
            if user:
                user_info = {
                    "telegram_id": user.telegram_id,
                    "username": f"@{user.username}" if user.username else None,
                    "total_deposited": float(user.total_deposited_usdt or 0),
                    "balance": float(user.balance or 0),
                }

            return {
                "success": True,
                "wallet": {
                    "address": wallet_address,
                    "address_short": f"{wallet_address[:6]}...{wallet_address[-4:]}",
                },
                "balances": {
                    "bnb": {
                        "raw": float(bnb_balance),
                        "formatted": f"{bnb_balance:.6f} BNB",
                    },
                    "usdt": {
                        "raw": float(usdt_balance),
                        "formatted": f"{usdt_balance:.2f} USDT",
                    },
                    "plex": {
                        "raw": float(plex_balance),
                        "formatted": f"{int(plex_balance):,} PLEX",
                    },
                },
                "plex_rate": {
                    "per_dollar": plex_per_dollar,
                    "description": f"{plex_per_dollar} PLEX за $1 в сутки",
                    "example": f"$100 депозит = {daily_plex_per_100:,} PLEX/сутки",
                },
                "recommendations": recommendations,
                "warnings": warnings,
                "user": user_info,
                "checked_at": datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC"),
                "message": self._format_balance_message(
                    wallet_address, balance, plex_per_dollar, recommendations, warnings
                ),
            }

        except Exception as e:
            logger.error(f"AI WALLET: Error checking wallet: {e}")
            return {"success": False, "error": f"❌ Ошибка при проверке кошелька: {str(e)}"}

    async def get_plex_rate(self) -> dict[str, Any]:
        """
        Get current PLEX exchange rate.

        Returns:
            PLEX rate information
        """
        try:
            # Get from deposit level config
            config_repo = DepositLevelConfigRepository(self.session)
            configs = await config_repo.find_all()

            plex_per_dollar = PLEX_PER_DOLLAR_DAILY  # default

            if configs:
                # Use first level config as reference
                for config in configs:
                    if config.plex_per_dollar:
                        plex_per_dollar = config.plex_per_dollar
                        break

            # PLEX token price (implied from ROI)
            # If user gets 10 PLEX per $1, and typical ROI is ~2-10%
            # Token utility value, not market price
            implied_value_per_plex = Decimal("0.10")  # $0.10 per PLEX utility value

            return {
                "success": True,
                "plex_per_dollar": plex_per_dollar,
                "implied_value_usd": float(implied_value_per_plex),
                "description": f"Текущий курс: {plex_per_dollar} PLEX за $1 депозита в сутки",
                "economics": {
                    "daily_plex_per_100_usd": plex_per_dollar * 100,
                    "weekly_plex_per_100_usd": plex_per_dollar * 100 * 7,
                    "monthly_plex_per_100_usd": plex_per_dollar * 100 * 30,
                },
                "recommendation": (
                    "💡 Курс PLEX сейчас выгодный! Рекомендуем накапливать токены, пока цена адекватная."
                ),
                "message": (
                    f"💎 **Курс PLEX**\n\n"
                    f"• {plex_per_dollar} PLEX за $1 депозита в сутки\n"
                    f"• $100 = {plex_per_dollar * 100:,} PLEX/сутки\n"
                    f"• $100 за месяц = {plex_per_dollar * 100 * 30:,} PLEX\n\n"
                    f"📈 Курс стабильный, рекомендуем накапливать!"
                ),
            }

        except Exception as e:
            logger.error(f"AI WALLET: Error getting PLEX rate: {e}")
            return {
                "success": False,
                "plex_per_dollar": PLEX_PER_DOLLAR_DAILY,
                "error": str(e),
            }

    async def get_wallet_summary_for_dialog_end(
        self,
        user_telegram_id: int,
    ) -> dict[str, Any]:
        """
        Get wallet summary specifically for end of dialog.

        This is used by ARIA to show balance info and ask about PLEX.

        Args:
            user_telegram_id: User's Telegram ID

        Returns:
            Summary with recommendation prompt
        """
        result = await self.check_user_wallet(str(user_telegram_id))

        if not result.get("success"):
            return result

        # Build end-of-dialog message
        balances = result["balances"]
        plex_rate = result["plex_rate"]
        plex_balance = balances["plex"]["raw"]

        # Determine PLEX status
        if plex_balance >= 10000:
            plex_status = "✅ Отличный запас PLEX!"
            should_buy_more = False
        elif plex_balance >= 1000:
            plex_status = "👍 Хороший запас PLEX"
            should_buy_more = False
        elif plex_balance >= 100:
            plex_status = "⚠️ Запас PLEX на исходе"
            should_buy_more = True
        else:
            plex_status = "❌ Критически мало PLEX!"
            should_buy_more = True

        end_message = (
            f"📊 **Состояние вашего кошелька:**\n\n"
            f"💰 BNB: {balances['bnb']['formatted']}\n"
            f"💵 USDT: {balances['usdt']['formatted']}\n"
            f"💎 PLEX: {balances['plex']['formatted']}\n\n"
            f"{plex_status}\n\n"
            f"📈 Текущий курс: {plex_rate['per_dollar']} PLEX за $1/сутки\n"
        )

        if should_buy_more:
            end_message += (
                "\n❓ **Уверены, что у вас достаточно PLEX?**\nМожет быть стоит докупить, пока курс ещё адекватный? 💎"
            )

        return {
            "success": True,
            "balances": balances,
            "plex_rate": plex_rate,
            "plex_status": plex_status,
            "should_buy_more": should_buy_more,
            "warnings": result.get("warnings", []),
            "end_dialog_message": end_message,
        }

    def _format_balance_message(
        self,
        wallet_address: str,
        balance: Any,
        plex_per_dollar: int,
        recommendations: list[str],
        warnings: list[str],
    ) -> str:
        """Format balance info as readable message."""
        msg = (
            f"💼 **Баланс кошелька**\n"
            f"📍 `{wallet_address[:6]}...{wallet_address[-4:]}`\n\n"
            f"💰 **BNB:** {balance.bnb_formatted}\n"
            f"💵 **USDT:** {balance.usdt_formatted}\n"
            f"💎 **PLEX:** {balance.plex_formatted}\n\n"
            f"📈 Курс: {plex_per_dollar} PLEX/$1/сутки"
        )

        if warnings:
            msg += "\n\n" + "\n".join(warnings)

        if recommendations:
            msg += "\n\n" + "\n".join(recommendations)

        return msg
