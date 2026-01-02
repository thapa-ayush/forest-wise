# Azure AI Integration Guide for Forest Guardian

## Required Azure Services for Imagine Cup

This guide walks through setting up the Azure AI services needed for your Imagine Cup submission.

## 1. Azure IoT Hub Setup

### Create IoT Hub
```bash
# Using Azure CLI
az iot hub create \
  --name forest-guardian-hub \
  --resource-group forest-guardian-rg \
  --sku S1 \
  --location canadacentral
```

### Register Device
```bash
az iot hub device-identity create \
  --device-id GUARDIAN_001 \
  --hub-name forest-guardian-hub
```

### Get Connection String
```bash
az iot hub device-identity connection-string show \
  --device-id GUARDIAN_001 \
  --hub-name forest-guardian-hub
```

### Message Format from Device
```json
{
  "device_id": "GUARDIAN_001",
  "message_type": "alert",
  "confidence": 0.75,
  "location": {
    "lat": 49.2827,
    "lon": -123.1207
  },
  "battery": 85,
  "timestamp": "2025-01-20T15:30:00Z"
}
```

## 2. Azure Custom Vision Setup

### Create Custom Vision Resource
1. Go to Azure Portal → Create Resource → AI + ML → Custom Vision
2. Choose "Both training and prediction"
3. Select your resource group

### Train Chainsaw Detection Model
1. Create a new project (Classification, Multiclass)
2. Upload training images:
   - **Positive samples**: Spectrograms of chainsaw sounds
   - **Negative samples**: Forest ambient sounds, birds, wind, rain

3. Generate spectrograms from audio:
```python
# training_data/generate_spectrograms.py
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

def audio_to_spectrogram(audio_file, output_image):
    y, sr = librosa.load(audio_file, sr=16000)
    
    # Create mel spectrogram
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    S_dB = librosa.power_to_db(S, ref=np.max)
    
    # Save as image
    plt.figure(figsize=(4, 4))
    librosa.display.specshow(S_dB, sr=sr, x_axis='time', y_axis='mel')
    plt.axis('off')
    plt.savefig(output_image, bbox_inches='tight', pad_inches=0)
    plt.close()
```

4. Train the model (Quick Train or Advanced Training)
5. Publish the model and get the Prediction URL

### Using Custom Vision API
```cpp
// gateway/azure_custom_vision.cpp
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* CUSTOM_VISION_URL = "https://YOUR-REGION.api.cognitive.microsoft.com/customvision/v3.0/Prediction/YOUR-PROJECT-ID/classify/iterations/YOUR-ITERATION/image";
const char* PREDICTION_KEY = "YOUR-PREDICTION-KEY";

float verify_with_azure(uint8_t* imageData, size_t imageLen) {
    HTTPClient http;
    http.begin(CUSTOM_VISION_URL);
    http.addHeader("Content-Type", "application/octet-stream");
    http.addHeader("Prediction-Key", PREDICTION_KEY);
    
    int httpCode = http.POST(imageData, imageLen);
    
    if (httpCode == HTTP_CODE_OK) {
        String response = http.getString();
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, response);
        
        // Get chainsaw probability
        JsonArray predictions = doc["predictions"].as<JsonArray>();
        for (JsonObject pred : predictions) {
            if (String(pred["tagName"].as<const char*>()) == "chainsaw") {
                return pred["probability"].as<float>();
            }
        }
    }
    return 0.0f;
}
```

## 3. Azure Maps Setup

### Create Azure Maps Account
```bash
az maps account create \
  --name forest-guardian-maps \
  --resource-group forest-guardian-rg \
  --sku S0
```

### Get Maps Key
```bash
az maps account keys list \
  --name forest-guardian-maps \
  --resource-group forest-guardian-rg
```

