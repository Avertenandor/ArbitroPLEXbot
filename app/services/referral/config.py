"""
Referral system configuration.

Contains constants and configuration for the referral system.
"""

from decimal import Decimal

# Referral system configuration (from PART2 docs)
# 3-level referral program: 5% from deposits AND earnings at each level
REFERRAL_DEPTH = 3
REFERRAL_RATES = {
    1: Decimal("0.05"),  # 5% for level 1 (direct referrals)
    2: Decimal("0.05"),  # 5% for level 2
    3: Decimal("0.05"),  # 5% for level 3
}
