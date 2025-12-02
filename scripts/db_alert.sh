#!/bin/bash
# Database monitoring with Telegram alerts

MONITOR_SCRIPT="/usr/bin/docker exec sigmatrade-bot python3 /app/scripts/monitor_db.py postgres"
LOG_FILE="/var/log/db_monitor.log"
ALERT_LOG="/var/log/db_alerts.log"

# Telegram bot settings (from env or config)
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_ADMIN_ID:-}"

send_telegram_alert() {
    local message="$1"
    
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${message}" \
            -d "parse_mode=Markdown" > /dev/null 2>&1
    fi
}

# Run monitor
OUTPUT=$($MONITOR_SCRIPT 2>&1)
EXIT_CODE=$?

# Log output
echo "$(date '+%Y-%m-%d %H:%M:%S') - Exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "$OUTPUT" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

# Check for critical issues (exit code 1 = unhealthy)
if [ $EXIT_CODE -eq 1 ]; then
    # Extract critical issues
    CRITICAL_ISSUES=$(echo "$OUTPUT" | grep "🔴 CRITICAL" | head -3)
    
    if [ -n "$CRITICAL_ISSUES" ]; then
        ALERT_MESSAGE="🚨 *DB Critical Alert*%0A%0A${CRITICAL_ISSUES}"
        
        echo "$(date '+%Y-%m-%d %H:%M:%S') - CRITICAL: Sending alert" >> "$ALERT_LOG"
        echo "$CRITICAL_ISSUES" >> "$ALERT_LOG"
        
        send_telegram_alert "$ALERT_MESSAGE"
    fi
fi

# Check for too many connections
CONNECTION_COUNT=$(echo "$OUTPUT" | grep "Total Connections:" | grep -oP '\d+(?=/)')
if [ -n "$CONNECTION_COUNT" ] && [ "$CONNECTION_COUNT" -gt 80 ]; then
    ALERT_MESSAGE="⚠️ *DB Warning*%0A%0AHigh connection count: ${CONNECTION_COUNT}/100"
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - WARNING: High connections: $CONNECTION_COUNT" >> "$ALERT_LOG"
    send_telegram_alert "$ALERT_MESSAGE"
fi

exit $EXIT_CODE