### Web Dashboard with Azure Maps
```html
<!-- dashboard/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Forest Guardian Dashboard</title>
    <link rel="stylesheet" href="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.css">
    <script src="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.js"></script>
</head>
<body>
    <div id="map" style="width:100%;height:600px;"></div>
    <script>
        const map = new atlas.Map('map', {
            center: [-123.1207, 49.2827],
            zoom: 10,
            authOptions: {
                authType: 'subscriptionKey',
                subscriptionKey: 'YOUR_AZURE_MAPS_KEY'
            }
        });

        // Add detection markers
        function addDetectionMarker(lat, lon, confidence) {
            const marker = new atlas.HtmlMarker({
                position: [lon, lat],
                color: confidence > 0.7 ? 'red' : 'orange',
                text: '🌲'
            });
            map.markers.add(marker);
        }

        // Connect to IoT Hub via SignalR for real-time updates
        // See Azure Function for SignalR integration
    </script>
</body>
</html>
```

## 4. Azure Functions for Real-Time Processing

### IoT Hub Trigger Function
```javascript
// functions/ProcessDetection/index.js
const { CosmosClient } = require("@azure/cosmos");

module.exports = async function (context, IoTHubMessages) {
    for (const message of IoTHubMessages) {
        context.log('Detection received:', JSON.stringify(message));
        
        if (message.message_type === 'alert') {
            // Store in Cosmos DB
            await storeDetection(message);
            
            // Send notification via SignalR
            context.bindings.signalRMessages = [{
                target: "newDetection",
                arguments: [message]
            }];
            
            // Optional: Trigger Azure Custom Vision verification
            // await verifyWithCustomVision(message);
        }
    }
};
```

## 5. Complete Azure Architecture

```
IoT Hub → Event Grid → Azure Functions → Cosmos DB
                                      ↓
                              Custom Vision API
                                      ↓
                              SignalR Service → Web Dashboard (Azure Maps)
```

## Cost Estimation (Free Tier Available)

| Service | Free Tier | Paid Estimate |
|---------|-----------|---------------|
| IoT Hub | 8,000 msgs/day | $25/month (S1) |
| Custom Vision | 2 projects, 10K predictions | $2/1000 predictions |
| Azure Maps | 5,000 transactions | $0.50/1000 |
| Functions | 1M executions | $0.20/million |
| **Total** | **Free for development** | ~$30-50/month |

## Environment Variables for Gateway

```bash
# .env file for gateway device
AZURE_IOT_HUB_CONNECTION_STRING="HostName=forest-guardian-hub.azure-devices.net;DeviceId=GUARDIAN_001;SharedAccessKey=xxx"
AZURE_CUSTOM_VISION_URL="https://canadacentral.api.cognitive.microsoft.com/customvision/v3.0/..."
AZURE_CUSTOM_VISION_KEY="your-prediction-key"
AZURE_MAPS_KEY="your-maps-key"
```

## Testing Azure Integration

### 1. Test IoT Hub Connection
```bash
# Send test message using Azure CLI
az iot device send-d2c-message \
  --device-id GUARDIAN_001 \
  --hub-name forest-guardian-hub \
  --data '{"message_type":"test","confidence":0.85}'
```

### 2. Monitor IoT Hub Messages
```bash
az iot hub monitor-events \
  --hub-name forest-guardian-hub \
  --device-id GUARDIAN_001
```

### 3. Test Custom Vision API
```bash
curl -X POST "https://YOUR-ENDPOINT/customvision/v3.0/Prediction/..." \
  -H "Prediction-Key: YOUR-KEY" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@test_spectrogram.png"
```

## Imagine Cup Submission Tips

1. **Demo Video**: Show end-to-end flow from sound → detection → Azure → dashboard
2. **Architecture Diagram**: Include the diagram showing all Azure services
3. **Impact Metrics**: Calculate potential hectares of forest protected
4. **Scalability**: Explain how LoRa mesh + Azure scales to large forests
5. **Cost Efficiency**: Show Azure cost estimates for different scales
