# Azure Custom Vision Training & Export Guide
# Forest Guardian - Offline Spectrogram Analysis

## Overview

This guide walks you through training a spectrogram classifier on Azure Custom Vision and exporting it for offline use on Raspberry Pi.

## Prerequisites

- Azure account with Custom Vision resource
- Training images in `ml/training_images/` (you already have these!)
- Python with Azure SDK

## Step 1: Create Custom Vision Resource (if not done)

### Via Azure Portal:
1. Go to [portal.azure.com](https://portal.azure.com)
2. Click "Create a resource"
3. Search for "Custom Vision"
4. Select **"Custom Vision"** (not Custom Vision Service)
5. Click "Create"
6. Fill in:
   - **Subscription**: Your subscription
   - **Resource Group**: `forest-guardian-rg`
   - **Region**: `Canada Central` (or nearest)
   - **Name**: `forest-guardian-cv-local`
   - **Training pricing tier**: `F0` (Free) or `S0`
   - **Prediction pricing tier**: `F0` (Free) or `S0`
7. Click "Review + create" → "Create"

### Get Your Keys:
After creation, go to the resource and note:
- **Training Endpoint**: `https://canadacentral.api.cognitive.microsoft.com/`
- **Training Key**: (from Keys section)
- **Prediction Endpoint**: (same or similar)
- **Prediction Key**: (from Keys section)

## Step 2: Create Project & Upload Images

### Option A: Via customvision.ai Portal (Easiest)

1. Go to [customvision.ai](https://www.customvision.ai/)
2. Sign in with your Azure account
3. Click "New Project"
4. Configure:
   - **Name**: `forest-guardian-spectrogram`
   - **Resource**: Select your Custom Vision resource
   - **Project Type**: `Classification`
   - **Classification Type**: `Multiclass` (single tag per image)
   - **Domain**: `General (compact)` ⚠️ **IMPORTANT for export!**
5. Click "Create Project"

### Upload Training Images:

1. Click "Add images"
2. Select all images from `ml/training_images/chainsaw/`
3. Add tag: `chainsaw`
4. Click "Upload"
5. Repeat for `nature` and `vehicle` folders

### Option B: Via Python Script (Automated)

Run the upload script below after setting environment variables.

## Step 3: Train the Model

1. In customvision.ai, click **"Train"** button (top right)
2. Choose **"Quick Training"** (15-30 minutes) or **"Advanced"** (1+ hour, better accuracy)
3. Wait for training to complete
4. Review the **Performance** metrics:
   - **Precision**: % of correct positive predictions
   - **Recall**: % of actual positives found
   - **AP**: Average Precision (overall accuracy)

### Expected Performance:
| Class | Target Precision | Target Recall |
|-------|------------------|---------------|
| chainsaw | >85% | >80% |
| nature | >90% | >90% |
| vehicle | >80% | >75% |

## Step 4: Export Model for Raspberry Pi

### Via Portal (Recommended):

1. Go to **"Performance"** tab
2. Click on your trained iteration
3. Click **"Export"** button
4. Select platform: **"TensorFlow"**
5. Select format: **"TensorFlow Lite"**
6. Click **"Export"** → **"Download"**
7. Extract the ZIP file

### You'll get:
```
export/
├── model.tflite      # The model file (~1-5MB)
├── labels.txt        # Class labels
└── metadata.json     # Model info
```

### Copy to Raspberry Pi:
```bash
# On your development machine
scp export/model.tflite pi@raspberrypi:/home/pi/forest-guardian/ml/models/chainsaw_classifier.tflite
scp export/labels.txt pi@raspberrypi:/home/pi/forest-guardian/ml/models/labels.txt
```

Or if working directly on Pi:
```bash
cp export/model.tflite ~/forest-g/ml/models/chainsaw_classifier.tflite
cp export/labels.txt ~/forest-g/ml/models/labels.txt
```

## Step 5: Test Offline Inference

```bash
cd ~/forest-g/hub
source venv/bin/activate
python local_inference.py
```

## Environment Variables

Add to your `.env` or `local.settings.json`:

```bash
# Azure Custom Vision - Training
AZURE_CV_TRAINING_ENDPOINT=https://canadacentral.api.cognitive.microsoft.com/
AZURE_CV_TRAINING_KEY=your-training-key

# Azure Custom Vision - Prediction (for online verification)
AZURE_CUSTOM_VISION_ENDPOINT=https://canadacentral.api.cognitive.microsoft.com/
AZURE_CUSTOM_VISION_KEY=your-prediction-key
AZURE_CUSTOM_VISION_PROJECT_ID=your-project-id
AZURE_CUSTOM_VISION_ITERATION=your-published-iteration-name
```

## Troubleshooting

### "Domain must be compact for export"
- When creating project, select a **"compact"** domain
- Options: `General (compact)`, `Food (compact)`, `Landmarks (compact)`
- Non-compact domains cannot be exported!

### "Model file not found"
- Ensure the `.tflite` file is at: `ml/models/chainsaw_classifier.tflite`
- Check file permissions: `chmod 644 ml/models/*.tflite`

### "Low accuracy on Pi"
- Ensure spectrogram preprocessing matches training:
  - Same image size (resize to 224x224 for Custom Vision)
  - Same normalization (0-255 or 0-1)
  - Grayscale vs RGB (Custom Vision uses RGB)

## Quick Reference

| Item | Value |
|------|-------|
| Model Path | `ml/models/chainsaw_classifier.tflite` |
| Labels Path | `ml/models/labels.txt` |
| Input Size | 224x224x3 (RGB) for Custom Vision |
| Output | Softmax probabilities per class |

## Next Steps

After exporting:
1. Test with `python local_inference.py`
2. The hub will automatically use local inference when offline
3. When online, results sync to Azure for GPT-4o verification
