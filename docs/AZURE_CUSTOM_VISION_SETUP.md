# Azure Custom Vision Setup Guide

## Overview

This guide walks you through creating an Azure Custom Vision model to classify audio spectrograms as:
- **chainsaw** - Illegal logging activity (CRITICAL threat)
- **vehicle** - Potential logging vehicle (MEDIUM threat)  
- **nature** - Normal forest sounds (NO threat)

## Step 1: Create Azure Custom Vision Resource

### Using Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource**
3. Search for **Custom Vision**
4. Click **Create**
5. Fill in the details:

| Setting | Value |
|---------|-------|
| Create options | **Both** (Training + Prediction) |
| Subscription | Your subscription |
| Resource group | `forest-guardian-rg` |
| Region | East US (or nearest) |
| Name | `forest-guardian-cv` |
| Training pricing tier | **Free F0** (2 projects, 5,000 images) |
| Prediction pricing tier | **Free F0** (10K predictions/month) |

6. Click **Review + create** → **Create**

### Using Azure CLI

```bash
# Login to Azure
az login

# Create resource group (if not exists)
az group create --name forest-guardian-rg --location eastus

# Create Custom Vision Training resource
az cognitiveservices account create \
    --name forest-guardian-cv-training \
    --resource-group forest-guardian-rg \
    --kind CustomVision.Training \
    --sku F0 \
    --location eastus

# Create Custom Vision Prediction resource
az cognitiveservices account create \
    --name forest-guardian-cv-prediction \
    --resource-group forest-guardian-rg \
    --kind CustomVision.Prediction \
    --sku F0 \
    --location eastus
```

## Step 2: Get Your Keys and Endpoints

### From Azure Portal

1. Go to your **Custom Vision Training** resource
2. Click **Keys and Endpoint**
3. Copy:
   - **Key 1** (Training Key)
   - **Endpoint** (Training Endpoint)

4. Go to your **Custom Vision Prediction** resource  
5. Click **Keys and Endpoint**
6. Copy:
   - **Key 1** (Prediction Key)
   - **Endpoint** (Prediction Endpoint)

### From Azure CLI

```bash
# Get Training Key
az cognitiveservices account keys list \
    --name forest-guardian-cv-training \
    --resource-group forest-guardian-rg

# Get Prediction Key
az cognitiveservices account keys list \
    --name forest-guardian-cv-prediction \
    --resource-group forest-guardian-rg

# Get Endpoints
az cognitiveservices account show \
    --name forest-guardian-cv-prediction \
    --resource-group forest-guardian-rg \
    --query properties.endpoint
```

## Step 3: Create Project in Custom Vision Portal

