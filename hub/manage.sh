#!/bin/bash
# ==============================================
# Forest Guardian Hub - Service Management
# ==============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_menu() {
    clear
    echo ""
    echo "🌲 ═══════════════════════════════════════════════════"
    echo "   FOREST GUARDIAN HUB - SERVICE MANAGER"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "   1) Start Hub"
    echo "   2) Stop Hub"
    echo "   3) Restart Hub"
    echo "   4) View Status"
    echo "   5) View Logs (live)"
    echo "   6) Enable Auto-Start on Boot"
    echo "   7) Disable Auto-Start"
    echo "   8) Run in Foreground (debug mode)"
    echo "   9) Edit Configuration (.env)"
    echo "   0) Exit"
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo -n "   Select option: "
}

install_service() {
    if [ ! -f "$SCRIPT_DIR/forest-guardian.service" ]; then
        echo "Service file not found. Running installer..."
        "$SCRIPT_DIR/install.sh"
    fi
    sudo cp "$SCRIPT_DIR/forest-guardian.service" /etc/systemd/system/
    sudo systemctl daemon-reload
}

while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            echo "Starting Forest Guardian Hub..."
            install_service
            sudo systemctl start forest-guardian
            echo "✅ Started! Dashboard: http://$(hostname -I | awk '{print $1}'):5000"
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "Stopping Forest Guardian Hub..."
            sudo systemctl stop forest-guardian
            echo "✅ Stopped"
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "Restarting Forest Guardian Hub..."
            sudo systemctl restart forest-guardian
            echo "✅ Restarted"
            read -p "Press Enter to continue..."
            ;;
        4)
            echo ""
            sudo systemctl status forest-guardian || true
            echo ""
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "Showing live logs (Ctrl+C to exit)..."
            sudo journalctl -u forest-guardian -f
            ;;
        6)
            echo "Enabling auto-start..."
            install_service
            sudo systemctl enable forest-guardian
            echo "✅ Will start automatically on boot"
            read -p "Press Enter to continue..."
            ;;
        7)
            echo "Disabling auto-start..."
            sudo systemctl disable forest-guardian
            echo "✅ Auto-start disabled"
            read -p "Press Enter to continue..."
            ;;
        8)
            echo "Running in foreground (Ctrl+C to stop)..."
            "$SCRIPT_DIR/run.sh"
            ;;
        9)
            nano "$SCRIPT_DIR/.env"
            ;;
        0)
            echo "Goodbye! 🌲"
            exit 0
            ;;
        *)
            echo "Invalid option"
            read -p "Press Enter to continue..."
            ;;
    esac
done
