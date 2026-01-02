# Forest Guardian Firmware Installation Guide

## Arduino IDE Setup for Heltec WiFi LoRa 32 V3

This guide explains how to install the Forest Guardian firmware on the Heltec WiFi LoRa 32 V3 board using Arduino IDE.

---

## Prerequisites

### Hardware Required
- **Heltec WiFi LoRa 32 V3** (ESP32-S3 + SX1262)
- **INMP441 I2S MEMS Microphone**
- **GY-NEO6MV2 GPS Module**
- **USB-C cable** for programming
- **3.7V LiPo battery** (optional, for portable operation)
- **915MHz LoRa antenna** (REQUIRED - never power on without antenna!)

### Software Required
- Arduino IDE 2.x (recommended) or 1.8.x
- USB drivers for ESP32-S3 (usually auto-installed)

---

## Step 1: Install Arduino IDE

1. Download Arduino IDE from: https://www.arduino.cc/en/software
2. Install for your operating system
3. Launch Arduino IDE

---

## Step 2: Add ESP32 Board Support

1. Open Arduino IDE
2. Go to **File → Preferences** (or **Arduino IDE → Settings** on Mac)
3. In "Additional Boards Manager URLs", add:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
4. Click **OK**
5. Go to **Tools → Board → Boards Manager**
6. Search for **"esp32"**
7. Install **"esp32 by Espressif Systems"** (version 2.0.14 or newer)
8. Wait for installation to complete

---

## Step 3: Install Required Libraries

Go to **Tools → Manage Libraries** and install:

| Library | Version | Purpose |
|---------|---------|---------|
| **RadioLib** | 6.x | SX1262 LoRa communication |
| **TinyGPSPlus** | 1.0.3+ | GPS NMEA parsing |
| **U8g2** | 2.34+ | OLED display driver |
| **ArduinoJson** | 7.x | JSON message formatting |
| **arduinoFFT** | 2.0+ | FFT spectral analysis for Edge AI |

> **Note**: The firmware uses FFT-based spectral analysis for Edge AI chainsaw detection. This analyzes frequency bands characteristic of chainsaw sounds (engine drone, chain cutting noise). For cloud verification, the system integrates with Azure Custom Vision.

### Library Installation Steps:
1. **Tools → Manage Libraries**
2. Search for each library name
3. Click **Install**
4. Repeat for all libraries

---

## Step 4: Configure Board Settings

1. Connect Heltec WiFi LoRa 32 V3 via USB-C
2. Go to **Tools** menu and set:

| Setting | Value |
|---------|-------|
| **Board** | ESP32S3 Dev Module |
| **Port** | COMx (Windows) or /dev/cu.xxx (Mac) |
| **USB CDC On Boot** | Enabled |
| **USB Mode** | Hardware CDC and JTAG |
| **Upload Speed** | 921600 |
| **Flash Mode** | QIO 80MHz |
| **Flash Size** | 8MB (64Mb) |
| **Partition Scheme** | Huge APP (3MB No OTA/1MB SPIFFS) |
| **PSRAM** | OPI PSRAM |
| **Core Debug Level** | Info (optional, for debugging) |

---

## Step 5: Hardware Wiring

### INMP441 Microphone Connection
| INMP441 | Heltec V3 |
|---------|-----------|--------------|
| VDD | 3.3V | Pin 3-4 (left) |
| GND | GND | Pin 1 (left) |
| SCK | **GPIO 7** (Clock) | Pin 18 (left, top) |
| WS | **GPIO 6** (Word Select) | Pin 17 (left) |
| SD | **GPIO 5** (Data) | Pin 16 (left) |
| L/R | **GND** (left channel) | Pin 1 (left) |

> **Note**: L/R to GND selects left channel. If mic shows 0%, try connecting L/R to 3.3V instead.

### GY-NEO6MV2 GPS Connection
| GPS | Heltec V3 | Physical Pin |
|-----|-----------|--------------|
| VCC | 3.3V | Pin 3 (right) |
| GND | GND | Pin 1 (right) |
| TX | **GPIO 19** (ESP32 RX) | Pin 18 (right, top) |
| RX | **GPIO 20** (ESP32 TX) | Pin 17 (right) |

> **Note**: GPS TX connects to ESP32 RX (GPIO19). GPS RX connects to ESP32 TX (GPIO20).

### Important Notes:
- ⚠️ **ALWAYS attach 915MHz antenna before powering on!**
- The Heltec V3 OLED display is built-in (no wiring needed)
- The SX1262 LoRa is built-in (no wiring needed)

---

## Step 6: Upload Firmware

### Method 1: Arduino IDE Upload

1. Open the main sketch:
   ```
   File → Open → forest_guardian/firmware/guardian_node/guardian_node.ino
   ```

