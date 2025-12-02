#!/bin/bash
# ArbitroPLEXbot - Health Check Script
#
# Checks the health of all services and reports status

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${GREEN}✅${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
info() { echo -e "${BLUE}ℹ️${NC} $1"; }

# Error counter
ERRORS=0
WARNINGS=0

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║      🔍 ArbitroPLEXbot - System Health Check           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ============================================
# 1. Docker Containers Check
# ============================================
info "1. Checking Docker containers..."
echo "   ──────────────────────────────"

if ! command -v docker &> /dev/null; then
    error "Docker is not installed"
    ERRORS=$((ERRORS + 1))
else
    if ! docker-compose -f docker-compose.python.yml ps &> /dev/null; then
        error "Docker Compose not running or file not found"
        ERRORS=$((ERRORS + 1))
    else
        # Check each container
        CONTAINERS=("sigmatrade-bot" "sigmatrade-postgres" "sigmatrade-redis" "sigmatrade-worker" "sigmatrade-scheduler")
        for container in "${CONTAINERS[@]}"; do
            if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
                STATUS=$(docker inspect --format='{{.State.Status}}' "$container")
                if [ "$STATUS" = "running" ]; then
                    log "$container is running"
                else
                    error "$container status: $STATUS"
                    ERRORS=$((ERRORS + 1))
                fi
            else
                warn "$container not found"
                WARNINGS=$((WARNINGS + 1))
            fi
        done
    fi
fi

echo ""

# ============================================
# 2. PostgreSQL Health Check
# ============================================
info "2. Checking PostgreSQL..."
echo "   ──────────────────────────"

if docker exec sigmatrade-postgres pg_isready -U sigmatrade &>/dev/null; then
    log "PostgreSQL is healthy"
    
    # Check database connection
    if docker exec sigmatrade-postgres psql -U sigmatrade -d sigmatrade -c "SELECT 1" &>/dev/null; then
        log "Database connection successful"
    else
        error "Cannot connect to database"
        ERRORS=$((ERRORS + 1))
    fi
else
    error "PostgreSQL not responding"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ============================================
# 3. Redis Health Check
# ============================================
info "3. Checking Redis..."
echo "   ──────────────────────────"

if docker exec sigmatrade-redis redis-cli ping &>/dev/null; then
    REDIS_RESPONSE=$(docker exec sigmatrade-redis redis-cli ping)
    if [ "$REDIS_RESPONSE" = "PONG" ]; then
        log "Redis is healthy"
        
        # Check Redis info
        REDIS_CLIENTS=$(docker exec sigmatrade-redis redis-cli INFO clients | grep "connected_clients" | awk -F':' '{print $2}' | tr -d '\r')
        info "   Connected clients: $REDIS_CLIENTS"
    else
        error "Redis unexpected response: $REDIS_RESPONSE"
        ERRORS=$((ERRORS + 1))
    fi
else
    error "Redis not responding"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ============================================
# 4. Bot Logs Check
# ============================================
info "4. Checking bot logs for errors..."
echo "   ──────────────────────────"

if docker logs sigmatrade-bot --tail 100 &>/dev/null; then
    # Count errors in last 100 lines
    ERROR_COUNT=$(docker logs sigmatrade-bot --tail 100 2>&1 | grep -ic "error\|exception\|traceback\|failed" || true)
    
    if [ "$ERROR_COUNT" -eq 0 ]; then
        log "No errors in recent logs"
    elif [ "$ERROR_COUNT" -lt 5 ]; then
        warn "Found $ERROR_COUNT errors in last 100 lines"
        WARNINGS=$((WARNINGS + 1))
        echo "   Run 'docker logs sigmatrade-bot --tail 100' to see details"
    else
        error "Found $ERROR_COUNT errors in last 100 lines"
        ERRORS=$((ERRORS + 1))
        echo "   Run 'docker logs sigmatrade-bot --tail 100' to see details"
    fi
else
    warn "Cannot read bot logs"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ============================================
# 5. Worker Logs Check
# ============================================
info "5. Checking worker logs for errors..."
echo "   ──────────────────────────"

if docker logs sigmatrade-worker --tail 100 &>/dev/null; then
    WORKER_ERROR_COUNT=$(docker logs sigmatrade-worker --tail 100 2>&1 | grep -ic "error\|exception\|traceback\|failed" || true)
    
    if [ "$WORKER_ERROR_COUNT" -eq 0 ]; then
        log "No errors in worker logs"
    elif [ "$WORKER_ERROR_COUNT" -lt 3 ]; then
        warn "Found $WORKER_ERROR_COUNT errors in worker logs"
        WARNINGS=$((WARNINGS + 1))
    else
        error "Found $WORKER_ERROR_COUNT errors in worker logs"
        ERRORS=$((ERRORS + 1))
    fi
else
    warn "Cannot read worker logs"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ============================================
# 6. Disk Space Check
# ============================================
info "6. Checking disk space..."
echo "   ──────────────────────────"

DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h / | tail -1 | awk '{print $4}')

