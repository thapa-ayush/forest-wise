# Forest Guardian - Configuration Guide

## Quick Start

The Forest Guardian firmware supports two operational modes:

| Mode | Use Case | Sensitivity |
|------|----------|-------------|
| **Demo Mode** | Imagine Cup presentations, testing with speakers | High (works with phone/laptop) |
| **Production Mode** | Real forest deployment | Optimized for actual chainsaws |

---

## How to Switch Modes

### Step 1: Open Configuration File

Open `firmware/guardian_node/config.h` in Arduino IDE or VS Code.

### Step 2: Find the DEMO_MODE Setting

Look for this line (around line 80):

```cpp
#define DEMO_MODE 1
```

### Step 3: Change the Value

**For Demo/Testing (Imagine Cup):**
```cpp
#define DEMO_MODE 1
```

**For Real Deployment:**
```cpp
#define DEMO_MODE 0
```

### Step 4: Compile and Upload

1. Open Arduino IDE
2. Press `Ctrl+R` to compile
3. Press `Ctrl+U` to upload
4. Open Serial Monitor (`Ctrl+Shift+M`) at 115200 baud

---

## Mode Comparison

### Demo Mode (`DEMO_MODE 1`)

```cpp
DETECTION_THRESHOLD   = 0.18f   // 18% smoothed confidence
DETECTION_RAW_MIN     = 0.15f   // 15% raw detection counts
CONSECUTIVE_REQUIRED  = 2       // 2 consecutive hits needed
LORA_COOLDOWN_MS      = 5000    // 5 seconds between alerts
```

**Best for:**
- Imagine Cup video recording
- Testing with phone speakers
- Testing with laptop speakers
- Testing with Bluetooth speakers
- Quick demonstrations

**Characteristics:**
- More sensitive to weak signals
- Faster alert response
- May have occasional false positives in noisy environments

---

### Production Mode (`DEMO_MODE 0`)

```cpp
DETECTION_THRESHOLD   = 0.35f   // 35% smoothed confidence
DETECTION_RAW_MIN     = 0.25f   // 25% raw detection counts
CONSECUTIVE_REQUIRED  = 3       // 3 consecutive hits needed
LORA_COOLDOWN_MS      = 30000   // 30 seconds between alerts
```

**Best for:**
- Real forest deployment
- Actual chainsaw detection
- Long-term monitoring
- Battery conservation

**Characteristics:**
- Optimized for real chainsaw sounds (50-90% confidence)
- Fewer false positives
- More robust detection requiring sustained sounds
- Longer cooldown to prevent alert spam

---

## Other Configurable Settings

### Audio Settings (config.h)

```cpp
#define SAMPLE_RATE 16000        // 16kHz - matches Edge Impulse model
#define AUDIO_BUFFER_SIZE 17000  // Buffer size for 1+ second of audio
#define AUDIO_CHUNK_SIZE 16000   // 1 second chunks for inference
```

> ⚠️ **Do not change** these unless you retrain the Edge Impulse model

### LoRa Settings (config.h)

```cpp
#define LORA_BAND 915E6          // Frequency: 915MHz (US) or 868E6 (EU)
#define LORA_SPREADING 7         // Spreading factor (7-12)
#define LORA_BANDWIDTH 125E3     // Bandwidth
#define LORA_TX_POWER 20         // Transmit power (dBm)
```

### Timing Settings (config.h)

```cpp
#define HEARTBEAT_INTERVAL_MS 300000  // 5 minute heartbeat to hub
#define DEEP_SLEEP_DURATION 60        // Sleep duration when battery critical
#define LOW_BATTERY_THRESHOLD 20      // Battery % for low power warning
```

---

## Pin Configuration

### Microphone (INMP441)

```cpp
#define I2S_SCK 7    // Bit clock
#define I2S_WS  6    // Word select (left/right)
#define I2S_SD  5    // Data
```

### GPS (GY-NEO6MV2)

```cpp
#define GPS_RX 19    // GPS TX -> ESP32 RX
#define GPS_TX 20    // GPS RX -> ESP32 TX
```

### Other

```cpp
#define LED_PIN 35   // Built-in LED for alerts
```

---

## Recommended Settings by Scenario

### Scenario 1: Recording Imagine Cup Demo Video

```cpp
#define DEMO_MODE 1
```
- Use laptop speakers or Bluetooth speaker
- Play chainsaw videos from YouTube at max volume
- Position device 10-50cm from speaker

### Scenario 2: Live Demo at Competition

```cpp
#define DEMO_MODE 1
```
- Prepare chainsaw audio on phone/tablet
- Test beforehand to find optimal volume/distance
- Have backup audio ready

### Scenario 3: Field Testing with Real Chainsaw

```cpp
#define DEMO_MODE 0
```
- Ensure safety protocols
- Test at various distances (10m, 50m, 100m)
- Document detection range

### Scenario 4: Long-term Forest Deployment

```cpp
#define DEMO_MODE 0
```
- Use weatherproof enclosure
- Connect solar panel for charging
- Configure hub for alert forwarding

---

## Troubleshooting Configuration Issues

### Detection Too Sensitive (False Positives)

Increase thresholds:
```cpp
#define DETECTION_THRESHOLD 0.25f  // Raise from 0.18
#define DETECTION_RAW_MIN 0.20f    // Raise from 0.15
#define CONSECUTIVE_REQUIRED 3     // Raise from 2
```

### Detection Not Sensitive Enough

Lower thresholds:
```cpp
#define DETECTION_THRESHOLD 0.15f  // Lower from 0.18
#define DETECTION_RAW_MIN 0.12f    // Lower from 0.15
#define CONSECUTIVE_REQUIRED 2     // Keep at 2
```

### Too Many Alerts

Increase cooldown:
```cpp
#define LORA_COOLDOWN_MS 60000  // 60 seconds
```

### Alerts Not Showing in Serial

Check baud rate - must be **115200**:
```cpp
Serial.begin(115200);
```

---

## Configuration Checklist

Before deployment, verify:

- [ ] Correct `DEMO_MODE` setting for your use case
- [ ] LoRa frequency matches your region (915MHz US, 868MHz EU)
- [ ] Pin assignments match your wiring
- [ ] Serial baud rate is 115200
- [ ] Firmware compiles without errors
- [ ] Device connects to Serial Monitor
- [ ] Audio levels show in debug output
- [ ] Test detection works with sample sounds

---

## File Locations

| File | Purpose |
|------|---------|
| `firmware/guardian_node/config.h` | Main configuration |
| `firmware/guardian_node/guardian_node.ino` | Main application |
| `firmware/guardian_node/ml_inference.cpp` | ML detection logic |
| `firmware/guardian_node/audio_capture.cpp` | Microphone handling |

---

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| Arduino IDE | 2.0+ | Required |
| ESP32 Board Package | 3.2.0 | Tested |
| Edge Impulse Library | 1.0.1 | Included |
| Heltec Board | WiFi LoRa 32 V3 | ESP32-S3 |

---

## Support

For configuration issues:
1. Check Serial Monitor output for errors
2. Verify pin connections
3. Try Demo Mode first to confirm hardware works
4. Gradually adjust thresholds based on your environment

**Project**: Forest Guardian - Microsoft Imagine Cup 2026
