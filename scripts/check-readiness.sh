#!/bin/bash
###############################################################################
# Production Readiness Check Script
# Checks if the bot is ready for production deployment
###############################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║      ArbitroPLEXbot - Readiness Check Script        ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

ERRORS=0
WARNINGS=0

# Check 1: .env file exists
log "Check 1/8: Checking .env file..."
if [ ! -f "${ENV_FILE}" ]; then
    error ".env file not found"
    info "Run: scripts/setup-env.sh"
    ((ERRORS++))
else
    log "✅ .env file exists"
fi

# Check 2: Validate environment variables
log "Check 2/8: Validating environment variables..."
if python3 "${PROJECT_ROOT}/scripts/validate-env.py" 2>/dev/null; then
    log "✅ Environment variables are valid"
else
    error "Environment variables validation failed"
    info "Run: scripts/setup-env.sh or fix .env manually"
    ((ERRORS++))
fi

# Check 3: Docker is installed
log "Check 3/8: Checking Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log "✅ Docker is installed: ${DOCKER_VERSION}"
else
    error "Docker is not installed"
    info "Install: sudo apt install docker.io"
    ((ERRORS++))
fi

# Check 4: Docker Compose is installed
log "Check 4/8: Checking Docker Compose..."
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    log "✅ Docker Compose is available"
else
    error "Docker Compose is not installed"
    info "Install: sudo apt install docker-compose"
    ((ERRORS++))
fi

# Check 5: Dockerfile.python exists
log "Check 5/8: Checking Dockerfile.python..."
if [ -f "${PROJECT_ROOT}/Dockerfile.python" ]; then
    log "✅ Dockerfile.python exists"
else
    error "Dockerfile.python not found"
    ((ERRORS++))
fi

# Check 6: docker-compose.python.yml exists
log "Check 6/8: Checking docker-compose.python.yml..."
if [ -f "${PROJECT_ROOT}/docker-compose.python.yml" ]; then
    log "✅ docker-compose.python.yml exists"
else
    error "docker-compose.python.yml not found"
    ((ERRORS++))
fi

# Check 7: Database connection (if DATABASE_URL is set)
log "Check 7/8: Checking database connection..."
if [ -f "${ENV_FILE}" ] && grep -q "DATABASE_URL=" "${ENV_FILE}"; then
    DATABASE_URL=$(grep "^DATABASE_URL=" "${ENV_FILE}" | cut -d '=' -f2-)
    if [ -n "${DATABASE_URL}" ] && [[ "${DATABASE_URL}" != *"your_"* ]] && [[ "${DATABASE_URL}" != *"localhost"* ]]; then
        # Try to connect (if psql is available)
        if command -v psql &> /dev/null; then
            # Extract connection details and test
            if echo "${DATABASE_URL}" | grep -q "postgresql"; then
                log "✅ Database URL is configured"
                warn "⚠️  Database connection test skipped (requires psql)"
            else
                warn "⚠️  DATABASE_URL format may be incorrect"
                ((WARNINGS++))
            fi
        else
            log "✅ Database URL is configured"
            warn "⚠️  psql not available for connection test"
        fi
    else
        error "DATABASE_URL is not properly configured"
        ((ERRORS++))
    fi
else
    error "DATABASE_URL not found in .env"
    ((ERRORS++))
fi

# Check 8: Required scripts exist
log "Check 8/8: Checking required scripts..."
REQUIRED_SCRIPTS=(
    "scripts/setup-env.sh"
    "scripts/validate-env.py"
    "scripts/deploy-python.sh"
    "scripts/backup-production.sh"
)

for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ -f "${PROJECT_ROOT}/${script}" ]; then
        log "✅ ${script} exists"
    else
        warn "⚠️  ${script} not found"
        ((WARNINGS++))
    fi
done

# Summary
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    SUMMARY                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ${ERRORS} -eq 0 ] && [ ${WARNINGS} -eq 0 ]; then
    log "✅ All checks passed! Bot is ready for production deployment."
    echo ""
    log "Next steps:"
    info "1. Review .env file: nano ${ENV_FILE}"
    info "2. Run deployment: ./scripts/deploy-python.sh production"
    exit 0
elif [ ${ERRORS} -eq 0 ]; then
    log "✅ Critical checks passed, but there are ${WARNINGS} warning(s)"
    warn "Please review warnings above"
    exit 0
else
    error "❌ ${ERRORS} critical error(s) found, ${WARNINGS} warning(s)"
    error "Please fix errors before deploying to production"
    exit 1
fi

