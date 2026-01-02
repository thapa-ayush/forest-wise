# Forest Guardian - Setup Guide

## Prerequisites
- Python 3.11+
- Arduino IDE 2.x
- Raspberry Pi OS (for hub)
- Azure account (free tier)
- Git

---

## 1. Clone the Repository
```sh
git clone https://github.com/your-org/forest-guardian.git
cd forest-guardian
```

---

## 2. Machine Learning Pipeline

### Install dependencies
```sh
cd ml
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Prepare data
- Place chainsaw audio samples in `data/chainsaw/`
- Place forest ambient sounds in `data/forest/`
- Place similar (non-chainsaw) sounds in `data/hard_negatives/`
- Or run `python scripts/download_data.py` to fetch from public sources

### Preprocess audio
```sh
python scripts/preprocess.py
```

### Train model
```sh
python scripts/train.py
```

### Convert to TFLite and C header
```sh
python scripts/convert_tflite.py
```
- Output: `models/chainsaw_cnn_int8.tflite`, `firmware/guardian_node/chainsaw_model.h`

---

## 3. ESP32 Firmware

### Install Arduino IDE libraries
- RadioLib
- TinyGPSPlus
- Adafruit SSD1306
- Adafruit GFX
- TensorFlowLite_ESP32

### Open project
- Open `firmware/guardian_node/guardian_node.ino` in Arduino IDE

### Configure
- Edit `config.h` to set node ID, pin assignments, LoRa frequency

### Upload
- Select board: Heltec WiFi LoRa 32 V3
- Select port
- Upload

---

## 4. Raspberry Pi Hub

### Install system dependencies
```sh
sudo apt update
sudo apt install python3-pip python3-venv libffi-dev libssl-dev
```

### Setup Python environment
```sh
cd hub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure environment
```sh
cp .env.example .env
# Edit .env with your Azure credentials
```

### Initialize database
```sh
python -c "from database import init_db; init_db()"
```

### Run
```sh
python app.py
```

### Access dashboard
- Open http://localhost:5000 in your browser
- Default login: admin / admin123

---

## 5. Azure Setup
See [azure_setup.md](azure_setup.md) for Azure resource creation.

---

## 6. Hardware Assembly
See [hardware_assembly.md](hardware_assembly.md) for wiring diagrams.

---

## 7. Demo Script
See [demo_script.md](demo_script.md) for Imagine Cup demo instructions.

---

## Troubleshooting
- **No audio capture:** Check I2S wiring and pin config
- **GPS not found:** Ensure GPS has clear sky view
- **LoRa not working:** Check frequency and antenna
- **Azure errors:** Verify connection strings in .env

---

## License
MIT
