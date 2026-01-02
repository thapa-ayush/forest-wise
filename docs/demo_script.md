# Forest Guardian - 3-Minute Demo Script

## Overview
This script guides you through a 3-minute live demo of Forest Guardian for Microsoft Imagine Cup 2026 judges.

---

## Preparation (before demo)
1. Ensure Raspberry Pi hub is running and dashboard is accessible
2. Ensure at least one Guardian node is powered on (or use simulation mode)
3. Open dashboard in browser: http://localhost:5000
4. Log in as admin/admin123

---

## Demo Flow

### 0:00 - Introduction (30 seconds)
> "Forest Guardian is an AI-powered illegal logging detection system. It uses TinyML on ESP32 microcontrollers to detect chainsaw sounds in real time, transmits alerts via LoRa, and notifies forest rangers through a secure web dashboard."

### 0:30 - Dashboard Tour (30 seconds)
> "Here's our ranger dashboard. We can see active nodes, recent alerts, and system status. The map shows node locations and alerts in real time."

- Show Dashboard, Map, Nodes, Alerts pages

### 1:00 - Simulate Alert (30 seconds)
> "Let me simulate a chainsaw detection. Our edge AI model runs directly on the ESP32, so it works offline in the forest."

- Click "Simulate Alert" button
- Show alert appearing on dashboard and map
- Show alert sound notification

### 1:30 - AI Analysis (30 seconds)
> "Every alert is analyzed by Azure OpenAI to assess threat level and provide context for rangers."

- Show AI-generated analysis in alert details
- Show AI Reports page

### 2:00 - Azure Integration (30 seconds)
> "We use Azure IoT Hub for telemetry, Cosmos DB for storage, Azure Functions for serverless processing, Azure ML for training, and Azure OpenAI for smart analysis—meeting the Imagine Cup requirement of two Microsoft AI services."

- Show Azure portal (optional, or just mention)

### 2:30 - Security & Admin (15 seconds)
> "Our system includes secure ranger authentication and admin controls."

- Show Admin > Users page

### 2:45 - Impact (15 seconds)
> "Forest Guardian helps protect Canada's forests from illegal logging, supporting conservation and climate action."

---

## Q&A
Be prepared to answer:
- How does the ML model work?
- What is the range of LoRa?
- How is the system powered?
- What Azure services are used?

---

## Backup Plan
- If hardware fails, use Simulate Alert/Heartbeat buttons
- If network fails, dashboard still works locally

---

## License
MIT
