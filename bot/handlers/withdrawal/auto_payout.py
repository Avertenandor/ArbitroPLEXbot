"""
Auto-payout processing module.

This module handles automatic withdrawal payouts, including blockchain transactions
and user notifications.
"""

from decimal import Decimal

from aiogram import Bot
from loguru import logger
from sqlalchemy import select

from app.models.enums import TransactionStatus
from app.models.transaction import Transaction
from app.utils.security import mask_address


async def _safe_process_auto_payout(
    tx_id: int,
    amount: Decimal,
    to_address: str,
    bot: Bot,
    telegram_id: int
) -> None:
    """Wrapper for safe auto-payout execution."""
    try:
        await process_auto_payout(tx_id, amount, to_address, bot, telegram_id)
    except Exception as e:
        logger.error(f"Auto-payout task failed for tx {tx_id}: {e}", exc_info=True)


async def process_auto_payout(
    tx_id: int,
    amount: Decimal,
    to_address: str,
    bot: Bot,
    telegram_id: int
):
    """
    Process auto-payout in background.
    """
    from app.config.database import async_session_maker
    from app.services.blockchain_service import get_blockchain_service

    blockchain_service = get_blockchain_service()
    if not blockchain_service:
        logger.error(f"Blockchain service not initialized for auto-payout tx {tx_id}")
        return

    logger.info(f"Starting auto-payout for tx {tx_id}, amount {amount} to {mask_address(to_address)}")

    # Send payment (keep Decimal for precision)
    result = await blockchain_service.send_payment(to_address, amount)

    async with async_session_maker() as session:
        stmt = select(Transaction).where(Transaction.id == tx_id)
        res = await session.execute(stmt)
        tx = res.scalar_one_or_none()

        if not tx:
            logger.error(f"Transaction {tx_id} not found during auto-payout update")
            return

        if result["success"]:
            logger.info(f"Auto-payout successful for tx {tx_id}: {result['tx_hash']}")
            tx.tx_hash = result["tx_hash"]
            tx.status = TransactionStatus.CONFIRMED.value

            # Notify user about success
            try:
                # Show net amount that was actually sent (amount param is already net_amount)
                await bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        f"✅ *Выплата отправлена!*\n\n"
                        f"💰 Получено: `{amount} USDT`\n"
                        f"💳 Кошелек: `{to_address[:6]}...{to_address[-4:]}`\n"
                        f"🔗 TX: [Посмотреть транзакцию](https://bscscan.com/tx/{result['tx_hash']})\n\n"
                        f"🤝 Спасибо за ваше доверие к ArbitroPLEXbot!"
                    ),
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Failed to send auto-payout notification to {telegram_id}: {e}")

        else:
            logger.error(f"Auto-payout failed for tx {tx_id}: {result.get('error')}")
            # Revert to PENDING for manual admin review
            tx.status = TransactionStatus.PENDING.value

        await session.commit()
