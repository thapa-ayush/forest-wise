# Azure Services Setup Guide

This guide covers setting up all Azure services required for Forest Guardian.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Azure OpenAI (GPT-4o Vision)](#azure-openai-gpt-4o-vision)
- [Azure Custom Vision](#azure-custom-vision)
- [Azure Maps](#azure-maps)
- [Azure Functions](#azure-functions)
- [Environment Configuration](#environment-configuration)

---

## Prerequisites

1. **Azure Account** - [Create free account](https://azure.microsoft.com/free/)
2. **Azure CLI** (optional) - `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`

---

## Azure OpenAI (GPT-4o Vision)

GPT-4o Vision provides the most accurate spectrogram analysis with detailed reasoning.

### Setup

1. Go to [Azure AI Studio](https://ai.azure.com)
2. Create a new **Hub** or use existing
3. Deploy **GPT-4o** model
4. Note the **Endpoint URL** and **API Key**

### Configuration

```bash
# In hub/.env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Rate Limits

| Tier | Requests/min | Tokens/min |
|------|-------------|------------|
| Free | 3 | 1,000 |
| S0 | 60 | 40,000 |

The hub tracks rate limits and falls back to Custom Vision when limits are reached.

---

## Azure Custom Vision

Custom Vision provides fast, cost-effective classification (88.9% accuracy).

### Setup

1. Go to [Custom Vision Portal](https://www.customvision.ai/)
2. Create new **Project**:
   - Name: `forest-guardian-spectrograms`
   - Project Type: **Classification**
   - Classification Type: **Multilabel**
   - Domain: **General (compact)** (for TFLite export)

3. Upload training images:
   - `chainsaw/` - Chainsaw spectrograms
   - `nature/` - Forest sounds
   - `vehicle/` - Engine sounds

4. Train the model (Advanced Training recommended)

5. Get credentials:
   - Go to **Settings** → Copy **Prediction Key**
   - Note **Project ID** from URL
   - Note **Endpoint** from Settings

### Configuration

```bash
# In hub/.env
CUSTOM_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
CUSTOM_VISION_PREDICTION_KEY=your-prediction-key
CUSTOM_VISION_PROJECT_ID=your-project-id
CUSTOM_VISION_ITERATION_NAME=Iteration1
```

### Export TFLite Model

For offline inference on Raspberry Pi:

1. In Custom Vision Portal → **Performance** tab
2. Click **Export** → **TensorFlow** → **TensorFlow Lite**
3. Download and extract to `ml/models/`

```bash
cd ml/models
unzip TensorFlow.zip
mv model.tflite chainsaw_classifier.tflite
```

---

## Azure Maps

Azure Maps provides interactive geospatial visualization.

### Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Create **Azure Maps Account**:
   - Search "Azure Maps"
   - Create new account (S0 tier for free usage)

3. Get **Primary Key**:
   - Go to resource → **Authentication**
   - Copy **Primary Key**

### Configuration

```bash
# In hub/.env
AZURE_MAPS_KEY=your-azure-maps-key
```

### Features Used

- Interactive map with satellite/terrain views
- Node location markers with status colors
- Alert markers with GPS coordinates
- Distance calculations for ranger dispatch

---

## Azure Functions

Azure Functions handle serverless event processing.

### Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Create **Function App**:
   - Runtime: **Python 3.11**
   - Plan: **Consumption (Serverless)**

3. Deploy functions:

```bash
cd azure
func azure functionapp publish your-function-app-name
```

### Functions

#### AlertProcessor

Triggered on new detections, sends notifications.

```python
# azure/AlertProcessor/__init__.py
# Webhook for critical alerts
```

#### DailyReport

Generates daily summary emails.

```python
# azure/DailyReport/__init__.py
# Scheduled for 6 AM daily
```

### Configuration

```bash
# In hub/.env (optional - for webhook integration)
AZURE_FUNCTION_URL=https://your-function.azurewebsites.net/api/AlertProcessor
AZURE_FUNCTION_KEY=your-function-key
```

---

## Environment Configuration

### Complete .env File

Create `hub/.env`:

```bash
# =============================================================================
# Forest Guardian Hub - Environment Configuration
# =============================================================================

# Flask Configuration
FLASK_SECRET_KEY=your-random-secret-key-here
FLASK_DEBUG=false

# Database
DATABASE_PATH=forest_guardian.db

# LoRa Configuration
LORA_ENABLED=true

# =============================================================================
# Azure OpenAI (GPT-4o Vision) - Primary AI
# =============================================================================
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# =============================================================================
# Azure Custom Vision - Fast Classification
# =============================================================================
CUSTOM_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
CUSTOM_VISION_PREDICTION_KEY=your-prediction-key
CUSTOM_VISION_PROJECT_ID=your-project-id
CUSTOM_VISION_ITERATION_NAME=Iteration1

# Training key (for uploading new images)
CUSTOM_VISION_TRAINING_KEY=your-training-key

# =============================================================================
# Azure Maps - Geospatial Visualization
# =============================================================================
AZURE_MAPS_KEY=your-azure-maps-key

# =============================================================================
# Local TFLite Model - Offline Inference
# =============================================================================
TFLITE_MODEL_PATH=../ml/models/chainsaw_classifier.tflite
TFLITE_LABELS_PATH=../ml/models/labels.txt

# =============================================================================
# AI Mode Configuration
# =============================================================================
# Options: auto, gpt4o, custom_vision, local
DEFAULT_AI_MODE=auto
```

### .env.example

An example file is provided at `hub/.env.example` with all available options documented.

---

## Testing Services

### Test Azure OpenAI

```bash
curl -X POST "$AZURE_OPENAI_ENDPOINT/openai/deployments/gpt-4o/chat/completions?api-version=2024-12-01-preview" \
  -H "Content-Type: application/json" \
  -H "api-key: $AZURE_OPENAI_KEY" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
```

### Test Custom Vision

```bash
curl -X POST "$CUSTOM_VISION_ENDPOINT/customvision/v3.0/Prediction/$CUSTOM_VISION_PROJECT_ID/classify/iterations/$CUSTOM_VISION_ITERATION_NAME/image" \
  -H "Prediction-Key: $CUSTOM_VISION_PREDICTION_KEY" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @test_spectrogram.png
```

### Test in Hub

Visit `http://localhost:5000` and check the AI Status indicator in the dashboard header.

---

## Cost Estimation

| Service | Free Tier | Estimated Monthly (10 nodes) |
|---------|-----------|------------------------------|
| Azure OpenAI | 1M tokens | $5-15 |
| Custom Vision | 5K predictions | $0 (under limit) |
| Azure Maps | 5K transactions | $0 (under limit) |
| Azure Functions | 1M executions | $0 (under limit) |

**Total estimated cost:** $5-20/month for typical deployment

---

*Last updated: January 2026*
