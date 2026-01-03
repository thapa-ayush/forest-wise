# Forest Guardian - Raspberry Pi LoRa Hub Setup

## Quick Start (One-Click Install) 🚀

```bash
# 1. Clone or copy the project to your Pi
cd ~/forest_guardian/hub

# 2. Make scripts executable
chmod +x install.sh run.sh manage.sh

# 3. Run the installer
./install.sh

# 4. Edit your Azure credentials
nano .env

# 5. Start the hub
./run.sh
```

**That's it!** Dashboard will be at `http://your-pi-ip:5000`

### Service Management Menu
```bash
./manage.sh
```
Provides an interactive menu to start/stop/restart, view logs, enable auto-start, etc.

---

## Overview

The Raspberry Pi serves as the **central hub** that receives alerts from Forest Guardian nodes via LoRa and forwards them to Azure cloud services for verification and ranger notification.

### System Architecture

```
┌─────────────────┐     LoRa 915MHz     ┌─────────────────────────────────────┐
│  Guardian Node  │ ──────────────────► │         Raspberry Pi Hub            │
│  (ESP32 + LoRa) │                     │  ┌─────────┐    ┌────────────────┐  │
└─────────────────┘                     │  │ SX1262  │───►│ Python Server  │  │
                                        │  │ Module  │    │                │  │
┌─────────────────┐     LoRa 915MHz     │  └─────────┘    └───────┬────────┘  │
│  Guardian Node  │ ──────────────────► │                         │           │
│  (ESP32 + LoRa) │                     └─────────────────────────┼───────────┘
└─────────────────┘                                               │
                                                                  │ HTTPS
┌─────────────────┐     LoRa 915MHz                               ▼
│  Guardian Node  │ ──────────────────►                  ┌─────────────────┐
│  (ESP32 + LoRa) │                                      │   Azure Cloud   │
└─────────────────┘                                      │  - IoT Hub      │
                                                         │  - Functions    │
                                                         │  - Custom Vision│
                                                         └─────────────────┘
```

---

## Hardware Requirements

### Raspberry Pi

| Component | Recommended | Minimum |
|-----------|-------------|---------|
| Model | Raspberry Pi 4 (4GB) | Raspberry Pi 3B+ |
| Storage | 32GB microSD | 16GB microSD |
| Power | 5V 3A USB-C | 5V 2.5A |
| OS | Raspberry Pi OS (64-bit) | Raspberry Pi OS Lite |

### LoRa Module Options

#### Option 1: Waveshare SX1262 HAT (Recommended)

| Specification | Value |
|---------------|-------|
| Chip | SX1262 |
| Frequency | 868/915 MHz |
| Interface | SPI |
| Antenna | SMA connector |
| Price | ~$25 |

**Wiring**: Plugs directly onto GPIO header (HAT form factor)

#### Option 2: RFM95W Module

| Specification | Value |
|---------------|-------|
| Chip | SX1276 |
| Frequency | 915 MHz |
| Interface | SPI |
| Price | ~$15 |

---

## Detailed Wiring Diagrams

### RFM95W / SX1276 to Raspberry Pi

