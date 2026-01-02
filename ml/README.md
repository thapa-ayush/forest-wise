# Forest Guardian - Machine Learning Pipeline

This folder contains the ML pipeline for training and deploying a TinyML chainsaw detection model on ESP32.

## Pipeline Steps

1. **Data Collection**
   - Place audio samples in `data/chainsaw/`, `data/forest/`, `data/hard_negatives/`
   - Or run `scripts/download_data.py` to fetch from public sources

2. **Preprocessing**
   - Run `scripts/preprocess.py` to convert audio to mel spectrograms

3. **Training**
   - Run `scripts/train.py` to train the CNN model locally
   - Or run `scripts/azure_ml_train.py` to train on Azure ML

4. **Conversion**
   - Run `scripts/convert_tflite.py` to export to TFLite and C header

## Model Architecture
- Input: 40x32 mel spectrogram
- Conv2D(8) → MaxPool → Conv2D(16) → MaxPool → Conv2D(32) → GlobalAvgPool → Dense(16) → Dense(1, sigmoid)
- Output: Chainsaw confidence (0-1)
- Size: <100KB (INT8 quantized)

## Requirements
```sh
pip install -r requirements.txt
```

## Azure ML Integration
See `scripts/azure_ml_train.py` for cloud training.

## License
MIT
