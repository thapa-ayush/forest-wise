# Deployment & Custom Domain Configuration

This guide covers production deployment of Forest Guardian Hub with Nginx, SSL, custom domain, and Cloudflare Tunnel.

## Table of Contents

- [System Services](#system-services)
- [Nginx Reverse Proxy](#nginx-reverse-proxy)
- [Cloudflare Tunnel Setup](#cloudflare-tunnel-setup)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Kiosk Mode (Waveshare Display)](#kiosk-mode)
- [Troubleshooting](#troubleshooting)

---

## System Services

### Forest Guardian Service

Create `/etc/systemd/system/forest-guardian.service`:

```ini
[Unit]
Description=Forest Guardian Hub
After=network.target

[Service]
Type=simple
User=forestguardain
WorkingDirectory=/home/forestguardain/forest-wise/hub
Environment="PATH=/home/forestguardain/forest-wise/hub/venv/bin"
ExecStart=/home/forestguardain/forest-wise/hub/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable forest-guardian
sudo systemctl start forest-guardian
sudo systemctl status forest-guardian
```

### Managing the Service

```bash
# Start/Stop/Restart
sudo systemctl start forest-guardian
sudo systemctl stop forest-guardian
sudo systemctl restart forest-guardian

# View logs
sudo journalctl -u forest-guardian -f

# Check status
sudo systemctl status forest-guardian
```

---

## Nginx Reverse Proxy

### Installation

```bash
sudo apt update
sudo apt install nginx
```

### Configuration

Create `/etc/nginx/sites-available/forestwise.online`:

```nginx
# Forest Guardian Hub - Nginx Configuration
# Domain: forestwise.online

server {
    listen 80;
    listen [::]:80;
    server_name forestwise.online www.forestwise.online;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    # WebSocket support for Flask-SocketIO
    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
    }

    # Static files optimization
    location /static/ {
        alias /home/forestguardain/forest-wise/hub/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
        try_files $uri $uri/ =404;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/forestwise.online /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Cloudflare Tunnel Setup

Cloudflare Tunnel provides secure access without opening ports, with automatic SSL and IPv4/IPv6 support.

### Installation

```bash
# Download and install cloudflared (ARM64 for Raspberry Pi)
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared.deb
```

### Setup

```bash
# Login to Cloudflare (opens browser)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create forestwise

# Note the tunnel ID from output, e.g.: f07cdf41-efff-40d5-a7d7-9bcf44fb810f
```

### Configuration

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/forestguardain/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: forestwise.online
    service: http://localhost:5000
  - hostname: www.forestwise.online
    service: http://localhost:5000
  - service: http_status:404
```

### DNS Routing

```bash
# Route DNS through tunnel (delete existing A/AAAA records first in Cloudflare dashboard)
cloudflared tunnel route dns forestwise forestwise.online
cloudflared tunnel route dns forestwise www.forestwise.online
```

### Install as System Service

```bash
# Copy config to system location
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/
sudo cp ~/.cloudflared/*.json /etc/cloudflared/

# Install and enable service
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### Domain Registrar Configuration

Update nameservers at your domain registrar (e.g., Namecheap):

1. Go to Domain → Manage → Nameservers
2. Change to **Custom DNS**
3. Add Cloudflare nameservers:
   - `joel.ns.cloudflare.com` (yours may differ)
   - `paislee.ns.cloudflare.com`
4. Delete old nameservers
5. Save and wait 5-30 minutes for propagation

### Managing Cloudflare Tunnel

```bash
# Check status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f

# Restart
sudo systemctl restart cloudflared
```

---

## SSL/TLS Configuration

### With Cloudflare Tunnel (Recommended)

SSL is **automatic** - Cloudflare handles certificates. Your site is accessible via HTTPS immediately.

### With Certbot (Traditional)

If not using Cloudflare Tunnel:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (ensure DNS points to your server first)
sudo certbot --nginx -d forestwise.online -d www.forestwise.online

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

---

## Kiosk Mode

For Waveshare 5" display (800x480) on Raspberry Pi.

### Kiosk Script

Create `/home/forestguardain/forest-wise/hub/kiosk.sh`:

```bash
#!/bin/bash
# Forest Guardian Kiosk Mode

# Wait for desktop and service
sleep 5

echo "Waiting for Forest Guardian service..."
for i in {1..30}; do
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo "Service is ready!"
        break
    fi
    echo "Attempt $i/30 - waiting..."
    sleep 2
done

sleep 3

# Disable screen blanking
xset s off
xset s noblank
xset -dpms 2>/dev/null

# Hide cursor
unclutter -idle 0.5 -root &

# Clear Chromium crash flags
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
    http://localhost:5000/kiosk
```

Make executable:

```bash
chmod +x /home/forestguardain/forest-wise/hub/kiosk.sh
```

### Systemd User Service

Create `~/.config/systemd/user/forest-kiosk.service`:

```ini
[Unit]
Description=Forest Guardian Kiosk Display
After=graphical-session.target forest-guardian.service
Wants=forest-guardian.service

[Service]
Type=simple
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 10
ExecStart=/home/forestguardain/forest-wise/hub/kiosk.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
```

Enable:

```bash
mkdir -p ~/.config/systemd/user
systemctl --user daemon-reload
systemctl --user enable forest-kiosk
sudo loginctl enable-linger $USER
```

### Desktop Autostart (Alternative)

Create `~/.config/autostart/forest-kiosk.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Forest Guardian Kiosk
Exec=/home/forestguardain/forest-wise/hub/kiosk.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
```

### Managing Kiosk

```bash
# Start/stop/restart
systemctl --user start forest-kiosk
systemctl --user stop forest-kiosk
systemctl --user restart forest-kiosk

# Refresh display
DISPLAY=:0 xdotool key ctrl+F5

# Kill and restart Chromium
pkill chromium && systemctl --user restart forest-kiosk
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u forest-guardian -n 50

# Verify Python environment
source /home/forestguardain/forest-wise/hub/venv/bin/activate
python app.py
```

### Nginx 502 Bad Gateway

```bash
# Check if Flask is running
curl http://localhost:5000

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

### Cloudflare Tunnel Not Working

```bash
# Check tunnel status
sudo systemctl status cloudflared

# Verify config
cat /etc/cloudflared/config.yml

# Check DNS propagation
host forestwise.online
```

### Site Not Loading (DNS)

```bash
# Check nameservers
host -t NS forestwise.online

# Check if Cloudflare nameservers are active
# Should show: joel.ns.cloudflare.com, paislee.ns.cloudflare.com
```

### Kiosk Display Issues

```bash
# Check if X is running
echo $DISPLAY

# Manual test
DISPLAY=:0 chromium --kiosk http://localhost:5000/kiosk &

# Check service status
systemctl --user status forest-kiosk
```

---

## Quick Reference

| Service | Command |
|---------|---------|
| Forest Guardian | `sudo systemctl {start\|stop\|restart\|status} forest-guardian` |
| Nginx | `sudo systemctl {start\|stop\|restart\|status} nginx` |
| Cloudflared | `sudo systemctl {start\|stop\|restart\|status} cloudflared` |
| Kiosk | `systemctl --user {start\|stop\|restart\|status} forest-kiosk` |

| URL | Purpose |
|-----|---------|
| `http://localhost:5000` | Local dashboard |
| `http://localhost:5000/kiosk` | Kiosk display |
| `https://forestwise.online` | Public dashboard |

---

*Last updated: January 2026*
