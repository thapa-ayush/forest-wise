# Azure Services Setup Guide for Forest Guardian

This guide walks you through setting up all required Azure services for the Forest Guardian illegal logging detection system.

## Prerequisites

- Azure account with active subscription
- Azure CLI installed (optional but recommended)
- Azure for Students or Pay-As-You-Go subscription

---

## Table of Contents

1. [Azure OpenAI Service (GPT-4o Vision)](#1-azure-openai-service-gpt-4o-vision)
2. [Azure Custom Vision](#2-azure-custom-vision)
3. [Azure IoT Hub (Optional)](#3-azure-iot-hub-optional)
4. [Azure Communication Services (Optional)](#4-azure-communication-services-optional)
5. [Azure Cosmos DB (Optional)](#5-azure-cosmos-db-optional)
6. [Configuration Summary](#6-configuration-summary)

---

## 1. Azure OpenAI Service (GPT-4o Vision)

GPT-4o Vision analyzes spectrogram images to detect chainsaw sounds with detailed reasoning.

### Step 1.1: Create Azure OpenAI Resource

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"**
3. Search for **"Azure OpenAI"**
4. Click **Create**

### Step 1.2: Configure the Resource

| Setting | Value |
|---------|-------|
| Subscription | Your subscription |
| Resource Group | `forest-guardian-rg` (create new) |
| Region | `East US` or `Sweden Central` (GPT-4o availability) |
| Name | `forest-guardian-openai` |
| Pricing Tier | `Standard S0` |

5. Click **Review + Create** → **Create**
6. Wait for deployment (~2-5 minutes)

### Step 1.3: Deploy GPT-4o Model

1. Go to your Azure OpenAI resource
2. Click **"Go to Azure OpenAI Studio"** (or visit [oai.azure.com](https://oai.azure.com))
3. Click **Deployments** → **Create new deployment**
4. Configure:

| Setting | Value |
|---------|-------|
| Model | `gpt-4o` |
| Deployment name | `gpt-4o` |
| Deployment type | Standard |
| Tokens per minute | 10K (adjust as needed) |

5. Click **Create**

### Step 1.4: Get API Keys

1. In Azure Portal, go to your OpenAI resource
2. Click **Keys and Endpoint** (left sidebar)
3. Copy:
   - **KEY 1** → `AZURE_OPENAI_KEY`
   - **Endpoint** → `AZURE_OPENAI_ENDPOINT`

```bash
# Example values (do not use these)
AZURE_OPENAI_KEY=abc123def456...
AZURE_OPENAI_ENDPOINT=https://forest-guardian-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

---

## 2. Azure Custom Vision

Custom Vision provides fast classification of spectrograms using your trained model.

### Step 2.1: Create Custom Vision Resources

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"**
3. Search for **"Custom Vision"**
4. Click **Create**

**Important:** You need TWO resources - Training and Prediction

### Step 2.2: Create Training Resource

| Setting | Value |
|---------|-------|
| Create options | **Both** (Training + Prediction) |
| Subscription | Your subscription |
| Resource Group | `forest-guardian-rg` |
| Region | `East US` |
| Name | `forest-guardian-cv` |
| Training pricing tier | `Free F0` or `Standard S0` |
| Prediction pricing tier | `Free F0` or `Standard S0` |

5. Click **Review + Create** → **Create**

### Step 2.3: Create and Train Your Project

1. Go to [Custom Vision Portal](https://customvision.ai)
2. Sign in with your Azure account
3. Click **New Project**

| Setting | Value |
|---------|-------|
| Name | `forest-guardian-spectrogram` |
| Resource | `forest-guardian-cv[Training]` |
| Project Type | **Classification** |
| Classification Type | **Multiclass** |
| Domain | **General (compact)** ⚠️ Important for edge deployment |

4. Click **Create Project**

### Step 2.4: Upload Training Images

You need spectrogram images for each category:

#### Required Tags:
- `chainsaw` - Spectrogram images of chainsaw sounds
- `vehicle` - Spectrogram images of vehicle/truck sounds  
- `natural` - Spectrogram images of forest ambient sounds

#### Upload Process:
1. Click **Add images**
2. Select 15-50 images per category (minimum 5 per tag)
3. Assign the appropriate tag
4. Repeat for each category

**💡 Tip:** Generate spectrograms from audio samples using the firmware's spectrogram generation code, or use tools like `librosa` in Python.

### Step 2.5: Train the Model

1. Click **Train** (top right)
2. Select **Quick Training** for initial testing
3. Wait for training to complete (~5-15 minutes)
4. Review performance metrics (aim for >90% precision)

### Step 2.6: Publish the Model

1. Click **Publish** (next to your iteration)
2. Configure:

| Setting | Value |
|---------|-------|
| Model name | `production` |
| Prediction resource | `forest-guardian-cv[Prediction]` |

3. Click **Publish**

### Step 2.7: Get Prediction API Keys

1. Click **Prediction URL** (after publishing)
2. You'll see two URLs - use the **"If you have an image file"** option
3. From the URL and key, extract:

```
URL: https://eastus.api.cognitive.microsoft.com/customvision/v3.0/Prediction/{project-id}/classify/iterations/{iteration}/image
```

4. Go to Azure Portal → Your Prediction resource → **Keys and Endpoint**
5. Copy:
   - **Prediction Endpoint** → `AZURE_CUSTOM_VISION_ENDPOINT`
   - **Prediction Key** → `AZURE_CUSTOM_VISION_KEY`
   - **Project ID** (from URL) → `AZURE_CUSTOM_VISION_PROJECT_ID`
   - **Iteration name** → `AZURE_CUSTOM_VISION_ITERATION`

```bash
# Example values
AZURE_CUSTOM_VISION_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
AZURE_CUSTOM_VISION_KEY=xyz789abc123...
AZURE_CUSTOM_VISION_PROJECT_ID=12345678-abcd-1234-efgh-567890abcdef
AZURE_CUSTOM_VISION_ITERATION=production
```

---

## 3. Azure IoT Hub (Optional)

For cloud connectivity and device management.

### Step 3.1: Create IoT Hub

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → Search **"IoT Hub"**
3. Click **Create**

| Setting | Value |
|---------|-------|
| Subscription | Your subscription |
| Resource Group | `forest-guardian-rg` |
| IoT Hub name | `forest-guardian-iothub` |
| Region | `East US` |
| Tier | `Free` (8,000 messages/day) or `Standard S1` |

4. Click **Review + Create** → **Create**

### Step 3.2: Get Connection String

1. Go to your IoT Hub resource
2. Click **Shared access policies** → **iothubowner**
3. Copy **Primary connection string** → `AZURE_IOTHUB_CONN_STR`

### Step 3.3: Register a Device

1. Click **Devices** → **Add Device**
2. Device ID: `raspberry-pi-hub`
3. Click **Save**
4. Click on the device → Copy **Primary Connection String** (for Pi)

---

## 4. Azure Communication Services (Optional)

For SMS alerts when threats are detected.

### Step 4.1: Create Communication Services

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → Search **"Communication Services"**
3. Click **Create**

| Setting | Value |
|---------|-------|
| Subscription | Your subscription |
| Resource Group | `forest-guardian-rg` |
| Resource name | `forest-guardian-comms` |
| Data location | `United States` |

4. Click **Review + Create** → **Create**

### Step 4.2: Get a Phone Number

1. Go to your Communication Services resource
2. Click **Phone numbers** → **Get**
3. Select country and number type (Toll-free for SMS)
4. Complete purchase (~$2/month)

### Step 4.3: Get Connection String

1. Click **Keys** (left sidebar)
2. Copy **Primary connection string** → `AZURE_COMMUNICATION_CONN_STR`

---

## 5. Azure Cosmos DB (Optional)

For cloud-based alert storage and analytics.

### Step 5.1: Create Cosmos DB Account

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → Search **"Azure Cosmos DB"**
3. Select **Azure Cosmos DB for NoSQL**
4. Click **Create**

| Setting | Value |
|---------|-------|
| Subscription | Your subscription |
| Resource Group | `forest-guardian-rg` |
| Account name | `forest-guardian-cosmos` |
| Location | `East US` |
| Capacity mode | **Serverless** (cost-effective) |

5. Click **Review + Create** → **Create**

### Step 5.2: Create Database and Container

1. Go to your Cosmos DB account
2. Click **Data Explorer** → **New Container**

| Setting | Value |
|---------|-------|
| Database id | `ForestGuardian` |
| Container id | `Alerts` |
| Partition key | `/node_id` |

3. Click **OK**

### Step 5.3: Get Keys

1. Click **Keys** (left sidebar)
2. Copy:
   - **URI** → `AZURE_COSMOS_ENDPOINT`
   - **PRIMARY KEY** → `AZURE_COSMOS_KEY`

---

## 6. Configuration Summary

After completing all steps, your `.env` file should look like:

```bash
# Forest Guardian Hub Configuration

# Flask Settings
FLASK_SECRET_KEY=generate-a-secure-random-key
FLASK_ENV=production
FLASK_DEBUG=0

# Database
DATABASE_URL=sqlite:///forest_guardian.db

# =============================================================================
# AZURE AI SERVICES (Required)
# =============================================================================

# Azure OpenAI (GPT-4o Vision)
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Azure Custom Vision
AZURE_CUSTOM_VISION_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
AZURE_CUSTOM_VISION_KEY=your-custom-vision-key
AZURE_CUSTOM_VISION_PROJECT_ID=your-project-guid
AZURE_CUSTOM_VISION_ITERATION=production

# AI Mode: 'gpt4o', 'custom_vision', or 'auto'
DEFAULT_AI_MODE=auto

# =============================================================================
# AZURE IOT & STORAGE (Optional)
# =============================================================================

AZURE_IOTHUB_CONN_STR=HostName=...
AZURE_COSMOS_KEY=your-cosmos-key
AZURE_COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/

# =============================================================================
# AZURE COMMUNICATION SERVICES (Optional)
# =============================================================================

AZURE_COMMUNICATION_CONN_STR=endpoint=...

# =============================================================================
# OTHER SETTINGS
# =============================================================================

ADMIN_EMAIL=your-email@example.com
SPECTROGRAM_DIR=static/spectrograms
AUTO_ANALYZE_SPECTROGRAMS=true
```

---

## Quick Reference: Required vs Optional Services

| Service | Purpose | Required? | Free Tier? |
|---------|---------|-----------|------------|
| **Azure OpenAI** | GPT-4o Vision analysis | ✅ Yes (for detailed analysis) | ❌ No (~$0.005/image) |
| **Azure Custom Vision** | Fast classification | ✅ Yes (for production) | ✅ Yes (10K predictions/month) |
| Azure IoT Hub | Cloud connectivity | ❌ Optional | ✅ Yes (8K messages/day) |
| Azure Communication Services | SMS alerts | ❌ Optional | ❌ No (~$0.0075/SMS) |
| Azure Cosmos DB | Cloud storage | ❌ Optional | ✅ Yes (Serverless) |

---

## Estimated Monthly Costs

| Service | Free Tier | Beyond Free Tier |
|---------|-----------|------------------|
| Azure OpenAI (GPT-4o) | N/A | ~$5-20/month (based on usage) |
| Custom Vision | 10K predictions free | $2/1000 predictions |
| IoT Hub | 8K messages/day free | $25/month (S1) |
| Communication Services | N/A | ~$2/month + SMS costs |
| Cosmos DB | Serverless free tier | ~$5/month |

**Total estimated cost:** $10-50/month depending on usage

---

## Testing Your Configuration

After configuring all services, test with:

```bash
cd /home/forestguardain/forest-g/hub
source venv/bin/activate  # if using virtualenv
python -c "
from config import Config
from ai_service import init_azure_openai, analyze_with_custom_vision

# Check OpenAI
print('OpenAI Key:', 'Set' if Config.AZURE_OPENAI_KEY else 'Missing')
print('OpenAI Endpoint:', Config.AZURE_OPENAI_ENDPOINT or 'Missing')

# Check Custom Vision
print('Custom Vision Key:', 'Set' if Config.AZURE_CUSTOM_VISION_KEY else 'Missing')
print('Custom Vision Project:', Config.AZURE_CUSTOM_VISION_PROJECT_ID or 'Missing')
"
```

---

## Troubleshooting

### "Azure OpenAI client not initialized"
- Check `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` are set
- Ensure your OpenAI resource is in a region that supports GPT-4o

### "Custom Vision API error"
- Verify the prediction endpoint (not training endpoint)
- Check project ID is correct (GUID format)
- Ensure model is published to the iteration name specified

### "Model deployment not found"
- Confirm deployment name matches `AZURE_OPENAI_DEPLOYMENT`
- Wait a few minutes after creating deployment

---

## Next Steps

1. ✅ Configure all required Azure services
2. ✅ Update your `.env` file with credentials
3. 🔄 Train Custom Vision with spectrogram samples
4. 🚀 Start the Flask app and test AI analysis
5. 📡 Deploy ESP32 nodes with spectrogram firmware

For more information, see:
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Custom Vision Documentation](https://learn.microsoft.com/en-us/azure/ai-services/custom-vision-service/)
- [Forest Guardian README](../README.md)
