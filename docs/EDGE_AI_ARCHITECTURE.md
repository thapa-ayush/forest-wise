# Forest Guardian Edge AI Architecture

## Overview

Forest Guardian uses a **hybrid Edge + Cloud AI architecture** optimized for Microsoft Imagine Cup requirements:

```
┌────────────────────────────────────────────────────────────────────┐
│                    FOREST GUARDIAN NODE                            │
│    ┌────────────┐    ┌───────────────┐    ┌─────────────────┐    │
│    │  INMP441   │───>│   FFT-based   │───>│   Detection     │    │
│    │ Microphone │    │  Spectral     │    │   Decision      │    │
│    └────────────┘    │  Analysis     │    └─────────────────┘    │
│                      └───────────────┘             │              │
│                                                     ▼              │
│                                            ┌─────────────────┐    │
│                                            │   LoRa Radio    │    │
│                                            │   SX1262        │    │
└────────────────────────────────────────────┴────────┬────────┴────┘
                                                       │
                                                       │ LoRaWAN/LoRa
                                                       ▼
┌───────────────────────────────────────────────────────────────────┐
│                         GATEWAY                                   │
│    ┌────────────────┐         ┌──────────────────────┐          │
│    │   LoRa Radio   │────────>│   MQTT/HTTP Bridge   │          │
│    │   Receiver     │         │                      │          │
│    └────────────────┘         └──────────┬───────────┘          │
└──────────────────────────────────────────┼──────────────────────┘
                                           │ HTTPS
                                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                    AZURE CLOUD SERVICES                           │
│                                                                   │
│  ┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │  Azure IoT   │──>│ Azure Custom    │──>│  Azure Maps      │  │
│  │     Hub      │   │ Vision/Speech   │   │  (Visualization) │  │
│  └──────────────┘   └─────────────────┘   └──────────────────┘  │
│         │                    │                     │             │
│         ▼                    ▼                     ▼             │
│  ┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │   Stream     │   │  ML Detection   │   │  Alert Dashboard │  │
│  │   Analytics  │   │  Verification   │   │   & Reporting    │  │
│  └──────────────┘   └─────────────────┘   └──────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

## Edge AI Component (ESP32-S3)

### FFT-based Spectral Analysis

The on-device detection uses Fast Fourier Transform to analyze audio in real-time:

```
Audio Input (16kHz) → Hanning Window → FFT (512-pt) → Magnitude → Band Analysis → Score
```

#### Chainsaw Audio Characteristics Detected:
| Frequency Band | Characteristic | Detection Weight |
|---------------|----------------|------------------|
| 100-500 Hz    | Engine fundamental | 25% |
| 500-1000 Hz   | 2-stroke motor whine | 20% |
| 1000-2000 Hz  | Chain cutting noise | 20% |
| 2000-4000 Hz  | Mechanical sounds | 15% |
| Harmonics     | Engine harmonics (2x, 3x) | 20% |

#### Performance:
- **Inference time**: ~20-30ms per analysis
- **Latency**: <100ms from sound to detection
- **Memory**: ~8KB RAM for FFT buffers
- **Power**: Low power (<50mA during analysis)

### Why FFT Instead of TFLite?

1. **Reliability**: FFT works consistently on ESP32-S3
2. **Speed**: Faster inference (20ms vs 200ms+)
3. **Interpretability**: Clear spectral features we can explain
4. **No dependencies**: Works with standard Arduino libraries
5. **Real-time**: Can analyze continuous audio stream

## Azure AI Services (Cloud Component)

### 1. Azure Custom Vision (ML Verification)
**Purpose**: Secondary ML verification of detections

```
Detection Event → Upload spectral features → Custom Vision API → Verified/False Positive
```

**Implementation**:
- Train Custom Vision model on chainsaw spectral signatures
- Use HTTP REST API from gateway
- Reduces false positives from similar sounds

### 2. Azure Speech Services (Optional Enhancement)
**Purpose**: Audio classification of environmental sounds

**Use cases**:
- Classify detection into: chainsaw, truck, helicopter, natural
- Multi-language voice alerts for rangers

### 3. Azure IoT Hub
**Purpose**: Device-to-cloud communication & management

**Features**:
- Secure device identity
- Message routing to other Azure services
- Device twin for remote configuration
- Direct methods for remote commands

### 4. Azure Maps
**Purpose**: Geospatial visualization

**Features**:
- Real-time detection heatmaps
- Forest zone boundaries
- Ranger location tracking
- Route optimization for response

### 5. Azure Stream Analytics (Optional)
**Purpose**: Real-time event processing

**Features**:
- Pattern detection across multiple nodes
- Anomaly detection in sensor data
- Alert aggregation

## Imagine Cup Requirements Checklist

| Requirement | Solution |
|------------|----------|
| ✅ TinyML on device | FFT Spectral Analysis (Edge AI) |
| ✅ Azure AI Service 1 | Azure Custom Vision (ML verification) |
| ✅ Azure AI Service 2 | Azure IoT Hub + Azure Maps |
| ✅ Real-world impact | Illegal logging detection |
| ✅ Scalable solution | LoRa mesh network architecture |

## Testing the Edge Detection

### With Chainsaw Sounds:
1. Play chainsaw audio from YouTube/mobile:
   - Search: "chainsaw cutting wood sound"
   - Place phone 20-50cm from microphone
   
2. Expected detection characteristics:
   - Strong 100-500 Hz energy (engine)
   - Harmonics at 2x, 3x fundamental
   - Broadband noise in 1000-2000 Hz range

### Serial Monitor Output:
```
[ML] Freq bands - Low:28% MidLow:22% Mid:18% High:12% Peak:186Hz Score:0.65
[ML] Confidence: 65% (threshold: 50%) Time: 24ms
=== CHAINSAW DETECTED! ===
```

### Adjusting Sensitivity:
In `config.h`:
```cpp
#define DETECTION_THRESHOLD 0.50f  // Lower = more sensitive
```

## Future Enhancements

1. **Multi-node correlation**: Detect same chainsaw from multiple nodes for triangulation
2. **Adaptive thresholds**: Auto-adjust based on ambient noise levels
3. **Sound classification**: Distinguish chainsaw types (commercial vs handheld)
4. **Power optimization**: Sleep between detections, wake on loud sounds
