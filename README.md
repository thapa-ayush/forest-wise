# 🌲 Forest Guardian: AI-Powered Illegal Logging Detection System

<div align="center">

![Forest Guardian](https://img.shields.io/badge/Forest-Guardian-228B22?style=for-the-badge&logo=tree&logoColor=white)
![Azure](https://img.shields.io/badge/Microsoft-Azure-0089D6?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-S3-E7352C?style=for-the-badge&logo=espressif&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Protecting forests through real-time acoustic monitoring and AI-powered threat detection**

*Developed by Ayush Thapa for Microsoft Imagine Cup 2026*

[Features](#-features) • [Architecture](#-system-architecture) • [Hardware](#-hardware-components) • [Setup](#-quick-start) • [Scenarios](#-usage-scenarios) • [Azure Services](#-azure-integration)

</div>

---

## 📋 Overview

Forest Guardian is an end-to-end acoustic monitoring solution that detects illegal logging activity in real-time. The system combines:

- **Edge Devices (ESP32-S3)**: Solar-powered sensor nodes with microphones that listen for chainsaw sounds
- **LoRa Wireless Network**: Long-range, low-power communication (up to 15km line-of-sight)
- **Raspberry Pi Hub**: Central receiver that processes alerts and generates spectrograms
- **Azure AI Services**: GPT-4o Vision and Custom Vision for intelligent sound classification
- **Web Dashboard**: Real-time monitoring interface for forest rangers

The system is designed for **remote deployment** with:
- ✅ Offline-first operation (works without internet)
- ✅ Solar-powered nodes (months of autonomous operation)
- ✅ Visual evidence (spectrograms) for each detection
- ✅ Multi-tier AI analysis (local → Custom Vision → GPT-4o)

---

## 🎯 Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Real-time Detection** | Audio analysis every 0.5 seconds, instant alert transmission |
| **Visual Spectrograms** | 32x32 mel-frequency spectrograms sent to hub for AI analysis |
| **Multi-tier AI** | Local TFLite → Azure Custom Vision → GPT-4o Vision fallback chain |
| **Offline Queue** | Detections stored locally when offline, synced when connected |
| **Live Dashboard** | WebSocket-powered real-time updates, interactive map, alert management |
| **Rate Limiting** | Smart API usage management for Azure free tier (5 req/15 min) |

### AI Analysis Modes

1. **GPT-4o Vision** (Default): Highest accuracy (~95%), detailed reasoning, visual feature detection
2. **Custom Vision**: Fast classification, lower latency, trained on forest sounds
3. **Auto Mode**: Custom Vision for speed, GPT-4o for threat verification
4. **Local TFLite**: Fully offline mode using on-device ML model

### Dashboard Features

- 📊 Real-time statistics (nodes online, alerts today, AI analysis count)
- 🗺️ Interactive map with node locations and alert markers
- 📈 Spectrogram viewer with AI analysis results
- 🔔 Unresponded alert notifications with response tracking
- 👥 User management with role-based access (Admin, Ranger)
- 📱 Responsive design for mobile field use

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FOREST (Remote Area)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│   │  GUARDIAN    │    │  GUARDIAN    │    │  GUARDIAN    │                  │
│   │  NODE #001   │    │  NODE #002   │    │  NODE #003   │                  │
│   │              │    │              │    │              │                  │
│   │ ESP32-S3     │    │ ESP32-S3     │    │ ESP32-S3     │                  │
│   │ INMP441 Mic  │    │ INMP441 Mic  │    │ INMP441 Mic  │                  │
│   │ GPS Module   │    │ GPS Module   │    │ GPS Module   │                  │
│   │ Solar Panel  │    │ Solar Panel  │    │ Solar Panel  │                  │
│   │ LoRa SX1262  │    │ LoRa SX1262  │    │ LoRa SX1262  │                  │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│          │                   │                   │                           │
│          │    LoRa 915MHz    │    (Up to 15km)   │                           │
│          └───────────────────┼───────────────────┘                           │
│                              │                                               │
│                              ▼                                               │
│                    ┌─────────────────┐                                       │
│                    │   RASPBERRY PI  │                                       │
│                    │      HUB        │                                       │
│                    │                 │                                       │
│                    │ • RFM95W LoRa   │                                       │
│                    │ • Flask Server  │                                       │
│                    │ • SQLite DB     │                                       │
│                    │ • Local TFLite  │                                       │
│                    └────────┬────────┘                                       │
│                             │                                                │
└─────────────────────────────┼────────────────────────────────────────────────┘
                              │
                              │ Internet (WiFi/4G)
                              │ (When Available)
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AZURE CLOUD                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────────────┐    ┌────────────────┐    ┌────────────────┐            │
│   │  Azure OpenAI  │    │ Custom Vision  │    │  Cosmos DB     │            │
│   │   GPT-4o       │    │                │    │  (Optional)    │            │
│   │   Vision       │    │  Spectrogram   │    │                │            │
│   │                │    │  Classifier    │    │  Alert Storage │            │
│   └────────────────┘    └────────────────┘    └────────────────┘            │
│                                                                              │
│   ┌────────────────┐    ┌────────────────┐                                  │
│   │ Azure IoT Hub  │    │   Azure        │                                  │
│   │  (Optional)    │    │   Functions    │                                  │
│   │                │    │                │                                  │
│   │ Device Mgmt    │    │ Alert Trigger  │                                  │
│   └────────────────┘    └────────────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Sound Detection**: Node microphone captures audio continuously
2. **Anomaly Detection**: On-device algorithm detects unusual sounds (energy + frequency analysis)
3. **Spectrogram Generation**: 32x32 mel-frequency spectrogram created from audio
4. **LoRa Transmission**: Compressed spectrogram sent to hub via multi-packet protocol
5. **AI Analysis**: Hub sends spectrogram to Azure AI for classification
6. **Alert Creation**: If threat detected, alert created with GPS coordinates
7. **Dashboard Update**: WebSocket pushes real-time updates to all connected rangers
8. **Response Tracking**: Rangers can mark alerts as responded with notes

---

## 🔧 Hardware Components

### Guardian Node (Sensor)

| Component | Model | Purpose |
|-----------|-------|---------|
| **MCU** | Heltec WiFi LoRa 32 V3 | ESP32-S3 with built-in LoRa SX1262 |
| **Microphone** | INMP441 | I2S MEMS mic, 16kHz sample rate |
| **GPS** | GY-NEO6MV2 | Location tracking |
| **Display** | SSD1306 0.96" OLED | Status display (built into Heltec) |
| **Battery** | 2x 18650 Li-ion | 7000mAh total capacity |
| **Solar Panel** | 6V 2W | Continuous charging |
| **Enclosure** | IP65 Waterproof | Outdoor protection |

**Pin Configuration (ESP32-S3):**
```
I2S Microphone (INMP441):
  - SCK (BCK)  → GPIO 7
  - WS (LRCK)  → GPIO 6
  - SD (DOUT)  → GPIO 5

GPS Module (GY-NEO6MV2):
  - TX → GPIO 19 (ESP32 RX)
  - RX → GPIO 20 (ESP32 TX)

LoRa SX1262 (Built-in):
  - NSS  → GPIO 8
  - RST  → GPIO 12
  - BUSY → GPIO 13
  - DIO1 → GPIO 14
```

### Raspberry Pi Hub

| Component | Model | Purpose |
|-----------|-------|---------|
| **Computer** | Raspberry Pi 5 (4GB) | Hub processing |
| **LoRa Module** | RFM95W (SX1276) | 915MHz LoRa receiver |
| **Power** | Official Pi 5 PSU | 27W USB-C power supply |
| **Storage** | 32GB+ SD Card | OS and database storage |

**RFM95W Pin Configuration:**
```
RFM95W → Raspberry Pi 5:
  - VCC  → 3.3V
  - GND  → GND
  - MISO → GPIO 9 (SPI0 MISO)
  - MOSI → GPIO 10 (SPI0 MOSI)
  - SCK  → GPIO 11 (SPI0 CLK)
  - NSS  → GPIO 8 (CE0)
  - RST  → GPIO 25
  - DIO0 → GPIO 24
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Arduino IDE 2.x (for ESP32 firmware)
- Raspberry Pi OS (64-bit recommended)
- Azure account (free tier works)

### 1. Clone the Repository

```bash
git clone https://github.com/thapa-ayush/forest-g.git
cd forest-g
```

### 2. Set Up Raspberry Pi Hub

```bash
cd hub

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your Azure credentials

# Initialize database
python -c "from database import init_db; init_db()"

# Run the hub
python app.py
```

Access dashboard at `http://<pi-ip>:5000`

**Default Login:**
- Username: `admin`
- Password: `admin123`

### 3. Flash ESP32 Firmware

```bash
# Open Arduino IDE
# File → Open → firmware/guardian_node_spectrogram/guardian_node_spectrogram.ino

# Install required libraries (Tools → Manage Libraries):
# - RadioLib
# - TinyGPSPlus  
# - U8g2
# - ArduinoFFT
# - ArduinoJson

# Select board: Heltec WiFi LoRa 32 V3
# Upload
```

Edit `config.h` to set unique NODE_ID for each device:
```cpp
#define NODE_ID "GUARDIAN_001"  // Change for each node
```

### 4. Configure Azure Services

Create `.env` file in `hub/` directory:

```env
# Flask
FLASK_SECRET_KEY=your-secret-key-here

# Azure OpenAI (GPT-4o Vision)
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Azure Custom Vision (Optional - for faster classification)
AZURE_CUSTOM_VISION_ENDPOINT=https://your-cv.cognitiveservices.azure.com/
AZURE_CUSTOM_VISION_KEY=your-key
AZURE_CUSTOM_VISION_PROJECT_ID=project-guid
AZURE_CUSTOM_VISION_ITERATION=production

# Default AI Mode: 'gpt4o', 'custom_vision', 'auto', or 'local'
DEFAULT_AI_MODE=gpt4o
```

---

## 📱 Usage Scenarios

### Scenario 1: Normal Forest Monitoring

```
1. Nodes continuously listen for sounds
2. Natural sounds (birds, wind, rain) → LOW confidence → No alert
3. Dashboard shows green status, nodes online
4. Heartbeat every 30 seconds updates node status
```

### Scenario 2: Chainsaw Detection (Full Internet)

```
1. Node detects unusual sound pattern (high energy, periodic frequency)
2. Node generates 32x32 mel spectrogram
3. Spectrogram transmitted to hub via LoRa (~3-5 packets)
4. Hub receives and reconstructs spectrogram image
5. Hub sends to Azure GPT-4o Vision for analysis
6. GPT-4o returns: "CHAINSAW - 92% confidence - CRITICAL threat"
7. Alert created with GPS coordinates
8. Dashboard shows red alert, notification sound plays
9. Ranger responds, marks alert as handled
```

### Scenario 3: Offline Detection (No Internet)

```
1. Node detects chainsaw, sends spectrogram to hub
2. Hub has no internet connection
3. Hub uses local TFLite model for classification
4. Local model: "Chainsaw - 75% confidence"
5. Alert created, queued for cloud verification
6. When internet returns, hub syncs with Azure
7. GPT-4o re-analyzes: "CHAINSAW - 94% confidence"
8. Alert updated with verified classification
```

### Scenario 4: Demo Mode (Indoor Testing)

```
# In firmware/guardian_node_spectrogram/config.h:
#define DEMO_MODE 1  // Enable demo mode

Demo mode adjusts thresholds for:
- Phone/laptop speaker playback (no bass frequencies)
- Indoor environment (higher noise floor)
- Lower detection thresholds
```

### Scenario 5: Multi-Node Deployment

```
1. Deploy 5 nodes in 10km² area
2. Each node covers ~2km radius
3. Chainsaw detected by Node #003
4. Alert shows exact GPS location
5. Rangers check map for nearest access road
6. Response time: < 30 minutes from detection
```

---

## ☁️ Azure Integration

### Azure OpenAI (GPT-4o Vision)

Primary AI service for spectrogram analysis. Uses advanced vision capabilities to:
- Identify audio patterns in spectrogram images
- Provide detailed reasoning for classifications
- Recommend specific actions for rangers

**Rate Limits (Free Tier):**
- 5 requests per 15 minutes
- System tracks usage and shows remaining quota in dashboard

**Prompt Engineering:**
The system uses a carefully crafted prompt that teaches GPT-4o to:
- Interpret mel-frequency spectrograms
- Distinguish chainsaw patterns (horizontal bands, periodic engine RPM)
- Identify vehicle sounds (low-frequency rumble)
- Recognize natural forest sounds (bird calls, wind, rain)

### Azure Custom Vision

Optional faster classification service:
- Train with your own spectrogram dataset
- Typical inference: <500ms vs 2-3s for GPT-4o
- Use in "auto" mode: Custom Vision first, GPT-4o for verification

### Azure Cosmos DB (Optional)

Cloud storage for:
- Historical alert data
- Cross-deployment aggregation
- Long-term analytics

### Azure Functions (Optional)

Serverless processing for:
- Alert webhooks
- SMS notifications via Azure Communication Services
- Daily summary reports

---

## 📁 Project Structure

```
forest-g/
├── README.md                 # This file
├── LICENSE                   # MIT License
│
├── firmware/                 # ESP32 Arduino code
│   ├── guardian_node_spectrogram/
│   │   ├── guardian_node_spectrogram.ino  # Main firmware
│   │   ├── config.h          # Node configuration
│   │   ├── audio_capture.cpp # I2S microphone handling
│   │   ├── spectrogram.cpp   # FFT and mel spectrogram generation
│   │   ├── lora_comms.cpp    # LoRa transmission protocol
│   │   ├── gps_handler.cpp   # GPS parsing
│   │   └── display_handler.cpp # OLED display
│   ├── hardware_test/        # Hardware diagnostic firmware
│   └── mic_test/             # Microphone test firmware
│
├── hub/                      # Raspberry Pi Flask application
│   ├── app.py                # Main Flask application
│   ├── config.py             # Configuration from .env
│   ├── database.py           # SQLite database helpers
│   ├── schema.sql            # Database schema
│   ├── auth.py               # Authentication & login
│   ├── admin.py              # Admin panel routes
│   ├── ai_service.py         # Azure AI integration
│   ├── lora_receiver.py      # LoRa packet reception
│   ├── lora_rfm95.py         # RFM95W hardware driver
│   ├── network_sync.py       # Offline queue and sync
│   ├── local_inference.py    # Local TFLite model
│   ├── requirements.txt      # Python dependencies
│   ├── static/
│   │   ├── css/style.css     # Dashboard styling
│   │   ├── js/app.js         # Frontend JavaScript
│   │   └── spectrograms/     # Received spectrogram images
│   └── templates/            # Jinja2 HTML templates
│       ├── base.html         # Base template
│       ├── index.html        # Main dashboard
│       ├── map.html          # Interactive map view
│       ├── alerts.html       # Alert management
│       ├── nodes.html        # Node status
│       └── reports.html      # Reports and analytics
│
├── ml/                       # Machine learning pipeline
│   ├── README.md             # ML documentation
│   ├── requirements.txt      # ML dependencies
│   ├── data/                 # Training data
│   │   ├── chainsaw/         # Chainsaw audio samples
│   │   ├── forest/           # Natural forest sounds
│   │   └── hard_negatives/   # Similar non-chainsaw sounds
│   ├── scripts/
│   │   ├── preprocess.py     # Audio to spectrogram conversion
│   │   ├── train.py          # Local model training
│   │   ├── azure_ml_train.py # Azure ML training
│   │   └── convert_tflite.py # Export to TFLite
│   └── models/               # Trained model files
│
├── azure/                    # Azure Functions
│   ├── host.json             # Azure Functions config
│   ├── requirements.txt      # Function dependencies
│   ├── AlertProcessor/       # Alert processing function
│   └── DailyReport/          # Daily summary function
│
├── docs/                     # Documentation
│   ├── setup_guide.md        # Detailed setup instructions
│   ├── hardware_assembly.md  # Hardware wiring guide
│   ├── azure_setup.md        # Azure service configuration
│   └── CONFIGURATION_GUIDE.md # Configuration reference
│
└── ei-forest-guardian-chainsaw-arduino-1.0.1/
    └── forest-guardian-chainsaw_inferencing/  # Edge Impulse library (legacy)
```

---

## 🔒 Security

- **Authentication**: Session-based login with bcrypt password hashing
- **CSRF Protection**: Flask-WTF CSRF tokens on all forms
- **Input Validation**: All user inputs sanitized
- **Secrets Management**: Environment variables via `.env` (never committed)
- **Rate Limiting**: Flask-Limiter prevents brute force attacks
- **Session Security**: HTTPOnly, SameSite cookies

---

## 🐛 Troubleshooting

### Node Not Sending Data

```bash
# Check serial monitor in Arduino IDE
# Should see: "[TX] Sent heartbeat" every 30 seconds

# Verify LoRa settings match hub:
# - Frequency: 915.0 MHz
# - Spreading Factor: 10
# - Bandwidth: 125 kHz
# - Sync Word: 0x12 (node) → 0x14 (hub converts)
```

### Hub Not Receiving

```bash
# Check LoRa status
curl http://localhost:5000/api/lora/status

# Should return: {"status": "running", "stats": {...}}

# Check SPI is enabled on Pi:
sudo raspi-config
# Interface Options → SPI → Enable
```

### Azure AI Not Working

```bash
# Check API connectivity
curl http://localhost:5000/api/ai/status

# Verify credentials in .env
# Check Azure portal for API quotas

# Rate limit status visible in dashboard
# 5 requests per 15 minutes on free tier
```

### Database Issues

```bash
# Reset database
cd hub
rm forest_guardian.db
python -c "from database import init_db; init_db()"
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Ayush Thapa**

- Microsoft Imagine Cup 2026 Participant
- GitHub: [@thapa-ayush](https://github.com/thapa-ayush)

---

## 🙏 Acknowledgments

- Microsoft Azure for cloud AI services
- Edge Impulse for TinyML tooling
- Heltec for excellent ESP32 LoRa modules
- The open-source community for libraries and tools

---

<div align="center">

**🌲 Protecting forests, one detection at a time 🌲**

</div>