```
                    RASPBERRY PI GPIO HEADER
                    ┌─────────────────────────────────────┐
                    │  (1) 3.3V PWR ●────────┐            │
                    │  (2) 5V PWR   ○        │            │
                    │  (3) GPIO 2   ○        │            │
                    │  (4) 5V PWR   ○        │            │
                    │  (5) GPIO 3   ○        │            │
                    │  (6) GND      ●────────┼──┐         │
                    │  (7) GPIO 4   ○        │  │         │
                    │  (8) GPIO 14  ○        │  │         │
                    │  (9) GND      ○        │  │         │
                    │ (10) GPIO 15  ○        │  │         │
                    │ (11) GPIO 17  ○        │  │         │
                    │ (12) GPIO 18  ○        │  │         │
                    │ (13) GPIO 27  ○        │  │         │
                    │ (14) GND      ○        │  │         │
                    │ (15) GPIO 22  ●────────┼──┼──┐      │  ← RST
                    │ (16) GPIO 23  ○        │  │  │      │
                    │ (17) 3.3V PWR ○        │  │  │      │
                    │ (18) GPIO 24  ○        │  │  │      │
                    │ (19) GPIO 10  ●────────┼──┼──┼──┐   │  ← MOSI
                    │ (20) GND      ○        │  │  │  │   │
                    │ (21) GPIO 9   ●────────┼──┼──┼──┼─┐ │  ← MISO
                    │ (22) GPIO 25  ●────────┼──┼──┼──┼─┼─┤  ← DIO0
                    │ (23) GPIO 11  ●────────┼──┼──┼──┼─┼─┼─┐  ← SCK
                    │ (24) GPIO 8   ●────────┼──┼──┼──┼─┼─┼─┼─┐ ← NSS/CS
                    │ (25) GND      ○        │  │  │  │ │ │ │ │
                    │ (26) GPIO 7   ○        │  │  │  │ │ │ │ │
                    └─────────────────────────┼──┼──┼──┼─┼─┼─┼─┼─┘
                                              │  │  │  │ │ │ │ │
                    ┌─────────────────────────┼──┼──┼──┼─┼─┼─┼─┼─┐
                    │      RFM95W MODULE      │  │  │  │ │ │ │ │ │
                    │  ┌──────────────────┐   │  │  │  │ │ │ │ │ │
                    │  │                  │   │  │  │  │ │ │ │ │ │
                    │  │    SX1276        │   │  │  │  │ │ │ │ │ │
                    │  │                  │   │  │  │  │ │ │ │ │ │
                    │  └──────────────────┘   │  │  │  │ │ │ │ │ │
                    │                         │  │  │  │ │ │ │ │ │
                    │  VCC ●──────────────────┘  │  │  │ │ │ │ │ │
                    │  GND ●─────────────────────┘  │  │ │ │ │ │ │
                    │  RST ●────────────────────────┘  │ │ │ │ │ │
                    │ MOSI ●───────────────────────────┘ │ │ │ │ │
                    │ MISO ●─────────────────────────────┘ │ │ │ │
                    │ DIO0 ●───────────────────────────────┘ │ │ │
                    │  SCK ●─────────────────────────────────┘ │ │
                    │  NSS ●───────────────────────────────────┘ │
                    │  ANT ○──[Antenna]                          │
                    └────────────────────────────────────────────┘
```

### Wiring Table - RFM95W / SX1276

**Your module pins (as labeled on PCB):**
```
DIO2 | DIO1 | DIO0 | 3.3V | DIO4 | DIO5 | GND | ANT
─────┴──────┴──────┴──────┴──────┴──────┴─────┴─────
GND | MISO | MOSI | SCK | NSS | RESET | DIO3 | GND
```

| Your Module Pin | Wire Color | Raspberry Pi | Physical Pin | Description |
|-----------------|------------|--------------|--------------|-------------|
| **3.3V** | 🔴 Red | 3.3V | Pin 1 | Power (3.3V ONLY!) |
| **GND** | ⚫ Black | GND | Pin 6 | Ground (any GND) |
| **SCK** | 🟡 Yellow | GPIO 11 (SCLK) | Pin 23 | SPI Clock |
| **MISO** (MSO) | 🟢 Green | GPIO 9 (MISO) | Pin 21 | SPI Data Out |
| **MOSI** (MOS1) | 🔵 Blue | GPIO 10 (MOSI) | Pin 19 | SPI Data In |
| **NSS** | 🟠 Orange | GPIO 8 (CE0) | Pin 24 | Chip Select |
| **RESET** | ⚪ White | GPIO 22 | Pin 15 | Reset |
| **DIO0** (DIOO) | 🟣 Purple | GPIO 25 | Pin 22 | RX Done Interrupt |
| **ANT** (ANA) | - | - | - | Connect antenna! |
| DIO1 | - | Not connected | - | Optional |
| DIO2 | - | Not connected | - | Optional |
| DIO3 | - | Not connected | - | Optional |
| DIO4 | - | Not connected | - | Optional |
| DIO5 | - | Not connected | - | Optional |

