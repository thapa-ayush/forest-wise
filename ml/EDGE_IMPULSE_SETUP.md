# Edge Impulse Setup for Forest Guardian

## Why Edge Impulse?
- **Free** for developers
- **Purpose-built** for embedded ML (ESP32-S3 supported)
- **Higher accuracy** than hand-crafted FFT rules
- **Professional ML pipeline** - impressive for Imagine Cup judges

## Step 1: Create Edge Impulse Account

1. Go to: https://edgeimpulse.com/
2. Click **"Get started free"**
3. Sign up (use student email for extra benefits)

## Step 2: Create New Project

1. Click **"Create new project"**
2. Name: `Forest Guardian Chainsaw Detection`
3. Select: **Audio** as project type

## Step 3: Upload Your Training Data

### Option A: Use Edge Impulse Uploader (Recommended)

1. Install the CLI:
   ```bash
   npm install -g edge-impulse-cli
   ```

2. Login:
   ```bash
   edge-impulse-uploader --clean
   ```

3. Upload chainsaw samples:
   ```bash
   cd f:\forest_guardian\ml\data\chainsaw
   edge-impulse-uploader --category training --label chainsaw *.mp3
   ```

4. Upload forest/ambient samples:
   ```bash
   cd f:\forest_guardian\ml\data\forest
   edge-impulse-uploader --category training --label noise *.mp3
   ```

### Option B: Manual Upload (No Node.js)

1. In Edge Impulse Studio, go to **Data acquisition**
2. Click **Upload data**
3. Select files from `ml\data\chainsaw\` → Label as **"chainsaw"**
4. Select files from `ml\data\forest\` → Label as **"noise"**

## Step 4: Create Impulse (ML Pipeline)

1. Go to **Create impulse**
2. Add processing block: **Audio (MFCC)**
   - Window size: 1000ms
   - Window increase: 500ms
   - Frequency: 16000 Hz
3. Add learning block: **Classification**
4. Click **Save Impulse**

## Step 5: Generate Features

1. Go to **MFCC** in left menu
2. Click **Generate features**
3. Wait for processing (~2-5 minutes)

## Step 6: Train the Model

1. Go to **Classifier**
2. Settings:
   - Number of training cycles: **100**
   - Learning rate: **0.005**
   - Minimum confidence: **0.6**
3. Click **Start training**
4. Wait for training (~5-10 minutes)

Expected results:
- **Accuracy: 90-95%**
- **Confusion matrix**: Low false positives

## Step 7: Test the Model

1. Go to **Model testing**
2. Click **Classify all**
3. Review results - should be >90% accurate

## Step 8: Deploy to ESP32-S3

1. Go to **Deployment**
2. Select **Arduino library**
3. Select optimization: **Quantized (int8)** - smaller, faster
4. Click **Build**
5. Download the `.zip` file

## Step 9: Install in Arduino IDE

1. Open Arduino IDE
2. **Sketch → Include Library → Add .ZIP Library**
3. Select the downloaded `ei-forest-guardian-chainsaw-detection-arduino-*.zip`

## Step 10: Update Firmware

Replace the FFT-based `ml_inference.cpp` with Edge Impulse version.
See `firmware/guardian_node/ml_inference_edgeimpulse.cpp` for template.

---

## Your Training Data Summary

| Category | Samples | Source |
|----------|---------|--------|
| **Chainsaw** | 56 | Freesound.org |
| **Forest/Noise** | 88 | Freesound.org |
| **Total** | 144 | Ready for upload! |

This is a solid dataset for training. Edge Impulse will automatically:
- Split into training/test sets (80/20)
- Augment data for robustness
- Optimize for ESP32-S3

---

## Estimated Timeline

| Step | Time |
|------|------|
| Account setup | 2 min |
| Data upload | 10-15 min |
| Create impulse | 2 min |
| Generate features | 3-5 min |
| Train model | 5-10 min |
| Test & deploy | 5 min |
| **Total** | **~30-45 minutes** |
