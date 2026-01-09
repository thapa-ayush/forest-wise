#!/bin/bash
# =============================================================================
# Forest Guardian Kiosk Mode - Waveshare 5" Display
# Auto-starts Chromium in fullscreen on boot
# =============================================================================

# Wait for desktop and network to be ready
sleep 5

# Wait for Forest Guardian service to be ready
echo "Waiting for Forest Guardian service..."
for i in {1..30}; do
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo "Service is ready!"
        break
    fi
    echo "Attempt $i/30 - waiting..."
    sleep 2
done

# Give it a bit more time to fully initialize
sleep 3

# Disable screen blanking/screensaver
xset s off
xset s noblank
xset -dpms

# Hide mouse cursor after 0.5 seconds of inactivity
unclutter -idle 0.5 -root &

# Remove any Chromium crash flags
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' ~/.config/chromium/Default/Preferences 2>/dev/null
sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' ~/.config/chromium/Default/Preferences 2>/dev/null

# Start Chromium in kiosk mode
/usr/bin/chromium \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --no-first-run \
    --start-fullscreen \
    --window-size=800,480 \
    --window-position=0,0 \
    --disable-translate \
    --disable-features=TranslateUI \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    --check-for-update-interval=31536000 \
    http://localhost:5000/kiosk
