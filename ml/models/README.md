# Forest Guardian - ML Models Directory

This directory stores trained TFLite models for offline inference on Raspberry Pi.

## Files

After training and exporting from Azure Custom Vision:

| File | Description |
|------|-------------|
| `chainsaw_classifier.tflite` | TFLite model exported from Azure Custom Vision |
| `labels.txt` | Class labels (one per line) |

## How to Get the Model

### Option 1: Azure Custom Vision (Recommended)

1. Go to [customvision.ai](https://customvision.ai)
2. Train your model with spectrogram images
3. Click **Performance** → **Export**
4. Select **TensorFlow** → **TensorFlow Lite**
5. Download and extract the ZIP
6. Copy files here:
   ```bash
   cp export/model.tflite ./chainsaw_classifier.tflite
   cp export/labels.txt ./labels.txt
   ```

### Option 2: Use Upload Script

```bash
cd /home/forestguardain/forest-g
source ml/venv/bin/activate  # or hub/venv/bin/activate

# Set environment variables
export AZURE_CV_TRAINING_ENDPOINT='https://your-region.api.cognitive.microsoft.com/'
export AZURE_CV_TRAINING_KEY='your-training-key'

# Run upload and training script
python ml/scripts/upload_to_custom_vision.py
```

## Expected Model Format

### Azure Custom Vision Export:
- Input: `(1, 224, 224, 3)` - RGB image
- Output: `(1, N)` - Softmax probabilities for N classes
- Labels in `labels.txt`

### Local Training:
- Input: `(1, 40, 32, 1)` - Grayscale spectrogram
- Output: `(1, 1)` - Binary sigmoid (chainsaw probability)

The `local_inference.py` module auto-detects the model type.
