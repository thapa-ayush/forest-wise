#!/bin/bash
# ==============================================
# Forest Guardian Hub - One-Click Installer
# For Raspberry Pi (Tested on Pi 4/5 with Bookworm)
# ==============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║         🌲 FOREST GUARDIAN HUB INSTALLER 🌲           ║"
echo "║              Microsoft Imagine Cup 2026               ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}[1/7]${NC} Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo -e "${BLUE}[2/7]${NC} Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    libopenblas-dev libjpeg-dev zlib1g-dev libpng-dev \
    git spi-tools

echo -e "${BLUE}[3/7]${NC} Enabling SPI interface for LoRa..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
    # Try new location first (Bookworm), then old location
    if [ -f /boot/firmware/config.txt ]; then
        echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
    else
        echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    fi
    echo -e "${YELLOW}SPI enabled - reboot may be required${NC}"
fi

echo -e "${BLUE}[4/7]${NC} Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo -e "${BLUE}[5/7]${NC} Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${BLUE}[6/7]${NC} Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Created .env from .env.example${NC}"
        echo -e "${YELLOW}Please edit .env with your Azure credentials!${NC}"
    else
        # Create minimal .env
        cat > .env << 'EOF'
# Forest Guardian Hub Configuration
# =================================

# Flask settings
FLASK_SECRET_KEY=change-this-to-random-string
FLASK_DEBUG=false

# Azure OpenAI (GPT-4o for spectrogram analysis)
AZURE_OPENAI_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# AI Mode: 'gpt4o', 'custom_vision', or 'auto'
DEFAULT_AI_MODE=gpt4o

# Optional: Azure IoT Hub
# AZURE_IOTHUB_CONN_STR=your-connection-string

# Optional: Azure Communication Services (SMS alerts)
# AZURE_COMMUNICATION_CONN_STR=your-connection-string
EOF
        echo -e "${YELLOW}Created default .env file${NC}"
        echo -e "${YELLOW}Please edit .env with your Azure credentials!${NC}"
    fi
fi

echo -e "${BLUE}[7/7]${NC} Initializing database..."
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized!')" 2>/dev/null || \
python3 -c "from database import init_db; init_db(); print('Database initialized!')" 2>/dev/null || \
echo -e "${YELLOW}Database will be created on first run${NC}"

# Create run script
cat > run.sh << 'EOF'
#!/bin/bash
# Forest Guardian Hub - Run Script
cd "$(dirname "${BASH_SOURCE[0]}")"
source venv/bin/activate
echo "🌲 Starting Forest Guardian Hub..."
echo "   Dashboard: http://$(hostname -I | awk '{print $1}'):5000"
echo "   Press Ctrl+C to stop"
echo ""
python3 app.py
EOF
chmod +x run.sh

# Create systemd service file
cat > forest-guardian.service << EOF
[Unit]
Description=Forest Guardian Hub
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/app.py
Restart=always
RestartSec=10
Environment=PATH=$SCRIPT_DIR/venv/bin:/usr/bin:/bin
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗"
echo "║            ✅ INSTALLATION COMPLETE!                   ║"
echo "╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📋 ${YELLOW}Next Steps:${NC}"
echo ""
echo "   1. Edit your Azure credentials:"
echo -e "      ${BLUE}nano .env${NC}"
echo ""
echo "   2. Run the hub manually:"
echo -e "      ${BLUE}./run.sh${NC}"
echo ""
echo "   3. OR install as auto-start service:"
echo -e "      ${BLUE}sudo cp forest-guardian.service /etc/systemd/system/${NC}"
echo -e "      ${BLUE}sudo systemctl enable forest-guardian${NC}"
echo -e "      ${BLUE}sudo systemctl start forest-guardian${NC}"
echo ""
echo "   4. View service status:"
echo -e "      ${BLUE}sudo systemctl status forest-guardian${NC}"
echo ""
echo -e "🌐 Dashboard URL: ${GREEN}http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your-pi-ip'):5000${NC}"
echo ""
