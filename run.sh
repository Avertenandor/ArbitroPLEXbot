#!/bin/bash
# ArbitroPLEXbot Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ArbitroPLEXbot Startup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env and configure it:${NC}"
    echo -e "  cp .env.example .env"
    echo -e "  nano .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs
echo -e "${GREEN}✓ Logs directory ready${NC}"

# Run database migrations
echo -e "${YELLOW}Checking database migrations...${NC}"
if command -v alembic &> /dev/null; then
    alembic upgrade head
    echo -e "${GREEN}✓ Database migrations applied${NC}"
else
    echo -e "${YELLOW}⚠ Alembic not found, skipping migrations${NC}"
fi
echo ""

# Start the bot
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Starting Bot...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

python3 -m bot.main

# Handle exit
echo ""
echo -e "${YELLOW}Bot stopped.${NC}"