2. Verify the sketch compiles:
   ```
   Sketch → Verify/Compile (Ctrl+R)
   ```
   
3. Put board in upload mode (if needed):
   - Hold **BOOT** button
   - Press and release **RST** button
   - Release **BOOT** button

4. Upload the firmware:
   ```
   Sketch → Upload (Ctrl+U)
   ```

5. Wait for upload to complete (should see "Done uploading")

6. Press **RST** button to start the firmware

### Method 2: Command Line Upload (Advanced)

If you have `arduino-cli` installed:

```bash
# Compile
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc,FlashSize=8M,PartitionScheme=huge_app,PSRAM=opi ./firmware/guardian_node

# Upload
arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32s3 ./firmware/guardian_node
```

---

## Step 7: Verify Installation

1. Open **Serial Monitor**: **Tools → Serial Monitor**
2. Set baud rate to **115200**
3. Press **RST** on board
4. You should see:

```
========================================
    FOREST GUARDIAN - Node Startup
========================================
Node ID: FGNODE001
Firmware: v1.0.0

[INIT] Display...
[INIT] Power manager...
[INIT] Battery: 85%
[INIT] Audio capture...
[Audio] I2S initialized successfully!
[INIT] GPS...
[GPS] GPS module responding!
[INIT] ML inference engine...
[ML] TFLite Micro initialized successfully!
[INIT] LoRa transceiver...
[LoRa] SX1262 initialized successfully!

========================================
       Initialization Complete!
========================================
```

5. The OLED should show:
   - Boot screen with "FOREST GUARDIAN"
   - Progress bars during initialization
   - "LISTENING" status when ready

---

## Troubleshooting

### "No port selected" or board not detected
- Try different USB cable (some are charge-only)
- Install CP210x or CH340 USB drivers
- Try different USB port
- On Windows: Check Device Manager for COM port

### "Upload failed" or timeout
1. Put board in boot mode:
   - Hold **BOOT** button
   - Press **RST** button
   - Release both
2. Try upload again immediately

### "Fatal error: xxx.h: No such file" 
- Missing library - install via Library Manager
- Check library versions match requirements

### OLED not working
- Check that `OLED_RST` is correctly defined in config.h (GPIO 21)
- The built-in display uses Wire library - conflicts with custom I2C

### LoRa not transmitting
- **CRITICAL**: Ensure antenna is connected!
- Check LoRa frequency matches your region (915 MHz for Canada/US)
- Verify RadioLib library is version 6.x+

### Audio not capturing
- Check INMP441 wiring (especially L/R to GND)
- Verify I2S pins in config.h match your wiring
- Test with simple I2S example sketch first

### GPS no fix
- Move outdoors with clear sky view
- GPS cold start can take 1-5 minutes
- Check GPS TX→ESP32 RX wiring

---

## Configuration

Edit `config.h` to customize:

```cpp
// Node identification
#define NODE_ID "FGNODE001"        // Unique node identifier

// LoRa settings (915 MHz for Canada/US)
#define LORA_FREQ 915.0            // MHz
#define LORA_TX_POWER 17           // dBm (max 20)

// Detection settings
#define DETECTION_THRESHOLD 0.75    // Confidence threshold (0.0-1.0)
#define HEARTBEAT_INTERVAL_MS 300000  // 5 minutes
#define LORA_COOLDOWN_MS 30000      // 30 seconds between alerts
```

---

## Firmware Files Structure

```
firmware/guardian_node/
├── guardian_node.ino      # Main sketch
├── config.h               # Configuration constants
├── chainsaw_model.h       # TFLite model (generated)
├── audio_capture.cpp/h    # INMP441 microphone handler
├── display_handler.cpp/h  # OLED display handler
├── gps_handler.cpp/h      # GPS module handler
├── lora_comms.cpp/h       # LoRa communication
├── ml_inference.cpp/h     # TinyML inference engine
└── power_manager.cpp/h    # Battery management
```

---

## Memory Usage

After compilation, you should see approximately:
- **Flash**: ~1.5 MB used (19% of 8MB)
- **RAM**: ~180 KB used (55% of 327KB)

If you get "Sketch too big" error:
1. Use "Huge APP" partition scheme
2. Reduce debug output
3. Optimize TensorFlow Lite arena size

---

## Next Steps

1. **Test detection**: Make chainsaw sounds near microphone
2. **Set up hub**: Deploy Raspberry Pi hub to receive LoRa messages
3. **Deploy outdoors**: Weatherproof enclosure recommended
4. **Monitor**: Use web dashboard to track alerts

---

## Support

For issues or questions:
- Check serial output for error messages
- Review config.h pin assignments
- Test individual components separately
- See project documentation in `/docs/`

---

*Forest Guardian - Protecting forests with AI*
