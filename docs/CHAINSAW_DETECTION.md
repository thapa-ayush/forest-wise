# Forest Guardian - Chainsaw Detection System

## Overview

The Forest Guardian uses **Edge Impulse TinyML** for on-device chainsaw detection. The system runs a neural network directly on the ESP32-S3 microcontroller, enabling real-time audio classification without cloud connectivity.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOREST GUARDIAN NODE                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ INMP441  │───►│  I2S     │───►│  Edge    │───►│  Alert   │  │
│  │   Mic    │    │ Capture  │    │ Impulse  │    │ Decision │  │
│  └──────────┘    │ 16kHz    │    │   ML     │    │  Logic   │  │
│                  └──────────┘    └──────────┘    └────┬─────┘  │
│                                                       │        │
│                                       ┌───────────────▼──────┐ │
│                                       │   LoRa Transmission  │ │
│                                       │   to Hub (SX1262)    │ │
│                                       └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         HUB                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ LoRa Receive │───►│ Azure AI     │───►│ Alert        │       │
│  │              │    │ Verification │    │ Rangers      │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Edge Impulse Model

### Model Specifications

| Parameter | Value |
|-----------|-------|
| **Model Type** | MFCC + Neural Network |
| **Training Accuracy** | 85.1% |
| **Inference Time** | ~3ms |
| **RAM Usage** | 12.5 KB |
| **Flash Size** | 45.7 KB |
| **Sample Rate** | 16 kHz |
| **Window Size** | 1 second (16,000 samples) |
| **Classes** | `chainsaw`, `noise` |

### MFCC Configuration

```
- Num Cepstral Coefficients: 13
- Frame Length: 20ms (320 samples)
- Frame Stride: 20ms
- FFT Length: 256
- Num Filters: 32
- Output Features: 650 (50 frames × 13 coefficients)
```

### Training Data

- **Total Samples**: 4,022 segments
- **Chainsaw Sources**: Freesound.org (various chainsaw recordings)
- **Noise Sources**: Forest ambiance, birds, wind, rain, traffic

---

## Hardware Configuration

### Audio Capture (INMP441)

| Pin | Function | ESP32-S3 GPIO |
|-----|----------|---------------|
| SCK | Bit Clock | GPIO 7 |
| WS | Word Select | GPIO 6 |
| SD | Data | GPIO 5 |
| L/R | Channel | GND (Left) |
| VDD | Power | 3.3V |
| GND | Ground | GND |

### I2S Settings

```cpp
Sample Rate:    16000 Hz
Bits per Sample: 32-bit (converted to 16-bit)
Channel Format:  Stereo (one channel used)
DMA Buffers:     8 × 256 samples
```

---

## Configuration Modes

The system supports two modes configured in `config.h`:

### Demo Mode (for Imagine Cup presentations)

```cpp
#define DEMO_MODE 1
```

| Setting | Value | Reason |
|---------|-------|--------|
| Detection Threshold | 18% | Phone speakers produce weak signals |
| Raw Minimum | 15% | Lower bar for detection |
| Consecutive Hits | 2 | Faster response for demo |
| Alert Cooldown | 5 sec | Show multiple alerts |

### Production Mode (real forest deployment)

```cpp
#define DEMO_MODE 0
```

| Setting | Value | Reason |
|---------|-------|--------|
| Detection Threshold | 35% | Real chainsaws are loud (50-90%) |
| Raw Minimum | 25% | Higher bar reduces false positives |
| Consecutive Hits | 3 | More robust detection |
| Alert Cooldown | 30 sec | Prevent alert spam |

---

## Detection Algorithm

### Audio Processing Pipeline

```
1. I2S Capture (32-bit stereo)
        │
        ▼
2. Bit Shift (>>15) + Soft Clipping
   - Prevents audio distortion
   - Limits to ±24000 range
        │
        ▼
3. DC Offset Removal
   - Calculates mean of buffer
   - Subtracts from each sample
        │
        ▼
4. Normalization (÷ 32768)
   - Converts to -1.0 to 1.0 float range
   - Matches Edge Impulse training format
        │
        ▼
5. Edge Impulse Inference
   - MFCC feature extraction (40ms)
   - Neural network classification (~3ms)
        │
        ▼
6. Consecutive Detection Logic
   - Counts sequential detections above threshold
   - Prevents single-frame false positives
        │
        ▼
7. Alert Decision
   - Triggers when smoothed confidence > threshold
   - Respects cooldown period
```

### Consecutive Detection System

```cpp
if (raw_confidence >= DETECTION_RAW_MIN) {
    consecutive_detections++;
    if (consecutive_detections >= CONSECUTIVE_REQUIRED) {
        // Strong confidence buildup
        smoothed = 0.8 * raw + 0.2 * smoothed;
    } else {
        // Moderate buildup
        smoothed = 0.4 * raw + 0.6 * smoothed;
    }
} else {
    // Reset and decay
    consecutive_detections = 0;
    smoothed = smoothed * 0.5;
}
```

