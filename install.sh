#!/bin/bash

# DittoKiller Installation Script
# This script sets up the Python environment and installs the systemd service.

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== DittoKiller Installer ===${NC}"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not found. Please install it."
    exit 1
fi

# 2. Create Virtual Environment
echo -e "${GREEN}[+] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Install Dependencies
echo -e "${GREEN}[+] Installing dependencies...${NC}"
pip install -r requirements.txt

# 4. Configure Systemd Service
echo -e "${GREEN}[+] Configuring systemd user service...${NC}"
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

ROOT_DIR=$(pwd)
PYTHON_EXEC="$ROOT_DIR/venv/bin/python"

# Read template and replace placeholders
sed -e "s|%ROOT_DIR%|$ROOT_DIR|g" \
    -e "s|%PYTHON_EXEC%|$PYTHON_EXEC|g" \
    dittokiller.service > "$SERVICE_DIR/dittokiller.service"

echo "Created $SERVICE_DIR/dittokiller.service"

# 5. Enable and Start Service
echo -e "${GREEN}[+] Starting service...${NC}"
systemctl --user daemon-reload
systemctl --user enable dittokiller.service
systemctl --user restart dittokiller.service

echo -e "${BLUE}=== Installation Complete! ===${NC}"
echo "DittoKiller is running. You can check status with: systemctl --user status dittokiller"
