# 🌲 Forest Guardian: AI-Powered Illegal Logging Detection System

<div align="center">

![Forest Guardian](https://img.shields.io/badge/Forest-Guardian-228B22?style=for-the-badge&logo=tree&logoColor=white)
![Azure](https://img.shields.io/badge/Microsoft-Azure-0089D6?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-S3-E7352C?style=for-the-badge&logo=espressif&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

### **🏆 Microsoft Imagine Cup 2026 Entry**

**Real-time acoustic monitoring system that detects illegal logging using AI-powered sound classification, LoRa mesh networking, and Azure cloud services**

*Developed by Ayush Thapa*

[🎯 Problem](#-the-problem) • [�� Solution](#-our-solution) • [🏗️ Architecture](#️-system-architecture) • [☁️ Azure Services](#️-azure-integration) • [📊 Features](#-features) • [🚀 Demo](#-usage-scenarios)

</div>

---

## 🌍 The Problem

### Illegal Logging: A Global Crisis

- **🌲 10 million hectares** of forest lost annually to illegal logging
- **💰 $50-150 billion** global revenue from illegal timber trade
- **🦎 Biodiversity loss** - 80% of terrestrial species depend on forests
- **🌡️ Climate impact** - Deforestation causes 10% of global carbon emissions
- **⏰ Detection delay** - Most illegal logging detected days or weeks after occurrence

### Current Solutions Fall Short

| Current Method | Limitation |
|----------------|------------|
| Satellite imagery | Days to weeks delay, cloud cover issues |
| Manual patrols | Expensive, dangerous, limited coverage |
| Fixed cameras | Short range, easily avoided, no real-time alerts |
| Mobile reports | Relies on witnesses, usually after damage done |

**The Gap:** No affordable, real-time detection system exists for remote forest areas without infrastructure.

---

## 💡 Our Solution

**Forest Guardian** is an end-to-end acoustic monitoring system that detects chainsaw activity **within seconds** using:

<table>
<tr>
<td width="33%" align="center">
<h3>🎤 Edge Sensors</h3>
<p>Solar-powered ESP32 nodes with AI-assisted sound detection, deployed throughout the forest</p>
</td>
<td width="33%" align="center">
<h3>📡 LoRa Network</h3>
<p>Long-range (15km+), low-power wireless mesh network requiring no cellular or internet infrastructure</p>
</td>
<td width="33%" align="center">
<h3>🧠 Azure AI</h3>
<p>Multi-tier AI analysis: Local TFLite → Custom Vision → GPT-4o Vision for maximum accuracy</p>
</td>
</tr>
</table>

### Key Innovation: Spectrogram-Based Detection

Instead of transmitting raw audio (which would require too much bandwidth), Forest Guardian:

1. **Captures** 2-second audio samples at 16kHz
2. **Generates** 32x32 mel-frequency spectrograms on-device
3. **Compresses** to ~2KB per detection (vs 64KB for raw audio)
4. **Transmits** via LoRa to central hub
5. **Analyzes** using Azure AI for classification

This approach enables **real-time detection** even in areas with **zero internet connectivity**.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              🌲 FOREST (Remote Area)                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌────────────────┐     ┌────────────────┐     ┌────────────────┐              │
│   │  🛰️ GUARDIAN    │     │  🛰️ GUARDIAN    │     │  🛰️ GUARDIAN    │              │
│   │   NODE #001    │     │   NODE #002    │     │   NODE #003    │              │
│   │                │     │                │     │                │              │
│   │ • ESP32-S3     │     │ • ESP32-S3     │     │ • ESP32-S3     │              │
│   │ • INMP441 Mic  │     │ • INMP441 Mic  │     │ • INMP441 Mic  │              │
│   │ • GPS Module   │     │ • GPS Module   │     │ • GPS Module   │              │
│   │ • Solar Panel  │     │ • Solar Panel  │     │ • Solar Panel  │              │
│   │ • LoRa SX1262  │     │ • LoRa SX1262  │     │ • LoRa SX1262  │              │
│   └───────┬────────┘     └───────┬────────┘     └───────┬────────┘              │
│           │                      │                      │                        │
│           │      ═══════════════════════════════       │                        │
│           └──────────────► LoRa 915MHz ◄───────────────┘                        │
│                            (Up to 15km)                                          │
│                                 │                                                │
│                                 ▼                                                │
│                    ┌───────────────────────┐                                     │
│                    │   🖥️ RASPBERRY PI HUB  │                                     │
│                    │                       │                                     │
│                    │  • RFM95W LoRa Radio  │                                     │
│                    │  • Flask Web Server   │                                     │
│                    │  • SQLite Database    │                                     │
│                    │  • Local TFLite AI    │                                     │
│                    │  • Real-time WebSocket│                                     │
│                    │  • Offline Queue      │                                     │
│                    └───────────┬───────────┘                                     │
│                                │                                                 │
└────────────────────────────────┼─────────────────────────────────────────────────┘
                                 │
                                 │ 🌐 Internet (WiFi/4G)
                                 │    (When Available)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ☁️ MICROSOFT AZURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  🧠 Azure OpenAI │  │  👁️ Custom Vision│  │  🗺️ Azure Maps   │                  │
│  │                 │  │                 │  │                 │                  │
│  │  GPT-4o Vision  │  │  Spectrogram    │  │  Interactive    │                  │
│  │  Spectrogram    │  │  Classifier     │  │  Node Map       │                  │
│  │  Analysis       │  │  (88.9% Prec.)  │  │  Satellite View │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  📊 Cosmos DB   │  │  ⚡ Functions    │  │  📱 Comm Services│                  │
│  │   (Optional)    │  │                 │  │   (Optional)    │                  │
│  │                 │  │  Alert Triggers │  │                 │                  │
│  │  Cloud Storage  │  │  Daily Reports  │  │  SMS Alerts     │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ☁️ Azure Integration

Forest Guardian leverages **7 Azure services** to deliver a comprehensive solution:

### 1. 🧠 Azure OpenAI (GPT-4o Vision)
**Purpose:** Primary AI analysis engine for spectrogram classification

- Analyzes mel-frequency spectrogram images
- Provides detailed reasoning for each classification
- Identifies specific acoustic patterns (chainsaw RPM bands, engine harmonics)
- Recommends actions for forest rangers

```
Example Response:
┌─────────────────────────────────────────────────────────────┐
│ 🔴 CHAINSAW DETECTED - 94% Confidence                       │
│                                                             │
│ Reasoning:                                                  │
│ • Clear horizontal bands at 50-100Hz (chainsaw engine RPM)  │
│ • Periodic pattern consistent with cutting motion           │
│ • Harmonic overtones typical of 2-stroke engine             │
│                                                             │
│ Threat Level: CRITICAL                                      │
│ Action: Dispatch ranger immediately to GPS coordinates      │
└─────────────────────────────────────────────────────────────┘
```

### 2. 👁️ Azure Custom Vision
**Purpose:** Fast, cost-effective classification with locally trainable model

| Metric | Value |
|--------|-------|
| Precision | 88.9% |
| Recall | 88.9% |
| Average Precision | 94.0% |
| Training Images | 2,000+ spectrograms |
| Inference Time | ~400ms (cloud) / ~17ms (exported TFLite) |

**Training Categories:**
- 🪓 **Chainsaw** - 781 images
- 🌲 **Nature** - 688 images  
- 🚗 **Vehicle** - 743 images

**Exportable Model:** Compact domain model exports to TFLite for offline Raspberry Pi inference.

### 3. 🗺️ Azure Maps
**Purpose:** Interactive geospatial visualization of the monitoring network

- Real-time node locations with status indicators
- Alert markers with GPS coordinates
- Satellite/terrain view for forest terrain analysis
- Distance calculations for ranger dispatch

### 4. 📊 Azure Cosmos DB (Optional)
**Purpose:** Cloud-based storage for cross-deployment analytics

- Long-term alert history
- Multi-site aggregation
- Trend analysis across forest regions

### 5. ⚡ Azure Functions
**Purpose:** Serverless event processing

- **AlertProcessor:** Triggered on new detections, sends notifications
- **DailyReport:** Generates daily summary emails for stakeholders

### 6. 📱 Azure Communication Services (Optional)
**Purpose:** SMS/Email alerts to rangers

- Immediate SMS when chainsaw detected
- Configurable alert thresholds
- Emergency contact escalation

### 7. 🔐 Azure IoT Hub (Optional)
**Purpose:** Device management at scale

- Remote firmware updates
- Device telemetry and health monitoring
- Scalable to thousands of nodes

---

## 📊 Features

### 🎛️ Dashboard Capabilities

| Feature | Description |
|---------|-------------|
| **Real-time Stats** | Live node count, daily alerts, AI analysis metrics |
| **Interactive Map** | Azure Maps with satellite view, node markers, alert locations |
| **Spectrogram Viewer** | AI analysis results with confidence scores and reasoning |
| **Alert Management** | Response tracking, priority levels, resolution notes |
| **Rate Limit Display** | Azure OpenAI usage tracking (5 req/15 min free tier) |
| **AI Mode Selector** | Switch between GPT-4o, Custom Vision, Auto, or Local modes |

### 🔄 Real-time Updates via WebSocket

```javascript
// Automatic dashboard updates when events occur:
socketio.emit('new_alert', { node: 'GUARDIAN_001', threat: 'chainsaw' });
socketio.emit('node_update', { node: 'GUARDIAN_002', status: 'online' });
socketio.emit('spectrogram_analyzed', { id: 123, result: 'nature' });
socketio.emit('ai_mode_changed', { mode: 'local' });
socketio.emit('sync_completed', { synced: 5, failed: 0 });
```

### 🔐 Authentication & Authorization

| Role | Capabilities |
|------|--------------|
| **Admin** | Full access, user management, system configuration |
| **Ranger** | View dashboard, respond to alerts, view reports |
| **Guest** | Read-only dashboard access |

**Security Features:**
- BCrypt password hashing
- Session-based authentication
- CSRF protection on all forms
- Rate limiting (brute force prevention)
- HTTPOnly, SameSite cookies

### 📈 Reports & Analytics

- **Daily Summary:** Alerts by hour, node uptime, response times
- **Risk Assessment:** Detection patterns, high-activity zones
- **Node Health:** Battery levels, signal strength, uptime metrics

---

## 🔧 Hardware Components

### Guardian Node (Field Sensor) - ~$45 per node

| Component | Model | Purpose | Cost |
|-----------|-------|---------|------|
| **MCU** | Heltec WiFi LoRa 32 V3 | ESP32-S3 + LoRa SX1262 | $18 |
| **Microphone** | INMP441 | I2S MEMS, 16kHz | $3 |
| **GPS** | GY-NEO6MV2 | Location tracking | $5 |
| **Battery** | 2x 18650 (7000mAh) | Power storage | $8 |
| **Solar Panel** | 6V 2W | Continuous charging | $6 |
| **Enclosure** | IP65 Waterproof | Outdoor protection | $5 |

### Raspberry Pi Hub - ~$100

| Component | Model | Purpose | Cost |
|-----------|-------|---------|------|
| **Computer** | Raspberry Pi 5 (4GB) | Hub processing | $60 |
| **LoRa Module** | RFM95W | 915MHz receiver | $12 |
| **Power** | Official Pi 5 PSU | 27W USB-C | $12 |
| **Storage** | 32GB SD Card | OS + database | $8 |
| **Case** | Aluminum heatsink case | Cooling | $8 |

### Total System Cost

| Configuration | Nodes | Hub | Total |
|---------------|-------|-----|-------|
| **Minimum Viable** | 3 × $45 = $135 | $100 | **$235** |
| **Standard Deployment** | 10 × $45 = $450 | $100 | **$550** |
| **Large Scale** | 50 × $45 = $2,250 | $100 | **$2,350** |

*Compare to commercial solutions: $10,000+ for similar coverage*

---

## 🚀 Usage Scenarios

### Scenario 1: 🌲 Normal Forest Monitoring
```
Timeline: 24/7 continuous operation

1. Nodes listen continuously, analyzing 0.5s audio windows
2. Natural sounds (birds, wind, rain) → confidence below threshold
3. No alert generated, node sends heartbeat every 30s
4. Dashboard shows all nodes green, "Forest Healthy" status
5. Battery topped up by solar panel during daylight
```

### Scenario 2: 🪓 Chainsaw Detection (Online)
```
Timeline: Detection to alert in ~10 seconds

1. 00:00.0 - Node #002 detects unusual sound pattern
2. 00:00.5 - Energy threshold exceeded, frequency analysis triggered
3. 00:02.0 - 2-second audio captured, spectrogram generated
4. 00:02.5 - Spectrogram compressed, LoRa transmission starts
5. 00:05.0 - Hub receives complete spectrogram (3-5 packets)
6. 00:05.5 - PNG image generated, sent to Azure GPT-4o Vision
7. 00:08.0 - Azure returns: "CHAINSAW - 94% confidence - CRITICAL"
8. 00:08.1 - Alert created with GPS: 27.6871°N, 85.3240°E
9. 00:08.2 - WebSocket pushes alert to all connected dashboards
10. 00:08.3 - 🔔 Audio notification plays, red alert banner shown
11. Ranger acknowledges alert, dispatches team to coordinates
```

### Scenario 3: 📴 Offline Detection (No Internet)
```
Timeline: Operates normally, syncs when online

1. Hub loses internet connection (power outage at cell tower)
2. Node #001 detects chainsaw, sends spectrogram
3. Hub receives spectrogram successfully
4. Hub uses LOCAL TFLite model for classification
5. Local model: "Chainsaw - 75% confidence" (lower than cloud AI)
6. Alert created, marked as "PENDING_VERIFICATION"
7. Detection queued in SQLite sync database
8. Rangers see alert on local network (dashboard still works)
9. --- 4 hours later, internet restored ---
10. Hub detects connectivity, begins sync process
11. Queued spectrogram sent to Azure GPT-4o Vision
12. Cloud AI confirms: "CHAINSAW - 91% confidence"
13. Alert updated, "VERIFIED" status, higher confidence
14. Dashboard shows sync complete notification
```

### Scenario 4: 🚗 Vehicle Detection
```
Timeline: Medium-priority alert

1. Node #003 detects engine sounds
2. Spectrogram shows low-frequency rumble pattern
3. Azure AI classifies: "VEHICLE - 82% confidence"
4. Threat level: MEDIUM (not immediate threat)
5. Alert created for ranger awareness
6. Ranger notes: "Forestry department truck, authorized"
7. Alert marked resolved with explanation
```

### Scenario 5: 🎬 Demo Mode (Indoor Testing)
```
For demonstrations without real chainsaw:

1. Enable demo mode in firmware: #define DEMO_MODE 1
2. Thresholds adjusted for:
   - Phone/laptop speaker playback (reduced bass)
   - Indoor acoustics (higher noise floor)
   - Lower energy thresholds
3. Play chainsaw audio from YouTube
4. System detects and alerts normally
5. Great for investor pitches and competition demos!
```

### Scenario 6: 🌐 Multi-Site Deployment
```
Forest Guardian scales to multiple forest regions:

┌─────────────────────────────────────────────────────────────┐
│                    NATIONAL FOREST NETWORK                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   🌲 Region A          🌲 Region B          🌲 Region C       │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐      │
│   │  Hub A  │         │  Hub B  │         │  Hub C  │      │
│   │ 15 nodes│         │ 10 nodes│         │ 20 nodes│      │
│   └────┬────┘         └────┬────┘         └────┬────┘      │
│        │                   │                   │            │
│        └───────────────────┼───────────────────┘            │
│                            │                                │
│                            ▼                                │
│                   ┌────────────────┐                        │
│                   │  Azure Cloud   │                        │
│                   │  Cosmos DB     │                        │
│                   │  Aggregation   │                        │
│                   └────────────────┘                        │
│                            │                                │
│                            ▼                                │
│                   ┌────────────────┐                        │
│                   │   National     │                        │
│                   │   Dashboard    │                        │
│                   │   (Unified)    │                        │
│                   └────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
forest-g/
├── �� README.md                 # This file
├── 📄 LICENSE                   # MIT License
│
├── 📁 firmware/                 # ESP32 Arduino Code
│   ├── 📁 guardian_node_spectrogram/
│   │   ├── guardian_node_spectrogram.ino  # Main firmware
│   │   ├── config.h             # Node configuration
│   │   ├── audio_capture.cpp    # I2S microphone handling
│   │   ├── spectrogram.cpp      # FFT & mel spectrogram
│   │   ├── lora_comms.cpp       # LoRa multi-packet protocol
│   │   ├── gps_handler.cpp      # GPS NMEA parsing
│   │   ├── display_handler.cpp  # OLED status display
│   │   └── power_manager.cpp    # Sleep & solar charging
│   ├── 📁 hardware_test/        # Hardware diagnostic
│   └── 📁 mic_test/             # Microphone calibration
│
├── 📁 hub/                      # Raspberry Pi Flask App
│   ├── app.py                   # Main Flask application
│   ├── config.py                # Environment configuration
│   ├── database.py              # SQLite helpers
│   ├── schema.sql               # Database schema
│   ├── auth.py                  # Login & session management
│   ├── admin.py                 # Admin panel routes
│   ├── ai_service.py            # Azure AI integration
│   ├── local_inference.py       # Offline TFLite model
│   ├── lora_receiver.py         # LoRa packet reception
│   ├── lora_rfm95.py            # RFM95W hardware driver
│   ├── network_sync.py          # Offline queue & sync
│   ├── requirements.txt         # Python dependencies
│   ├── 📁 static/
│   │   ├── 📁 css/              # Dashboard styling
│   │   ├── 📁 js/               # Frontend JavaScript
│   │   └── 📁 spectrograms/     # Received images
│   └── 📁 templates/            # Jinja2 HTML templates
│       ├── base.html            # Base layout
│       ├── index.html           # Main dashboard
│       ├── map.html             # Azure Maps integration
│       ├── alerts.html          # Alert management
│       ├── nodes.html           # Node status
│       └── reports.html         # Analytics & reports
│
├── 📁 ml/                       # Machine Learning Pipeline
│   ├── README.md                # ML documentation
│   ├── requirements.txt         # ML dependencies
│   ├── 📁 data/                 # Training datasets
│   │   ├── 📁 chainsaw/         # Chainsaw audio
│   │   ├── 📁 forest/           # Nature sounds
│   │   └── 📁 vehicle/          # Engine sounds
│   ├── 📁 scripts/
│   │   ├── preprocess.py        # Audio → spectrogram
│   │   ├── download_model.py    # Azure CV model export
│   │   └── train.py             # Local training script
│   └── 📁 models/
│       ├── chainsaw_classifier.tflite  # Exported model
│       └── labels.txt           # Class labels
│
├── 📁 azure/                    # Azure Functions
│   ├── host.json                # Functions config
│   ├── requirements.txt         # Dependencies
│   ├── 📁 AlertProcessor/       # Alert webhook
│   └── 📁 DailyReport/          # Daily email summary
│
└── 📁 docs/                     # Documentation
    ├── setup_guide.md           # Complete setup
    ├── hardware_assembly.md     # Wiring diagrams
    ├── AZURE_SERVICES_SETUP.md  # Azure configuration
    ├── AZURE_MAPS_SETUP.md      # Maps integration
    ├── AZURE_CUSTOM_VISION_SETUP.md
    ├── RASPBERRY_PI_HUB_SETUP.md
    └── demo_script.md           # Demo presentation
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (3.13 recommended)
- Arduino IDE 2.x
- Raspberry Pi OS (64-bit)
- Azure account (free tier sufficient for demo)

### 1. Clone Repository

```bash
git clone https://github.com/thapa-ayush/forest-g.git
cd forest-g
```

### 2. Set Up Raspberry Pi Hub

```bash
cd hub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure Azure credentials
cp .env.example .env
nano .env  # Add your keys

# Initialize database
python -c "from database import init_db; init_db()"

# Run
python app.py
```

Access: `http://<pi-ip>:5000` (Default: admin/admin123)

### 3. Flash ESP32 Firmware

```bash
# Arduino IDE → File → Open
# firmware/guardian_node_spectrogram/guardian_node_spectrogram.ino

# Install libraries: RadioLib, TinyGPSPlus, U8g2, ArduinoFFT
# Select board: Heltec WiFi LoRa 32 V3
# Upload
```

### 4. Configure Azure (Optional for basic demo)

See [docs/AZURE_SERVICES_SETUP.md](docs/AZURE_SERVICES_SETUP.md) for:
- Azure OpenAI (GPT-4o Vision)
- Azure Custom Vision
- Azure Maps
- Azure Functions

---

## 🌟 Impact & Scalability

### Environmental Impact

| Metric | With Forest Guardian |
|--------|---------------------|
| Detection Time | **< 1 minute** (vs days with satellites) |
| Coverage Cost | **$45/node** (vs $1000s for cameras) |
| False Positive Rate | **< 5%** with GPT-4o verification |
| Uptime | **99%+** with solar power |

### Scalability Path

```
Phase 1 (Current): Single forest deployment
├── 3-10 nodes
├── 1 Raspberry Pi hub
└── Basic Azure services

Phase 2 (6 months): Regional network
├── 50+ nodes per region
├── Multiple hubs with cloud sync
└── National forest service integration

Phase 3 (12 months): Commercial product
├── 1000+ nodes globally
├── White-label for forest services
└── Integration with satellite data
```

---

## 🏆 Why Forest Guardian Wins

| Criteria | Our Advantage |
|----------|---------------|
| **Innovation** | First real-time acoustic detection with spectrogram AI |
| **Azure Integration** | 7 Azure services working together seamlessly |
| **Affordability** | $235 minimum system vs $10,000+ commercial alternatives |
| **Offline Capability** | Works without internet using local TFLite |
| **Scalability** | From 3 nodes to thousands with same architecture |
| **Real Impact** | Directly addresses UN SDG 15 (Life on Land) |

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Ayush Thapa**
- 🏆 Microsoft Imagine Cup 2026 Participant
- 🐙 GitHub: [@thapa-ayush](https://github.com/thapa-ayush)
- 🌲 Mission: Protecting forests through technology

---

<div align="center">

### 🌲 Protecting Forests, One Sound at a Time 🌲

*Built with ❤️ for Microsoft Imagine Cup 2026*

**[⬆ Back to Top](#-forest-guardian-ai-powered-illegal-logging-detection-system)**

</div>
