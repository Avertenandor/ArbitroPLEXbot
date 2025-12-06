"""
Модель конфигурации уровней депозитов.
Хранит настройки коридоров сумм для каждого уровня.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DepositLevelConfig(Base):
    """Конфигурация уровня депозита с коридором сумм."""

    __tablename__ = "deposit_level_configs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Тип уровня: test, level_1, level_2, level_3, level_4, level_5
    level_type: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Человекочитаемое имя
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Порядок уровня (0=test, 1=level_1, ...)
    order: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    # Коридор сумм
    min_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False
    )
    max_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False
    )

    # PLEX за $1 в сутки
    plex_per_dollar: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )

    # Активность уровня
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True, nullable=False
    )

    # ROI настройки
    roi_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("2.0"), nullable=False
    )
    roi_cap_percent: Mapped[int] = mapped_column(
        Integer, default=500, nullable=False
    )  # 500%

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def is_amount_valid(self, amount: Decimal) -> bool:
        """
        Проверить, что сумма в коридоре.

        Args:
            amount: Сумма для проверки

        Returns:
            True если сумма в пределах коридора
        """
        return self.min_amount <= amount <= self.max_amount

    def calculate_daily_plex(self, amount: Decimal) -> Decimal:
        """
        Рассчитать ежедневный PLEX.

        Args:
            amount: Сумма депозита

        Returns:
            Ежедневная сумма PLEX
        """
        return amount * self.plex_per_dollar

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<DepositLevelConfig(id={self.id}, "
            f"level_type={self.level_type}, "
            f"name={self.name}, "
            f"order={self.order}, "
            f"min_amount={self.min_amount}, "
            f"max_amount={self.max_amount})>"
        )
