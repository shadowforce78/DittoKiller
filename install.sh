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

# Remove existing venv to ensure clean state (fixes broken/partial venvs)
if [ -d ".venv" ]; then
    rm -rf .venv
fi

python3 -m venv .venv

# Verify pip exists
if [ ! -f ".venv/bin/pip" ]; then
    echo "Error: pip not found in .venv/bin/pip. Please install 'python3-venv' or 'python3-full'."
    exit 1
fi

# We use explicit paths instead of activating to avoid shell issues
VENV_PYTHON="./.venv/bin/python"
VENV_PIP="./.venv/bin/pip"

# 3. Install Dependencies
echo -e "${GREEN}[+] Installing dependencies...${NC}"
"$VENV_PIP" install -r requirements.txt

# 4. Configure Systemd Service
echo -e "${GREEN}[+] Configuring systemd user service...${NC}"
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

ROOT_DIR=$(pwd)
PYTHON_EXEC="$ROOT_DIR/.venv/bin/python"
CURRENT_DISPLAY="${DISPLAY:-:0}"

# Read template and replace placeholders
sed -e "s|%ROOT_DIR%|$ROOT_DIR|g" \
    -e "s|%PYTHON_EXEC%|$PYTHON_EXEC|g" \
    -e "s|%DISPLAY%|$CURRENT_DISPLAY|g" \
    dittokiller.service > "$SERVICE_DIR/dittokiller.service"

echo "Created $SERVICE_DIR/dittokiller.service"

# 5. Enable and Start Service
echo -e "${GREEN}[+] Starting service...${NC}"
systemctl --user daemon-reload
systemctl --user enable dittokiller.service
systemctl --user restart dittokiller.service

echo -e "${BLUE}=== Installation Complete! ===${NC}"
echo "DittoKiller is running. You can check status with: systemctl --user status dittokiller"
