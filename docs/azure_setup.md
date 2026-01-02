# Azure Setup Guide

## Overview
Forest Guardian uses these Azure services (free tier where possible):
- Azure IoT Hub
- Azure Functions
- Azure Cosmos DB
- Azure Machine Learning
- Azure OpenAI Service
- Azure Communication Services (optional)

---

## 1. Resource Group
```sh
az group create --name forest-guardian-rg --location canadacentral
```

---

## 2. Azure IoT Hub
```sh
az iot hub create --name forest-guardian-hub --resource-group forest-guardian-rg --sku F1
```
- Get connection string:
```sh
az iot hub connection-string show --hub-name forest-guardian-hub
```

---

## 3. Azure Functions
```sh
az storage account create --name forestguardianstore --resource-group forest-guardian-rg --sku Standard_LRS
az functionapp create --name forest-guardian-func --resource-group forest-guardian-rg --storage-account forestguardianstore --consumption-plan-location canadacentral --runtime python --runtime-version 3.11 --functions-version 4
```

---

## 4. Azure Cosmos DB
```sh
az cosmosdb create --name forest-guardian-cosmos --resource-group forest-guardian-rg --kind GlobalDocumentDB --locations regionName=canadacentral
az cosmosdb sql database create --account-name forest-guardian-cosmos --resource-group forest-guardian-rg --name forestguardian
az cosmosdb sql container create --account-name forest-guardian-cosmos --resource-group forest-guardian-rg --database-name forestguardian --name alerts --partition-key-path /node_id
```

---

## 5. Azure Machine Learning
```sh
az ml workspace create --name forest-guardian-ml --resource-group forest-guardian-rg
```
- Use Azure ML Studio to train models or run `ml/scripts/azure_ml_train.py`

---

## 6. Azure OpenAI Service
- Go to [Azure OpenAI](https://portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI)
- Create resource, deploy GPT-4o model
- Note endpoint and key

---

## 7. Azure Communication Services (optional)
```sh
az communication create --name forest-guardian-comm --resource-group forest-guardian-rg --data-location canada
```
- Get connection string for SMS

---

## Environment Variables
Set the following in your `.env` or Azure Functions settings:
- `AZURE_IOTHUB_CONN_STR`
- `AZURE_OPENAI_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `COSMOS_ENDPOINT`
- `COSMOS_KEY`
- `AZURE_COMMUNICATION_CONN_STR`

---

## Deploy Azure Functions
```sh
cd azure
func azure functionapp publish forest-guardian-func
```

---

## Done!
You can now connect your Raspberry Pi hub to Azure and start receiving alerts.
