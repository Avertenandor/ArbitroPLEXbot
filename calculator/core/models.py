"""Pydantic models for calculator."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DepositLevel(BaseModel):
    """Model for deposit level configuration.

    Represents a tier in the deposit system with specific ROI parameters.
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    level_number: int = Field(..., ge=1, description="Level number (1, 2, 3, etc.)")
    min_amount: Decimal = Field(..., ge=0, description="Minimum deposit amount for this level")
    roi_percent: Decimal = Field(..., ge=0, description="Daily ROI percentage")
    roi_cap_percent: Decimal = Field(
        ..., ge=0, description="Maximum ROI cap percentage (e.g., 500 = 500%)"
    )
    is_active: bool = Field(default=True, description="Whether this level is currently active")
    name: str | None = Field(default=None, description="Optional level name")


class CalculationResult(BaseModel):
    """Result of ROI calculation.

    Contains calculated rewards over different time periods.
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    daily_reward: Decimal = Field(..., ge=0, description="Daily reward amount")
    weekly_reward: Decimal = Field(..., ge=0, description="Weekly reward amount")
    monthly_reward: Decimal = Field(..., ge=0, description="Monthly reward amount (30 days)")
    yearly_reward: Decimal = Field(..., ge=0, description="Yearly reward amount (365 days)")
    roi_cap_amount: Decimal = Field(..., ge=0, description="Maximum total reward amount (ROI cap)")
    days_to_cap: int = Field(..., ge=0, description="Number of days to reach ROI cap")


class DepositCalculation(BaseModel):
    """Complete calculation for a deposit.

    Combines deposit amount, level configuration, and calculation results.
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    amount: Decimal = Field(..., ge=0, description="Deposit amount")
    level: DepositLevel = Field(..., description="Deposit level configuration")
    result: CalculationResult = Field(..., description="Calculation results")
