#!/bin/bash
# ==============================================
# Forest Guardian Hub - Quick Run Script
# ==============================================

cd "$(dirname "${BASH_SOURCE[0]}")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run ./install.sh first"
    exit 1
fi

source venv/bin/activate

# Get IP address
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "🌲 ═══════════════════════════════════════════════════"
echo "   FOREST GUARDIAN HUB"
echo "   Microsoft Imagine Cup 2026"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "   📡 LoRa Receiver: Starting..."
echo "   🌐 Dashboard:     http://$IP:5000"
echo "   🔧 Local:         http://localhost:5000"
echo ""
echo "   Press Ctrl+C to stop"
echo "═══════════════════════════════════════════════════════"
echo ""

python3 app.py