### Only 8 Wires Needed!

```
YOUR LORA MODULE                          RASPBERRY PI
┌────────────────┐                    ┌─────────────────┐
│                │                    │   GPIO HEADER   │
│  3.3V ●────────┼── 🔴 Red ─────────┼──● Pin 1 (3.3V) │
│                │                    │                 │
│  GND  ●────────┼── ⚫ Black ────────┼──● Pin 6 (GND)  │
│                │                    │                 │
│  SCK  ●────────┼── 🟡 Yellow ──────┼──● Pin 23 (GPIO11)
│                │                    │                 │
│  MISO ●────────┼── 🟢 Green ───────┼──● Pin 21 (GPIO9)
│  (MSO)         │                    │                 │
│                │                    │                 │
│  MOSI ●────────┼── 🔵 Blue ────────┼──● Pin 19 (GPIO10)
│  (MOS1)        │                    │                 │
│                │                    │                 │
│  NSS  ●────────┼── 🟠 Orange ──────┼──● Pin 24 (GPIO8)
│                │                    │                 │
│  RESET●────────┼── ⚪ White ───────┼──● Pin 15 (GPIO22)
│                │                    │                 │
│  DIO0 ●────────┼── 🟣 Purple ──────┼──● Pin 22 (GPIO25)
│  (DIOO)        │                    │                 │
│                │                    └─────────────────┘
│  ANT ○───[Antenna]                  
│  (ANA)         │                    
│                │                    
│  DIO1 ○ (not connected)            
│  DIO2 ○ (not connected)            
│  DIO3 ○ (not connected)            
│  DIO4 ○ (not connected)            
│  DIO5 ○ (not connected)            
└────────────────┘                    
```

### Quick Reference - Connect These 8 Pins:

| # | Module → Pi | Color |
|---|-------------|-------|
| 1 | 3.3V → Pin 1 | 🔴 |
| 2 | GND → Pin 6 | ⚫ |
| 3 | SCK → Pin 23 | 🟡 |
| 4 | MISO → Pin 21 | 🟢 |
| 5 | MOSI → Pin 19 | 🔵 |
| 6 | NSS → Pin 24 | 🟠 |
| 7 | RESET → Pin 15 | ⚪ |
| 8 | DIO0 → Pin 22 | 🟣 |

+ **Antenna** to ANT pin!

### Wiring Table - SX1262 Breakout (Non-HAT version)

| SX1262 Pin | Wire Color | Raspberry Pi | Physical Pin | Description |
|------------|------------|--------------|--------------|-------------|
| **VCC** | 🔴 Red | 3.3V | Pin 1 | Power (3.3V ONLY!) |
| **GND** | ⚫ Black | GND | Pin 6 | Ground |
| **SCK** | 🟡 Yellow | GPIO 11 (SCLK) | Pin 23 | SPI Clock |
| **MISO** | 🟢 Green | GPIO 9 (MISO) | Pin 21 | SPI Data Out |
| **MOSI** | 🔵 Blue | GPIO 10 (MOSI) | Pin 19 | SPI Data In |
| **NSS/CS** | 🟠 Orange | GPIO 8 (CE0) | Pin 24 | Chip Select |
| **RST** | ⚪ White | GPIO 22 | Pin 15 | Reset |
| **BUSY** | 🟤 Brown | GPIO 23 | Pin 16 | Busy indicator |
| **DIO1** | 🟣 Purple | GPIO 25 | Pin 22 | Interrupt |
| **ANT** | - | - | - | Connect antenna! |

### Physical Connection Diagram

