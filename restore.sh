#!/bin/bash

# Newsletter Analyst - Restore Script
# Restores data from a backup archive

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Newsletter Analyst - Restore"
echo "=========================================="
echo ""

# Check if backup directory exists
if [ ! -d "${BACKUP_DIR}" ]; then
    echo -e "${RED}Error:${NC} Backup directory not found: ${BACKUP_DIR}"
    exit 1
fi

# List available backups
echo "Available backups:"
echo ""
BACKUPS=($(ls -1t "${BACKUP_DIR}"/newsletter-analyst-backup-*.tar.gz 2>/dev/null))

if [ ${#BACKUPS[@]} -eq 0 ]; then
    echo -e "${RED}No backups found in ${BACKUP_DIR}${NC}"
    exit 1
fi

# Display backups with numbers
for i in "${!BACKUPS[@]}"; do
    BACKUP_FILE="${BACKUPS[$i]}"
    BACKUP_NAME=$(basename "${BACKUP_FILE}")
    BACKUP_DATE=$(echo "${BACKUP_NAME}" | grep -oP '\d{8}_\d{6}')
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    BACKUP_TIME=$(date -d "${BACKUP_DATE:0:8} ${BACKUP_DATE:9:2}:${BACKUP_DATE:11:2}:${BACKUP_DATE:13:2}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "Unknown")

    echo -e "${BLUE}[$((i+1))]${NC} ${BACKUP_TIME} - ${BACKUP_SIZE}"
done

echo ""

# Prompt for selection
if [ -z "$1" ]; then
    read -p "Select backup to restore (1-${#BACKUPS[@]}) or 'q' to quit: " SELECTION

    if [ "${SELECTION}" == "q" ]; then
        echo "Restore cancelled"
        exit 0
    fi

    if ! [[ "${SELECTION}" =~ ^[0-9]+$ ]] || [ "${SELECTION}" -lt 1 ] || [ "${SELECTION}" -gt ${#BACKUPS[@]} ]; then
        echo -e "${RED}Error:${NC} Invalid selection"
        exit 1
    fi

    SELECTED_BACKUP="${BACKUPS[$((SELECTION-1))]}"
else
    # Use provided backup file
    SELECTED_BACKUP="$1"
    if [ ! -f "${SELECTED_BACKUP}" ]; then
        echo -e "${RED}Error:${NC} Backup file not found: ${SELECTED_BACKUP}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}Warning:${NC} This will overwrite existing data!"
echo "Backup file: $(basename ${SELECTED_BACKUP})"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo ""
echo "Starting restore..."
echo ""

# Create temporary extraction directory
TEMP_DIR=$(mktemp -d)
echo "Extracting backup to temporary directory..."

tar -xzf "${SELECTED_BACKUP}" -C "${TEMP_DIR}"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Failed to extract backup"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Backup extracted"

# Find the extracted directory
EXTRACTED_DIR=$(find "${TEMP_DIR}" -maxdepth 1 -type d -name "newsletter-analyst-backup-*" | head -n 1)

if [ -z "${EXTRACTED_DIR}" ]; then
    echo -e "${RED}✗${NC} Could not find extracted backup directory"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

# Restore data directory
if [ -d "${EXTRACTED_DIR}/data" ]; then
    echo "Restoring data directory..."

    # Backup current data if it exists
    if [ -d "${APP_DIR}/data" ]; then
        CURRENT_BACKUP="${APP_DIR}/data.backup.$(date +%Y%m%d_%H%M%S)"
        mv "${APP_DIR}/data" "${CURRENT_BACKUP}"
        echo "  Current data backed up to: ${CURRENT_BACKUP}"
    fi

    cp -r "${EXTRACTED_DIR}/data" "${APP_DIR}/"
    echo -e "${GREEN}✓${NC} Data restored"
else
    echo -e "${YELLOW}⚠${NC} No data directory in backup"
fi

# Restore config directory
if [ -d "${EXTRACTED_DIR}/config" ]; then
    echo "Restoring config directory..."

    # Backup current config if it exists
    if [ -d "${APP_DIR}/config" ]; then
        CURRENT_CONFIG_BACKUP="${APP_DIR}/config.backup.$(date +%Y%m%d_%H%M%S)"
        mv "${APP_DIR}/config" "${CURRENT_CONFIG_BACKUP}"
        echo "  Current config backed up to: ${CURRENT_CONFIG_BACKUP}"
    fi

    cp -r "${EXTRACTED_DIR}/config" "${APP_DIR}/"
    echo -e "${GREEN}✓${NC} Config restored"
else
    echo -e "${YELLOW}⚠${NC} No config directory in backup"
fi

# Restore output directory
if [ -d "${EXTRACTED_DIR}/output" ]; then
    echo "Restoring output directory..."
    cp -r "${EXTRACTED_DIR}/output" "${APP_DIR}/"
    echo -e "${GREEN}✓${NC} Output restored"
fi

# Restore .env file (optional)
if [ -f "${EXTRACTED_DIR}/.env" ]; then
    read -p "Restore .env file? (yes/no): " RESTORE_ENV
    if [ "${RESTORE_ENV}" == "yes" ]; then
        if [ -f "${APP_DIR}/.env" ]; then
            cp "${APP_DIR}/.env" "${APP_DIR}/.env.backup.$(date +%Y%m%d_%H%M%S)"
        fi
        cp "${EXTRACTED_DIR}/.env" "${APP_DIR}/"
        echo -e "${GREEN}✓${NC} .env restored"
    fi
fi

# Clean up temporary directory
rm -rf "${TEMP_DIR}"

echo ""
echo "=========================================="
echo "Restore Complete!"
echo "=========================================="
echo ""
echo "Restored from: $(basename ${SELECTED_BACKUP})"
echo ""
echo "Next steps:"
echo "  1. Verify database: python src/main.py stats"
echo "  2. Test dashboard: streamlit run dashboard.py"
echo ""
