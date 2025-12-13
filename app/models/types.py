"""
Standard type definitions for database models.

Provides consistent types for monetary and percentage fields across all models.
"""

from sqlalchemy import DECIMAL

# Standard money type for amounts, balances, rewards
# Precision: 18 digits total, 8 after decimal point
# Suitable for: USDT, PLEX, rewards, balances
# Range: up to 9,999,999,999.99999999
MoneyType = DECIMAL(18, 8)

# Large money type for blockchain transactions
# Precision: 36 digits total, 18 after decimal point
# Suitable for: raw blockchain amounts in wei
# Range: very large blockchain values
BigMoneyType = DECIMAL(36, 18)

# Standard percentage type for ROI rates
# Precision: 5 digits total, 2 after decimal point
# Suitable for: ROI percentages (e.g., 2.50%, 100.00%)
# Range: 0.00 to 999.99
PercentType = DECIMAL(5, 2)

# Precise rate percentage type for reward calculations
# Precision: 10 digits total, 4 after decimal point
# Suitable for: precise reward rates (e.g., 0.0833%, 2.5000%)
# Range: 0.0000 to 999999.9999
RatePercentType = DECIMAL(10, 4)
