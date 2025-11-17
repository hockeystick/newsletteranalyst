#!/bin/bash

# Newsletter Analyst - Backup Script
# Backs up data, config, and output directories

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="newsletter-analyst-backup-${DATE}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Newsletter Analyst - Backup"
echo "=========================================="
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Create temporary directory for this backup
TEMP_BACKUP_DIR="${BACKUP_DIR}/${BACKUP_NAME}"
mkdir -p "${TEMP_BACKUP_DIR}"

echo "Backup location: ${TEMP_BACKUP_DIR}"
echo ""

# Backup data directory (database)
if [ -d "${APP_DIR}/data" ]; then
    echo "Backing up data directory..."
    cp -r "${APP_DIR}/data" "${TEMP_BACKUP_DIR}/" 2>/dev/null || true
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Data backed up"
    else
        echo -e "${RED}✗${NC} Data backup failed"
    fi
else
    echo -e "${YELLOW}⚠${NC} Data directory not found"
fi

# Backup config directory (excluding sensitive files if needed)
if [ -d "${APP_DIR}/config" ]; then
    echo "Backing up config directory..."
    mkdir -p "${TEMP_BACKUP_DIR}/config"

    # Copy credentials and tokens
    cp "${APP_DIR}/config/credentials.json" "${TEMP_BACKUP_DIR}/config/" 2>/dev/null || echo "  (no credentials.json)"
    cp "${APP_DIR}/config/token.json" "${TEMP_BACKUP_DIR}/config/" 2>/dev/null || echo "  (no token.json)"

    echo -e "${GREEN}✓${NC} Config backed up"
else
    echo -e "${YELLOW}⚠${NC} Config directory not found"
fi

# Backup output directory
if [ -d "${APP_DIR}/output" ] && [ "$(ls -A ${APP_DIR}/output)" ]; then
    echo "Backing up output directory..."
    cp -r "${APP_DIR}/output" "${TEMP_BACKUP_DIR}/" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Output backed up"
fi

# Backup .env file
if [ -f "${APP_DIR}/.env" ]; then
    echo "Backing up .env file..."
    cp "${APP_DIR}/.env" "${TEMP_BACKUP_DIR}/" 2>/dev/null
    echo -e "${GREEN}✓${NC} .env backed up"
fi

# Create compressed archive
echo ""
echo "Creating compressed archive..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"

if [ $? -eq 0 ]; then
    # Remove temporary directory
    rm -rf "${BACKUP_NAME}"

    # Get backup size
    BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

    echo -e "${GREEN}✓${NC} Backup created: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"
else
    echo -e "${RED}✗${NC} Failed to create compressed archive"
    exit 1
fi

# Clean up old backups
echo ""
echo "Cleaning up old backups (keeping last ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -name "newsletter-analyst-backup-*.tar.gz" -mtime +${RETENTION_DAYS} -delete

REMAINING_BACKUPS=$(ls -1 "${BACKUP_DIR}"/newsletter-analyst-backup-*.tar.gz 2>/dev/null | wc -l)
echo -e "${GREEN}✓${NC} Cleanup complete (${REMAINING_BACKUPS} backups remaining)"

# Calculate total backup size
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
echo ""
echo "Total backup directory size: ${TOTAL_SIZE}"
echo ""
echo "=========================================="
echo "Backup Complete!"
echo "=========================================="
echo ""
echo "Backup file: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo ""

# Return to original directory
cd "${APP_DIR}"
