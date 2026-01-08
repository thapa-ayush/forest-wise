# Forest Guardian - Machine Learning Pipeline

This folder contains the ML pipeline for training spectrogram classifiers for Azure Custom Vision.

## Overview

The Forest Guardian system uses **Azure AI** for sound classification instead of on-device ML:

1. **ESP32 Node**: Generates mel spectrograms from audio (threshold-based anomaly detection)
2. **Raspberry Pi Hub**: Receives spectrograms via LoRa
3. **Azure GPT-4o Vision**: Analyzes spectrograms with high accuracy (~95%)
4. **Azure Custom Vision**: Optional faster classifier trained on spectrograms

## Training Data

Training data is **NOT tracked in git** due to size. Download separately:

```bash
# Create directories
mkdir -p audio_samples/{chainsaw,nature,vehicle}
mkdir -p training_images/{chainsaw,nature,vehicle}

# Download from Freesound or record your own samples
# See scripts/download_data.py for automated download
```

## Pipeline Steps

### 1. Collect Audio Samples
- Place chainsaw audio in `audio_samples/chainsaw/`
- Place forest/nature sounds in `audio_samples/nature/`
- Place vehicle sounds in `audio_samples/vehicle/`

### 2. Generate Spectrograms
```bash
python scripts/preprocess.py
```
This creates 64x64 mel spectrograms in `training_images/`

### 3. Upload to Azure Custom Vision
```bash
cd ../hub
python scripts/upload_custom_vision.py
```

### 4. Train in Azure Portal
- Go to customvision.ai
- Train iteration
- Publish as "production"

## Files

- `scripts/preprocess.py` - Convert audio to spectrograms
- `scripts/download_data.py` - Download training data from Freesound
- `requirements.txt` - Python dependencies

## Model Architecture (Custom Vision)

Azure Custom Vision handles architecture automatically. For reference:
- Input: 64x64 RGB spectrogram images
- Output: Classification (chainsaw, nature, vehicle)
- Deployed as REST API endpoint

## Requirements

```bash
pip install -r requirements.txt
```