if [ "$DISK_USAGE" -lt 70 ]; then
    log "Disk space OK (${DISK_USAGE}% used, ${DISK_AVAIL} available)"
elif [ "$DISK_USAGE" -lt 85 ]; then
    warn "Disk space moderate (${DISK_USAGE}% used, ${DISK_AVAIL} available)"
    WARNINGS=$((WARNINGS + 1))
else
    error "Disk space critical (${DISK_USAGE}% used, ${DISK_AVAIL} available)"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ============================================
# 7. Memory Usage Check
# ============================================
info "7. Checking memory usage..."
echo "   ──────────────────────────"

if command -v free &> /dev/null; then
    MEM_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100)}')
    MEM_AVAIL=$(free -h | grep Mem | awk '{print $7}')
    
    if [ "$MEM_USAGE" -lt 80 ]; then
        log "Memory OK (${MEM_USAGE}% used, ${MEM_AVAIL} available)"
    elif [ "$MEM_USAGE" -lt 90 ]; then
        warn "Memory high (${MEM_USAGE}% used, ${MEM_AVAIL} available)"
        WARNINGS=$((WARNINGS + 1))
    else
        error "Memory critical (${MEM_USAGE}% used, ${MEM_AVAIL} available)"
        ERRORS=$((ERRORS + 1))
    fi
else
    warn "Cannot check memory (free command not available)"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ============================================
# 8. Docker Resources Check
# ============================================
info "8. Checking Docker resource usage..."
echo "   ──────────────────────────"

if docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep sigmatrade &>/dev/null; then
    echo ""
    docker stats --no-stream --format "   {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep sigmatrade
    echo ""
    log "Docker containers resource usage displayed above"
else
    warn "Cannot check Docker stats"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ============================================
# 9. Network Connectivity Check
# ============================================
info "9. Checking network connectivity..."
echo "   ──────────────────────────"

# Check if bot can reach Telegram API
if docker exec sigmatrade-bot timeout 5 python -c "import requests; requests.get('https://api.telegram.org', timeout=3)" &>/dev/null; then
    log "Telegram API reachable"
else
    error "Cannot reach Telegram API"
    ERRORS=$((ERRORS + 1))
fi

# Check if bot can reach BSC RPC
if docker exec sigmatrade-bot timeout 5 python -c "import requests; requests.post('https://bsc-dataseed.binance.org/', json={'jsonrpc':'2.0','method':'eth_blockNumber','params':[],'id':1}, timeout=3)" &>/dev/null; then
    log "BSC RPC endpoint reachable"
else
    warn "Cannot reach BSC RPC (check RPC_URL setting)"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ============================================
# Summary
# ============================================
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    📊 Health Check Summary              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! System is healthy.${NC}"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  System is operational with $WARNINGS warning(s).${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ System has $ERRORS error(s) and $WARNINGS warning(s).${NC}"
    echo ""
    echo "Please address the errors above before deploying."
    echo ""
    exit 1
fi