1. Go to [Custom Vision Portal](https://www.customvision.ai/)
2. Sign in with your Azure account
3. Click **New Project**
4. Fill in:

| Setting | Value |
|---------|-------|
| Name | `forest-guardian-spectrograms` |
| Resource | `forest-guardian-cv-training` |
| Project Type | **Classification** |
| Classification Type | **Multiclass** (single tag per image) |
| Domain | **General [A2]** (best for spectrograms) |

5. Click **Create project**
6. **Copy the Project ID** from the URL:
   ```
   https://www.customvision.ai/projects/YOUR-PROJECT-ID-HERE/images
   ```

## Step 4: Prepare Training Images

You need spectrogram images for training. Here's the recommended structure:

```
training_images/
├── chainsaw/           # 50+ images
│   ├── spec_001.png
│   ├── spec_002.png
│   └── ...
├── vehicle/            # 50+ images
│   ├── spec_001.png
│   └── ...
└── nature/             # 50+ images
    ├── spec_001.png
    └── ...
```

### Option A: Use Existing Spectrograms

If you have spectrograms from testing:
```bash
# Copy from your hub's spectrogram folder
cp hub/static/spectrograms/*.png training_images/
# Then manually sort them into folders
```

### Option B: Generate from Audio Files

Use the included script:
```bash
cd ml
python scripts/generate_training_spectrograms.py
```

### Option C: Use Sample Dataset

Download chainsaw/nature audio samples and generate spectrograms:
- [ESC-50 Dataset](https://github.com/karolpiczak/ESC-50) - Environmental sounds
- [UrbanSound8K](https://urbansounddataset.weebly.com/) - Urban sounds

## Step 5: Upload & Tag Images

### Using Custom Vision Portal (Recommended)

1. In your project, click **Add images**
2. Select all images from `training_images/chainsaw/`
3. Add tag: `chainsaw`
4. Click **Upload**
5. Repeat for `vehicle` and `nature` folders

### Using Python Script

Run the upload script (created below):

```bash
cd hub
python scripts/upload_custom_vision.py
```

## Step 6: Train the Model

### Using Portal

1. Click **Train** button (top right)
2. Select **Quick Training** (for initial test)
3. Wait for training to complete (5-15 minutes)

### Using API

```python
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from msrest.authentication import ApiKeyCredentials

credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
trainer = CustomVisionTrainingClient(TRAINING_ENDPOINT, credentials)

# Start training
iteration = trainer.train_project(PROJECT_ID)
print(f"Training started: {iteration.id}")
```

## Step 7: Publish the Model

After training completes:

1. Click on the trained iteration (e.g., "Iteration 1")
2. Click **Publish**
3. Fill in:
   - **Model name**: `production` (or any name)
   - **Prediction resource**: `forest-guardian-cv-prediction`
4. Click **Publish**

**Note the iteration name** - you'll need it for the API.

## Step 8: Configure Forest Guardian Hub

Add these to your `.env` file:

```bash
# Azure Custom Vision
AZURE_CUSTOM_VISION_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
AZURE_CUSTOM_VISION_KEY=your-prediction-key-here
AZURE_CUSTOM_VISION_PROJECT_ID=your-project-id-here
AZURE_CUSTOM_VISION_ITERATION=production
```

Or update `hub/.env`:

```bash
nano hub/.env
```

## Step 9: Test the Integration

### Test API Directly

```bash
curl -X POST \
  "https://eastus.api.cognitive.microsoft.com/customvision/v3.0/Prediction/YOUR_PROJECT_ID/classify/iterations/production/image" \
  -H "Prediction-Key: YOUR_PREDICTION_KEY" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @test_spectrogram.png
```

### Test in Forest Guardian

1. Start the hub:
   ```bash
   cd hub
   python app.py
   ```

2. Go to Dashboard → AI Settings
3. Select **Custom Vision** mode
4. Upload or trigger a spectrogram analysis

### Test with Python

```python
# Quick test
from ai_service import analyze_with_custom_vision

result = analyze_with_custom_vision("static/spectrograms/test.png")
print(f"Classification: {result['classification']}")
print(f"Confidence: {result['confidence']}%")
print(f"Threat Level: {result['threat_level']}")
```

## Step 10: Check AI Status Endpoint

```bash
curl http://localhost:5000/api/ai/status
```

Expected response:
```json
{
  "current_mode": "custom_vision",
  "services": {
    "gpt4o": {
      "configured": true,
      "deployment": "gpt-4o"
    },
    "custom_vision": {
      "configured": true,
      "project_id": "abc12345...",
      "iteration": "production"
    }
  }
}
```

## Tips for Better Accuracy

1. **More images = better accuracy** - Aim for 100+ per class
2. **Diverse samples** - Different chainsaws, distances, background noise
3. **Consistent spectrogram format** - Same size (32x32), 32 mel bins (matching ESP32 firmware)
4. **Balance classes** - Similar number of images per class
5. **Advanced Training** - Use this for production (more accurate but slower)

## Troubleshooting

### "Custom Vision not configured"
- Check `.env` file has all 4 variables
- Restart the Flask app after changing `.env`

### "401 Unauthorized"  
- Verify Prediction Key (not Training Key)
- Check endpoint matches your region

### "404 Not Found"
- Verify Project ID
- Check iteration name is correct and published

### Low Accuracy
- Add more training images
- Use Advanced Training
- Check image quality/consistency

## Cost Estimate (Free Tier)

| Resource | Free Tier Limit |
|----------|-----------------|
| Training | 2 projects, 5,000 images, 1 hour training/month |
| Prediction | 10,000 predictions/month |

For Imagine Cup demo, free tier is sufficient!

## Next Steps

1. ✅ Create Custom Vision resource
2. ✅ Create project and upload images
3. ✅ Train and publish model
4. ✅ Configure `.env` with credentials
5. ✅ Test with Forest Guardian dashboard
6. ✅ Use `auto` mode for best results (Custom Vision + GPT-4o verification)
