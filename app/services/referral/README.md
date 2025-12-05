# Referral Service Module Structure

This directory contains the modularized referral service, refactored from a single 965-line file into well-organized, maintainable modules.

## Module Overview

### Configuration
- **config.py** (16 lines)
  - Constants: `REFERRAL_DEPTH`, `REFERRAL_RATES`
  - Central configuration for the referral system

### Core Managers

#### 1. Chain Manager (`chain_manager.py` - 203 lines)
**Purpose**: Manages referral chain operations

**Class**: `ReferralChainManager`

**Methods**:
- `get_referral_chain(user_id, depth)` - Retrieves referral chain using PostgreSQL CTE
- `create_referral_relationships(new_user_id, direct_referrer_id)` - Creates multi-level referral relationships

#### 2. Earnings Manager (`earnings_manager.py` - 127 lines)
**Purpose**: Handles earnings and payment operations

**Class**: `ReferralEarningsManager`

**Methods**:
- `get_pending_earnings(user_id, page, limit)` - Gets unpaid earnings with pagination
- `mark_earning_as_paid(earning_id, tx_hash)` - Marks earning as paid

#### 3. Query Manager (`query_manager.py` - 133 lines)
**Purpose**: Handles referral queries and lookups

**Class**: `ReferralQueryManager`

**Methods**:
- `get_referrals_by_level(user_id, level, page, limit)` - Gets user's referrals by level
- `get_my_referrers(user_id)` - Gets who invited this user

#### 4. Statistics Manager (`statistics.py` - 463 lines)
**Purpose**: Provides analytics and statistics

**Class**: `ReferralStatisticsManager`

**Methods**:
- `get_referral_stats(user_id)` - Basic referral statistics
- `get_referral_leaderboard(limit)` - Top referrers leaderboard
- `get_user_leaderboard_position(user_id)` - User's leaderboard position
- `get_platform_referral_stats()` - Platform-wide statistics
- `get_daily_earnings_stats(user_id, days)` - Daily earnings breakdown
- `get_referral_conversion_stats(user_id)` - Conversion statistics
- `get_referral_activity_stats(user_id)` - Activity statistics

#### 5. Reward Processor (`referral_reward_processor.py` - 305 lines)
**Purpose**: Processes referral rewards (already existed)

**Class**: `ReferralRewardProcessor`

#### 6. Notifications (`referral_notifications.py` - 138 lines)
**Purpose**: Handles reward notifications (already existed)

## Main Service

### ReferralService (`/app/services/referral_service.py` - 332 lines)

The main service acts as a facade that delegates to the specialized managers. It maintains the same public API as before, ensuring backward compatibility.

**Initialization**:
```python
from app.services.referral_service import ReferralService

service = ReferralService(session)
```

All public methods remain the same and delegate to the appropriate manager.

## Usage Examples

### Direct Manager Usage (if needed)
```python
from app.services.referral import (
    ReferralChainManager,
    ReferralEarningsManager,
    ReferralQueryManager,
    ReferralStatisticsManager,
)

# Use individual managers
chain_manager = ReferralChainManager(session)
chain = await chain_manager.get_referral_chain(user_id)
```

### Configuration Access
```python
from app.services.referral import REFERRAL_DEPTH, REFERRAL_RATES

print(f"Max depth: {REFERRAL_DEPTH}")
print(f"Rates: {REFERRAL_RATES}")
```

## Backward Compatibility

All existing imports continue to work:
```python
from app.services.referral_service import ReferralService
from app.services import ReferralService
```

No changes required to existing code that uses `ReferralService`.

## Benefits of This Structure

1. **Maintainability**: Each module has a single, clear responsibility
2. **Testability**: Managers can be tested independently
3. **Scalability**: Easy to add new features to specific areas
4. **Readability**: Much easier to navigate and understand
5. **Collaboration**: Multiple developers can work on different modules simultaneously
6. **Performance**: No performance impact - same underlying logic

## File Size Comparison

- **Before**: 1 file × 965 lines = 965 lines
- **After**: Main service 332 lines + 4 new managers (463 + 203 + 133 + 127 + 16 = 942 lines)
- **Main file reduction**: 66% smaller (965 → 332 lines)
- **Largest module**: 463 lines (well under 500 line threshold)
