# ArbitroPLEXbot

A Telegram bot for managing cryptocurrency deposits, ROI accrual, and withdrawals with PLEX token-based pay-to-use authorization.

## Features

- **Deposit Management**: Accept USDT deposits with multiple levels (10-300 USDT)
- **ROI System**: Daily ROI accrual with configurable rates and 500% cap
- **Pay-to-Use**: PLEX token-based authorization (10 PLEX per $1 deposit per day)
- **Withdrawal System**: Secure withdrawals with dual control for large amounts
- **Admin Panel**: Comprehensive admin tools with role-based access control
- **Blockchain Integration**: Real-time BSC/Polygon blockchain monitoring

## Architecture

### Wallet Types

| Wallet | Purpose | Configuration |
|--------|---------|---------------|
| **Input Wallet** | Receives USDT deposits from users | `SYSTEM_WALLET_ADDRESS` |
| **Auth Wallet** | Receives PLEX authorization payments | `AUTH_SYSTEM_WALLET_ADDRESS` |
| **Hot Wallet** | Sends USDT withdrawals to users | `WALLET_ADDRESS` + `WALLET_PRIVATE_KEY` |

### Pay-to-Use Model (PLEX)

Users must pay PLEX tokens daily to maintain active deposits:

- **Minimum Balance**: 5000 PLEX (non-spendable reserve)
- **Daily Fee**: 10 PLEX per $1 of deposit
- **Authorization**: 10 PLEX one-time payment to register

Example: A user with $100 deposit must pay 1000 PLEX daily.

### Admin Roles

| Role | Permissions |
|------|-------------|
| `super_admin` | Full access, wallet management, admin creation |
| `extended_admin` | User management, balance adjustments |
| `admin` | Basic admin operations |
| `moderator` | Limited read access |

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Node.js (for optional web interface)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Avertenandor/ArbitroPLEXbot.git
cd ArbitroPLEXbot
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your values
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the bot:
```bash
python -m bot.main
```

### Docker Deployment

```bash
docker-compose -f docker-compose.python.yml up -d
```

## Configuration

See [.env.example](.env.example) for all configuration options.

### Critical Security Settings

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Application secret (min 32 chars) | Yes |
| `ENCRYPTION_KEY` | Fernet key for encrypting private keys | Yes |
| `SUPER_ADMIN_TELEGRAM_ID` | Your Telegram user ID | Yes (production) |

### Generating Security Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Project Structure

```
ArbitroPLEXbot/
├── app/
│   ├── config/          # Settings and database config
│   ├── models/          # SQLAlchemy ORM models
│   ├── repositories/    # Data access layer
│   ├── services/        # Business logic
│   │   ├── blockchain/  # Blockchain operations
│   │   ├── deposit/     # Deposit lifecycle
│   │   └── withdrawal/  # Withdrawal processing
│   └── utils/           # Utility functions
├── bot/
│   ├── handlers/        # Telegram message handlers
│   │   ├── admin/       # Admin panel handlers
│   │   ├── deposit/     # Deposit handlers
│   │   └── withdrawal/  # Withdrawal handlers
│   ├── keyboards/       # Reply/inline keyboards
│   ├── middlewares/     # Bot middlewares
│   └── states/          # FSM states
├── jobs/
│   ├── tasks/           # Background tasks
│   └── scheduler.py     # Task scheduler
├── tests/               # Test suite
├── scripts/             # Utility scripts
└── alembic/             # Database migrations
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=bot

# Run specific test file
pytest tests/unit/test_roi_calculations.py
```

## Emergency Controls

The system includes emergency stop flags that can be toggled via admin panel:

- `emergency_stop_deposits` - Halt all new deposits
- `emergency_stop_withdrawals` - Halt all withdrawals
- `emergency_stop_roi` - Halt ROI accrual
- `blockchain_maintenance_mode` - Pause blockchain operations

## Security

- All private keys are encrypted using Fernet (AES-128)
- Admin actions require master key authentication
- Sensitive operations require `super_admin` role
- Comprehensive audit logging for all admin actions
- Rate limiting on admin operations to detect compromised accounts

## License

Proprietary - All rights reserved.

## Support

For issues and feature requests, please contact the development team.