```
      RASPBERRY PI (Top View - USB ports facing down)
    ┌─────────────────────────────────────────────────┐
    │ ┌─────┐                               ┌─────┐  │
    │ │ USB │                               │ USB │  │
    │ └─────┘                               └─────┘  │
    │                                                │
    │  ┌─────────────────────────────────────────┐   │
    │  │ GPIO HEADER                             │   │
    │  │  ●  ○  ○  ○  ○  ○  ○  ○  ○  ○  ○  ○  ○ │   │
    │  │ 3V3    5V                              │   │
    │  │                                        │   │
    │  │  ○  ●  ○  ○  ○  ○  ●  ○  ●  ○  ●  ●  ○ │   │
    │  │    GND          RST   MOSI MISO SCK CS │   │
    │  │                  22    10   9   11  8  │   │
    │  └─────────────────────────────────────────┘   │
    │                     │     │    │   │   │       │
    │   ┌─────────────────┴─────┴────┴───┴───┴──┐    │
    │   │                                       │    │
    │   │  Wires to LoRa Module                 │    │
    │   │                                       │    │
    │   └───────────────────────────────────────┘    │
    │                                                │
    │  ┌──────┐  ┌──────────┐                       │
    │  │ ETH  │  │  HDMI    │     [SD CARD SLOT]   │
    │  └──────┘  └──────────┘                       │
    └─────────────────────────────────────────────────┘

              LoRa MODULE (RFM95W)
         ┌─────────────────────────┐
         │   ┌───────────────┐     │
         │   │    SX1276     │     │
         │   │    CHIP       │     │
         │   └───────────────┘     │
         │                         │
   ANT ──┤ ○                       │
         │ ○ GND  ← Black wire     │
         │ ○ DIO5                  │
         │ ○ DIO4                  │
         │ ○ DIO3                  │
         │ ○ DIO2                  │
         │ ○ DIO1                  │
         │ ● DIO0 ← Purple wire    │
         │ ○ 3.3V                  │
         │                         │
         │ ● VCC  ← Red wire (3.3V)│
         │ ● GND  ← Black wire     │
         │ ● SCK  ← Yellow wire    │
         │ ● MISO ← Green wire     │
         │ ● MOSI ← Blue wire      │
         │ ● NSS  ← Orange wire    │
         │ ● RST  ← White wire     │
         └─────────────────────────┘
                   │
                   ▼
              [ANTENNA]
         (Wire or SMA connector)
```

### ⚠️ IMPORTANT WARNINGS

1. **Use 3.3V ONLY** - The LoRa module runs on 3.3V. Using 5V will destroy it!
2. **Connect antenna BEFORE powering on** - Transmitting without antenna can damage the module
3. **Double-check wiring** before powering on
4. **Keep wires short** - Long wires can cause signal issues on SPI

---

#### Option 3: Dragino LoRa/GPS HAT

| Specification | Value |
|---------------|-------|
| Chip | SX1276/SX1278 |
| Frequency | 868/915 MHz |
| Bonus | Built-in GPS |
| Interface | SPI |
| Price | ~$35 |

---

## Software Setup

### Step 1: Enable SPI

```bash
sudo raspi-config
```

Navigate to: `Interface Options` → `SPI` → `Enable`

Reboot:
```bash
sudo reboot
```

Verify SPI is enabled:
```bash
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1
```

### Step 2: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install SPI library
sudo apt install -y python3-spidev

# Create project directory
mkdir -p ~/forest_guardian_hub
cd ~/forest_guardian_hub

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install spidev RPi.GPIO pycryptodome azure-iot-device requests
```

### Step 3: Install LoRa Library

For **SX1262** (Waveshare HAT):
```bash
pip install pyLoRa
# Or use the sx126x library
git clone https://github.com/waveshare/SX126X-LoRa-HAT.git
cd SX126X-LoRa-HAT
pip install .
```

For **RFM95W/SX1276**:
```bash
pip install adafruit-circuitpython-rfm9x
```

---

## Hub Software

### Option 1: Using Waveshare SX1262

Create `lora_hub.py`:

```python
#!/usr/bin/env python3
"""
Forest Guardian - LoRa Hub Receiver
Receives alerts from Guardian nodes and forwards to Azure
"""