This prevents false positives from:
- Brief TV/radio sounds
- Random noise spikes
- Non-sustained sounds

---

## Serial Debug Output

```
[ML] Min:-15131 Max:15205 DC:953 Saw:21% Cons:2 Smooth:18% T:48ms
      │         │         │     │       │       │         │
      │         │         │     │       │       │         └─ Inference time
      │         │         │     │       │       └─ Smoothed confidence
      │         │         │     │       └─ Consecutive detection count
      │         │         │     └─ Raw chainsaw confidence
      │         │         └─ DC offset (should be near 0)
      │         └─ Maximum sample value
      └─ Minimum sample value
```

### Healthy Audio Ranges

| Metric | Good Range | Problem |
|--------|------------|---------|
| Min/Max | ±10000 to ±25000 | Clipping if ±32768 |
| DC Offset | -2000 to +2000 | High bias if >5000 |
| Inference Time | 40-60ms | Slow if >100ms |

---

## Troubleshooting

### Problem: Always 99% Noise

**Causes:**
1. Audio buffer not full (check `audio_capture_read`)
2. Audio clipping (values hitting ±32768)
3. Wrong bit shift (too much/little gain)

**Solutions:**
- Verify buffer fills 16,000 samples
- Adjust bit shift in `audio_capture.cpp`
- Check Min/Max values in serial output

### Problem: False Positives

**Causes:**
1. Threshold too low
2. TV/radio sounds triggering detection
3. Consecutive check not working

**Solutions:**
- Increase `DETECTION_THRESHOLD`
- Increase `CONSECUTIVE_REQUIRED`
- Check `Cons:` value in debug output

### Problem: No Detection from Phone Speakers

**Causes:**
1. Phone speakers can't reproduce low frequencies (50-400Hz)
2. Volume too low
3. Mic too far from speaker

**Solutions:**
- Use Bluetooth speaker with bass
- Use laptop speakers at max volume
- Place device very close to speaker
- Use Demo Mode settings

---

## Demo Tips for Imagine Cup

### Best Audio Sources

1. **Bluetooth speaker** - Best bass response
2. **Laptop speakers** - Moderate, use max volume
3. **Phone speaker** - Poor, very close to mic only

### Recommended YouTube Videos

Search for:
- "Chainsaw cutting wood close up"
- "Chainsaw felling tree"
- "Stihl chainsaw cutting"
- "Husqvarna chainsaw sound"

Videos with **actual cutting** (not just idle) work best.

### Demo Script

```
1. "This is Forest Guardian - an AI-powered illegal logging detector"
2. Show device monitoring (no alerts)
3. "When a chainsaw is detected..."
4. Play chainsaw sound
5. Device alerts! LED flashes, display shows alert
6. "Alert sent via LoRa to the hub"
7. "Azure AI verifies before alerting forest rangers"
```

### Video Recording Tips

- Record in quiet room (no background TV/music)
- Show serial monitor with detection percentages
- Mention: "Real chainsaws produce 50-90% confidence. We're demonstrating with speakers which have limited bass response."

---

## File Structure

```
firmware/guardian_node/
├── guardian_node.ino      # Main application
├── config.h               # Configuration (DEMO_MODE here)
├── ml_inference.cpp       # Edge Impulse integration
├── ml_inference.h
├── audio_capture.cpp      # I2S microphone handling
├── audio_capture.h
└── ...

ei-forest-guardian-chainsaw-arduino-1.0.1/
└── forest-guardian-chainsaw_inferencing/
    └── src/
        ├── forest-guardian-chainsaw_inferencing.h
        └── model-parameters/
            └── model_variables.h    # Model config
```

---

## Edge Impulse Project

- **Project URL**: https://studio.edgeimpulse.com
- **Model Export**: Arduino Library (.zip)
- **Library Location**: `Arduino/libraries/forest-guardian-chainsaw_inferencing/`

### Retraining the Model

1. Go to Edge Impulse Studio
2. Add more training data if needed
3. Retrain the model
4. Export as Arduino Library
5. Replace the library in Arduino/libraries/
6. Recompile and upload

---

## Performance Metrics

### Power Consumption

| State | Current | Notes |
|-------|---------|-------|
| Active Listening | ~80mA | Continuous audio capture |
| ML Inference | ~100mA | During classification |
| LoRa Transmit | ~120mA | Brief spike |
| Deep Sleep | ~10μA | When battery critical |

### Detection Range

| Source | Expected Range |
|--------|----------------|
| Real Chainsaw | 50-200 meters |
| Phone Speaker (demo) | 10-30 cm |
| Bluetooth Speaker | 1-3 meters |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Jan 2026 | Initial Edge Impulse integration |
| 1.0.1 | Jan 2026 | Added Demo/Production modes |
| 1.0.2 | Jan 2026 | Consecutive detection logic |

---

## Contact & Support

**Project**: Forest Guardian - Microsoft Imagine Cup 2026

For issues with:
- **Edge Impulse Model**: Check training data quality
- **Hardware**: Verify I2S wiring and pin configuration
- **Detection**: Adjust thresholds in `config.h`
