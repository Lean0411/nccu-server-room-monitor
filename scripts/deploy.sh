#!/bin/bash

# NCCU Server Room Monitor - Deployment Script
# Updates and restarts the monitoring system

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="nccu-monitor"
BACKUP_DIR="${PROJECT_DIR}/backups/$(date +%Y%m%d_%H%M%S)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting deployment...${NC}"

# Create backup
mkdir -p "$BACKUP_DIR"
cp -r "${PROJECT_DIR}/src" "$BACKUP_DIR/"
cp "${PROJECT_DIR}/.env" "$BACKUP_DIR/" 2>/dev/null || true

# Pull latest changes
cd "$PROJECT_DIR"
git pull origin main

# Update dependencies
source "${PROJECT_DIR}/venv/bin/activate"
pip install -r requirements/prod.txt

# Restart service
sudo systemctl restart "$SERVICE_NAME"

echo -e "${GREEN}Deployment completed!${NC}"
sudo systemctl status "$SERVICE_NAME" --no-pager