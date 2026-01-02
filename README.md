# Forest Guardian: AI-Powered Illegal Logging Detection System

## Overview
Forest Guardian is an end-to-end acoustic monitoring solution designed to detect illegal logging in real time using edge AI and Microsoft Azure cloud services. It combines TinyML-powered ESP32 nodes, LoRa wireless communication, a Raspberry Pi hub, and a secure web dashboard for forest rangers. The system is built for the Microsoft Imagine Cup 2026, with a focus on Azure integration, security, and offline-first operation.

---

## Features
- **Edge AI Detection:** TinyML model on ESP32 detects chainsaw sounds in the forest.
- **LoRa Communication:** Long-range, low-power wireless alerts from nodes to a central hub.
- **Cloud Integration:** Azure IoT Hub, Azure Functions, Cosmos DB, Azure ML, and Azure OpenAI.
- **Ranger Dashboard:** Secure Flask web app for real-time alerts, live map, and AI reports.
- **SMS Notifications:** Optional SMS alerts via Azure Communication Services.
- **Simulation Mode:** Develop and demo without hardware.

---

## Architecture
```
[Guardian Node (ESP32)] --LoRa--> [Raspberry Pi Hub] --Internet--> [Azure Cloud]
      |  |  |                                 |  |  |
      |  |  |                                 |  |  +-- Web Dashboard (Flask)
      |  |  |                                 |  +----- Azure IoT Hub
      |  |  |                                 +-------- Azure OpenAI
      |  |  +-- INMP441 Mic, GPS, OLED, Battery
      +-- Solar/Battery Powered
```

---

## Project Structure
```
forest-guardian/
├── README.md
├── .gitignore
├── ml/                # Machine learning pipeline
├── firmware/          # ESP32 firmware (Arduino)
├── hub/               # Raspberry Pi Flask app
├── azure/             # Azure Functions
└── docs/              # Documentation
```

---

## Quick Start

### 1. Clone the Repository
```sh
git clone https://github.com/your-org/forest-guardian.git
cd forest-guardian
```

### 2. Machine Learning Pipeline
- See [ml/README.md](ml/) for data preparation, training, and model export.

### 3. ESP32 Firmware
- Open `firmware/guardian_node/guardian_node.ino` in Arduino IDE.
- Install required libraries (see code comments).
- Flash to Heltec WiFi LoRa 32 V3.

### 4. Raspberry Pi Hub
- Install Python 3.11+ and dependencies:
  ```sh
  cd hub
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  cp .env.example .env
  # Edit .env with your Azure and app credentials
  python app.py
  ```
- Access dashboard at http://localhost:5000

### 5. Azure Functions
- See [azure/README.md](azure/) for deployment instructions.

---

## Hardware
- **Guardian Node:** Heltec WiFi LoRa 32 V3, INMP441 mic, GY-NEO6MV2 GPS, 2x 18650 Li-ion, solar panel
- **Hub:** Raspberry Pi 5, RFM95W LoRa module
- **Wiring diagrams:** See [docs/hardware_assembly.md](docs/hardware_assembly.md)

---

## Azure Services Used
- **Azure IoT Hub:** Device telemetry and management
- **Azure Functions:** Serverless alert processing
- **Azure Cosmos DB:** NoSQL database for alerts
- **Azure Machine Learning:** Model training and deployment
- **Azure OpenAI Service:** AI analysis and reporting
- **Azure Communication Services:** SMS notifications (optional)

---

## Security
- All passwords hashed (bcrypt/Werkzeug)
- Secure session cookies
- Input validation and XSS protection
- No secrets in git (.env files used)
- HTTPS recommended in production

---

## Documentation
- [docs/setup_guide.md](docs/setup_guide.md): Full setup instructions
- [docs/azure_setup.md](docs/azure_setup.md): Azure resource creation
- [docs/hardware_assembly.md](docs/hardware_assembly.md): Hardware build
- [docs/demo_script.md](docs/demo_script.md): 3-minute demo
- [docs/api_reference.md](docs/api_reference.md): API endpoints

---

## License
MIT License. See [LICENSE](LICENSE) for details.

---

## Authors
- Team Forest Guardian, Microsoft Imagine Cup 2026

---

## Contact
For support or questions, open an issue or contact: forestguardian@yourdomain.com
