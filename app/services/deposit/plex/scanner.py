"""
Сканер PLEX транзакций в блокчейне.
Поиск PLEX переводов на системный кошелек.
"""

import asyncio
from decimal import Decimal
from typing import Any

from loguru import logger
from web3 import AsyncWeb3

from app.config.constants import BLOCKCHAIN_LONG_TIMEOUT
from app.config.settings import settings
from app.services.blockchain.blockchain_service import BlockchainService
from app.services.blockchain.constants import USDT_ABI


# ERC-20 standard ABI для Transfer событий (PLEX использует тот же стандарт)
PLEX_ABI = USDT_ABI


class PlexTransferScanner:
    """Сканер PLEX переводов в блокчейне."""

    PLEX_DECIMALS = 9  # PLEX имеет 9 decimals

    def __init__(self, blockchain: BlockchainService):
        """
        Инициализация сканера.

        Args:
            blockchain: Сервис блокчейна
        """
        self.blockchain = blockchain
        self.plex_contract_address = settings.plex_contract_address
        self.system_wallet_address = settings.auth_system_wallet_address

        # Web3 instance для работы с PLEX контрактом
        self._web3: AsyncWeb3 | None = None
        self._plex_contract = None

    async def _init_plex_contract(self) -> None:
        """Инициализация PLEX контракта через Web3."""
        if self._plex_contract is not None:
            return

        # Получаем Web3 из BlockchainService
        self._web3 = self.blockchain.provider_manager.get_http_web3()

        # Создаем экземпляр контракта PLEX
        self._plex_contract = self._web3.eth.contract(
            address=self._web3.to_checksum_address(self.plex_contract_address),
            abi=PLEX_ABI,
        )

        logger.info(
            f"PLEX contract initialized: {self.plex_contract_address}"
        )

    async def scan_transfers(
        self,
        from_address: str,
        required_amount: Decimal,
        since_hours: int = 24,
    ) -> dict[str, Any]:
        """
        Сканировать блокчейн на наличие PLEX переводов.

        Args:
            from_address: Адрес отправителя
            required_amount: Требуемая сумма PLEX
            since_hours: Количество часов назад для сканирования

        Returns:
            {
                "found": bool,
                "amount": Decimal,
                "tx_hash": str | None,
                "block_number": int | None
            }
        """
        await self._init_plex_contract()

        try:
            # Получаем текущий блок
            current_block = await self._web3.eth.block_number

            # Рассчитываем начальный блок (примерно 3 секунды на блок в BSC)
            blocks_back = int(since_hours * 3600 / 3)
            from_block = max(0, current_block - blocks_back)

            # Преобразуем адреса в checksum формат
            from_addr_checksum = self._web3.to_checksum_address(from_address)
            to_addr_checksum = self._web3.to_checksum_address(
                self.system_wallet_address
            )

            logger.info(
                f"Scanning PLEX transfers from {from_addr_checksum} "
                f"to {to_addr_checksum} in blocks {from_block}-{current_block}"
            )

            # Создаем фильтр для Transfer событий
            event_filter = await asyncio.wait_for(
                self._plex_contract.events.Transfer.create_filter(
                    from_block=from_block,
                    to_block=current_block,
                    argument_filters={
                        "from": from_addr_checksum,
                        "to": to_addr_checksum,
                    },
                ),
                timeout=BLOCKCHAIN_LONG_TIMEOUT,
            )

            # Получаем все события
            events = await asyncio.wait_for(
                event_filter.get_all_entries(),
                timeout=BLOCKCHAIN_LONG_TIMEOUT,
            )

            # Обрабатываем события (берем самый последний)
            for event in reversed(events):  # Начинаем с последних
                # Конвертируем amount из wei в PLEX
                amount_raw = event["args"]["value"]
                amount = Decimal(amount_raw) / Decimal(10**self.PLEX_DECIMALS)

                logger.info(
                    f"Found PLEX transfer: {amount} PLEX "
                    f"(tx: {event['transactionHash'].hex()})"
                )

                # Проверяем, достаточно ли amount
                tolerance = required_amount * Decimal("0.01")  # 1% толеранс
                if amount >= (required_amount - tolerance):
                    return {
                        "found": True,
                        "amount": amount,
                        "tx_hash": event["transactionHash"].hex(),
                        "block_number": event["blockNumber"],
                    }

            # Платёж не найден
            logger.debug(
                f"No matching PLEX transfer found from {from_address} "
                f"(required: {required_amount} PLEX)"
            )
            return {
                "found": False,
                "amount": Decimal("0"),
                "tx_hash": None,
                "block_number": None,
            }

        except TimeoutError:
            logger.error("Timeout scanning PLEX transfers")
            return {
                "found": False,
                "amount": Decimal("0"),
                "tx_hash": None,
                "block_number": None,
            }
        except Exception as e:
            logger.error(f"Error scanning PLEX transfers: {e}")
            return {
                "found": False,
                "amount": Decimal("0"),
                "tx_hash": None,
                "block_number": None,
            }

    async def get_plex_balance(self, address: str) -> Decimal | None:
        """
        Получить баланс PLEX для адреса.

        Args:
            address: Адрес кошелька

        Returns:
            Баланс PLEX или None при ошибке
        """
        await self._init_plex_contract()

        try:
            address_checksum = self._web3.to_checksum_address(address)

            # Вызываем balanceOf
            balance_raw = await self._plex_contract.functions.balanceOf(
                address_checksum
            ).call()

            # Конвертируем из wei в PLEX
            balance = Decimal(balance_raw) / Decimal(10**self.PLEX_DECIMALS)

            logger.debug(f"PLEX balance for {address}: {balance}")
            return balance

        except Exception as e:
            logger.error(f"Error getting PLEX balance for {address}: {e}")
            return None