import json
import time
from datetime import datetime
import sys
sys.path.append('/home/pi/SX126X-LoRa-HAT')

from sx126x import sx126x

# LoRa Configuration - MUST MATCH NODES
FREQUENCY = 915  # MHz (use 868 for EU)
SPREADING_FACTOR = 7
BANDWIDTH = 125  # kHz
CODING_RATE = 1  # 4/5

# Initialize LoRa
lora = sx126x(serial_num="/dev/ttyS0", freq=FREQUENCY, addr=0, power=22, rssi=True)

print("=" * 50)
print("Forest Guardian Hub - LoRa Receiver")
print("=" * 50)
print(f"Frequency: {FREQUENCY} MHz")
print(f"Spreading Factor: {SPREADING_FACTOR}")
print(f"Bandwidth: {BANDWIDTH} kHz")
print("Listening for alerts...")
print("=" * 50)

def process_message(data, rssi):
    """Process received LoRa message"""
    try:
        # Parse JSON message
        message = json.loads(data.decode('utf-8'))
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n[{timestamp}] Message Received (RSSI: {rssi} dBm)")
        print(f"  Node ID: {message.get('node_id', 'Unknown')}")
        print(f"  Type: {message.get('type', 'Unknown')}")
        
        if message.get('type') == 'alert':
            print(f"  🚨 CHAINSAW ALERT!")
            print(f"  Confidence: {message.get('confidence', 0)}%")
            print(f"  Location: {message.get('lat', 0)}, {message.get('lon', 0)}")
            print(f"  Battery: {message.get('battery', 0)}%")
            
            # Forward to Azure (implement your Azure connection here)
            forward_to_azure(message)
            
        elif message.get('type') == 'heartbeat':
            print(f"  💓 Heartbeat from node")
            print(f"  Battery: {message.get('battery', 0)}%")
            
    except json.JSONDecodeError:
        print(f"  [Warning] Non-JSON message: {data}")
    except Exception as e:
        print(f"  [Error] Processing message: {e}")

def forward_to_azure(message):
    """Forward alert to Azure IoT Hub"""
    # TODO: Implement Azure IoT Hub connection
    # See Azure Integration section below
    print("  → Forwarding to Azure...")
    pass

# Main receive loop
while True:
    try:
        data = lora.receive()
        if data:
            rssi = lora.get_rssi()
            process_message(data, rssi)
    except KeyboardInterrupt:
        print("\nShutting down...")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
```

### Option 2: Using RFM95W with Adafruit Library

Create `lora_hub_rfm95.py`:

```python
#!/usr/bin/env python3
"""
Forest Guardian - LoRa Hub Receiver (RFM95W Version)
"""

import json
import time
from datetime import datetime
import board
import busio
import digitalio
import adafruit_rfm9x

# Configure SPI
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Configure pins
cs = digitalio.DigitalInOut(board.CE0)
reset = digitalio.DigitalInOut(board.D22)

# Initialize RFM95W
# MUST MATCH NODE SETTINGS
FREQUENCY = 915.0  # MHz

rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, FREQUENCY)
rfm9x.spreading_factor = 7
rfm9x.signal_bandwidth = 125000
rfm9x.coding_rate = 5
rfm9x.tx_power = 20

print("=" * 50)
print("Forest Guardian Hub - RFM95W Receiver")
print("=" * 50)
print(f"Frequency: {FREQUENCY} MHz")
print("Listening for alerts...")
print("=" * 50)

def process_message(packet, rssi):
    """Process received LoRa message"""
    try:
        # Decode and parse JSON
        data = packet.decode('utf-8')
        message = json.loads(data)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n[{timestamp}] Message Received (RSSI: {rssi} dBm)")
        print(f"  Node ID: {message.get('node_id', 'Unknown')}")
        print(f"  Type: {message.get('type', 'Unknown')}")
        
        if message.get('type') == 'alert':
            print(f"  🚨 CHAINSAW ALERT!")
            print(f"  Confidence: {message.get('confidence', 0)}%")
            print(f"  Location: {message.get('lat', 0)}, {message.get('lon', 0)}")
            print(f"  Battery: {message.get('battery', 0)}%")
            
        elif message.get('type') == 'heartbeat':
            print(f"  💓 Heartbeat")
            print(f"  Battery: {message.get('battery', 0)}%")
            
    except Exception as e:
        print(f"  [Error] {e}")

