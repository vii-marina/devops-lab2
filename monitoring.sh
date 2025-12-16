#!/usr/bin/env bash
# Simple system monitoring script:
# - Checks disk usage for root filesystem (/)
# - Compares usage with threshold
# - Logs all actions to log file
# - Sends alert to Discord via webhook if threshold is exceeded
#
# Usage:
#   ./monitoring.sh
#
# Notes:
#   Set DISCORD_WEBHOOK_URL variable below to your Discord webhook URL.

set -euo pipefail

# CONFIG
DISK_THRESHOLD=80           # % usage at which we send alert
CHECK_PATH="/"              # which filesystem to check
LOG_FILE="./system_monitor.log"

# Put your Discord webhook URL here:
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1447205953211732193/bUXJX8TC8k0gFvQCS_ibXBZWDwmzmuBg_f_QdERbV52LklxCOwjo0M_-uDItsiFTQRBd"

log() {
    local msg="$1"
    local now
    now="$(date +'%Y-%m-%d %H:%M:%S')"
    echo "[$now] $msg" | tee -a "$LOG_FILE"
}

send_discord_alert() {
    local text="$1"

    if [ -z "$DISCORD_WEBHOOK_URL" ] || [ "$DISCORD_WEBHOOK_URL" = "YOUR_WEBHOOK_URL_HERE" ]; then
        log "WARNING: DISCORD_WEBHOOK_URL is not set. Cannot send alert to Discord."
        return 0
    fi

    if ! command -v curl >/dev/null 2>&1; then
        log "ERROR: 'curl' command not found. Cannot send alert to Discord."
        return 1
    fi

    # Simple JSON payload: {"content":"..."}
    local payload
    payload=$(printf '{"content": "%s"}' "$text")

    # Send POST request
    if curl -sS -H "Content-Type: application/json" -X POST -d "$payload" "$DISCORD_WEBHOOK_URL" >/dev/null 2>&1; then
        log "Discord alert sent successfully."
    else
        log "ERROR: Failed to send alert to Discord via curl."
        return 1
    fi
}

get_disk_usage() {
    if ! command -v df >/dev/null 2>&1; then
        log "ERROR: 'df' command not found. Cannot check disk usage."
        exit 1
    fi

    # Take second line (NR==2), column 5 with percentage, remove '%' sign
    local usage
    usage="$(df -h "$CHECK_PATH" | awk 'NR==2 {gsub("%","",$5); print $5}')"

    if [ -z "$usage" ]; then
        log "ERROR: Failed to read disk usage for $CHECK_PATH."
        exit 1
    fi

    echo "$usage"
}

main() {
    log "=== System monitoring started ==="
    log "Checking disk usage for path: $CHECK_PATH"

    local disk_usage
    disk_usage="$(get_disk_usage)"

    log "Current disk usage: ${disk_usage}% (threshold: ${DISK_THRESHOLD}%)"

    if [ "$disk_usage" -ge "$DISK_THRESHOLD" ]; then
        log "Disk usage above threshold! Triggering alert."

        local alert_message
        alert_message="ALERT: Disk usage on $(hostname) for '$CHECK_PATH' is ${disk_usage}% (threshold ${DISK_THRESHOLD}%)."

        send_discord_alert "$alert_message" || log "WARNING: send_discord_alert reported an error."
    else
        log "Disk usage is within normal range."
    fi

    log "Monitoring finished."
}

main

