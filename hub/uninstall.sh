#!/bin/bash
# ==============================================
# Forest Guardian Hub - Uninstall Script
# ==============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║       🌲 FOREST GUARDIAN HUB UNINSTALLER 🌲           ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

read -p "Are you sure you want to uninstall? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping service..."
sudo systemctl stop forest-guardian 2>/dev/null || true
sudo systemctl disable forest-guardian 2>/dev/null || true
sudo rm -f /etc/systemd/system/forest-guardian.service
sudo systemctl daemon-reload

echo "Removing virtual environment..."
rm -rf venv

echo "Removing generated files..."
rm -f run.sh
rm -f forest-guardian.service
rm -f *.db

read -p "Remove .env file with your credentials? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f .env
fi

echo ""
echo -e "${GREEN}✅ Uninstall complete!${NC}"
echo "   Source files preserved. Delete folder manually if needed."