# Main receive loop
while True:
    try:
        packet = rfm9x.receive(timeout=5.0)
        if packet is not None:
            rssi = rfm9x.last_rssi
            process_message(packet, rssi)
    except KeyboardInterrupt:
        print("\nShutting down...")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
```

---

## LoRa Settings - Must Match Nodes!

The hub MUST use identical LoRa settings as the Guardian nodes:

| Parameter | Value | Notes |
|-----------|-------|-------|
| Frequency | 915 MHz | US/Australia (868 MHz for EU) |
| Spreading Factor | **10** | SF10 for long range |
| Bandwidth | 125 kHz | Standard |
| Coding Rate | 4/5 | Error correction |
| Sync Word | **0x12** | Private network (CRITICAL!) |
| TX Power | 14 dBm | Node default |

Check node settings in `firmware/guardian_node/config.h`:
```cpp
#define LORA_FREQ 915.0
#define LORA_SPREADING_FACTOR 10
#define LORA_BANDWIDTH 125.0
#define LORA_SYNC_WORD 0x12  // MUST MATCH HUB!
```

---

## Message Format

Messages from Guardian nodes are JSON:

### Alert Message
```json
{
  "node_id": "GUARDIAN_001",
  "type": "alert",
  "confidence": 85,
  "lat": 27.7172,
  "lon": 85.3240,
  "battery": 78,
  "timestamp": 12345,
  "alerts": 5,
  "tx_count": 23
}
```

### Heartbeat Message
```json
{
  "node_id": "GUARDIAN_001", 
  "type": "heartbeat",
  "battery": 82,
  "timestamp": 12400
}
```

---

## Running as a Service

### Create Systemd Service

```bash
sudo nano /etc/systemd/system/forest-guardian-hub.service
```

Add:
```ini
[Unit]
Description=Forest Guardian LoRa Hub
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/forest_guardian_hub
ExecStart=/home/pi/forest_guardian_hub/venv/bin/python lora_hub.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable forest-guardian-hub
sudo systemctl start forest-guardian-hub
```

Check status:
```bash
sudo systemctl status forest-guardian-hub
```

View logs:
```bash
journalctl -u forest-guardian-hub -f
```

---

## Azure Integration

### Azure IoT Hub Connection

Add to `lora_hub.py`:

```python
from azure.iot.device import IoTHubDeviceClient, Message
import os

# Azure IoT Hub connection string (from environment or config)
CONNECTION_STRING = os.getenv('AZURE_IOT_CONNECTION_STRING')

# Initialize Azure client
azure_client = None
if CONNECTION_STRING:
    azure_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    azure_client.connect()
    print("Connected to Azure IoT Hub")

def forward_to_azure(message):
    """Forward alert to Azure IoT Hub"""
    if azure_client:
        try:
            azure_message = Message(json.dumps(message))
            azure_message.content_type = "application/json"
            azure_message.content_encoding = "utf-8"
            
            # Add custom properties
            azure_message.custom_properties["alert_type"] = message.get('type', 'unknown')
            azure_message.custom_properties["node_id"] = message.get('node_id', 'unknown')
            
            azure_client.send_message(azure_message)
            print("  ✓ Sent to Azure IoT Hub")
        except Exception as e:
            print(f"  ✗ Azure send failed: {e}")
    else:
        print("  [Warning] Azure not configured")
```

Set environment variable:
```bash
export AZURE_IOT_CONNECTION_STRING="HostName=xxx.azure-devices.net;DeviceId=hub-001;SharedAccessKey=xxx"
```

---

## Web Dashboard (Optional)

Create a simple Flask dashboard to view alerts:

`dashboard.py`:
```python
from flask import Flask, render_template, jsonify
from datetime import datetime
import json

app = Flask(__name__)

# Store recent alerts in memory
alerts = []
MAX_ALERTS = 100

def add_alert(alert_data):
    """Add alert to list"""
    alert_data['received_at'] = datetime.now().isoformat()
    alerts.insert(0, alert_data)
    if len(alerts) > MAX_ALERTS:
        alerts.pop()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/alerts')
def get_alerts():
    return jsonify(alerts)

@app.route('/api/stats')
def get_stats():
    return jsonify({
        'total_alerts': len([a for a in alerts if a.get('type') == 'alert']),
        'active_nodes': len(set(a.get('node_id') for a in alerts)),
        'last_alert': alerts[0]['received_at'] if alerts else None
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## Troubleshooting

### No Messages Received

1. **Check LoRa settings match exactly** between hub and nodes
2. **Verify antenna is connected** to LoRa module
3. **Check SPI is enabled**: `ls /dev/spi*`
4. **Verify wiring** if using breakout module
5. **Check frequency** - US: 915MHz, EU: 868MHz

### SPI Errors

```bash
# Check SPI devices
ls -la /dev/spi*

# Check kernel modules
lsmod | grep spi

# Enable SPI if missing
sudo raspi-config
# Interface Options → SPI → Enable
```

### Permission Errors

```bash
# Add user to spi and gpio groups
sudo usermod -a -G spi,gpio pi
# Logout and login again
```

### Weak Signal (Low RSSI)

- Use proper antenna (not just wire)
- Keep antenna vertical
- Reduce obstructions between node and hub
- Lower spreading factor = less range but faster

---

## Testing

### Test LoRa Reception

```bash
cd ~/forest_guardian_hub
source venv/bin/activate
python lora_hub.py
```

Then trigger an alert on a Guardian node.

### Test with Simulated Message

On the node, you can force an alert via Serial command or by playing chainsaw sounds.

### Expected Output

```
==================================================
Forest Guardian Hub - LoRa Receiver
==================================================
Frequency: 915 MHz
Spreading Factor: 7
Bandwidth: 125 kHz
Listening for alerts...
==================================================

[2026-01-01 20:30:45] Message Received (RSSI: -65 dBm)
  Node ID: GUARDIAN_001
  Type: alert
  🚨 CHAINSAW ALERT!
  Confidence: 85%
  Location: 27.7172, 85.3240
  Battery: 78%
  → Forwarding to Azure...
  ✓ Sent to Azure IoT Hub
```

---

## Hardware Checklist

Before deployment:

- [ ] Raspberry Pi powered and booted
- [ ] LoRa module properly connected
- [ ] Antenna attached to LoRa module
- [ ] SPI enabled in raspi-config
- [ ] Python environment set up
- [ ] LoRa settings match Guardian nodes
- [ ] Service starts on boot
- [ ] Azure connection configured (optional)
- [ ] Network connectivity for cloud upload

---

## File Structure

```
~/forest_guardian_hub/
├── venv/                    # Python virtual environment
├── lora_hub.py              # Main hub receiver script
├── dashboard.py             # Optional web dashboard
├── templates/
│   └── index.html           # Dashboard template
├── config.json              # Configuration file
└── logs/                    # Log files
    └── alerts.log
```

---

## References

- [Waveshare SX1262 HAT Wiki](https://www.waveshare.com/wiki/SX1262_868M_LoRa_HAT)
- [Adafruit RFM9x CircuitPython](https://learn.adafruit.com/adafruit-rfm69hcw-and-rfm96-rfm95-rfm98-lora-packet-padio-breakouts)
- [Azure IoT Hub Python SDK](https://docs.microsoft.com/en-us/azure/iot-hub/quickstart-send-telemetry-python)
- [LoRa Frequency Regulations](https://www.thethingsnetwork.org/docs/lorawan/frequencies-by-country/)

---

**Project**: Forest Guardian - Microsoft Imagine Cup 2026
