"""
Azure Function: AlertProcessor
Processes incoming alerts from IoT Hub, analyzes with Azure OpenAI, stores in Cosmos DB.
"""
import os
import json
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
import openai

COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
COSMOS_DB = 'forestguardian'
COSMOS_CONTAINER = 'alerts'

OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')

openai.api_key = OPENAI_KEY
openai.api_base = OPENAI_ENDPOINT
openai.api_type = 'azure'
openai.api_version = '2024-02-01'

def analyze_alert(alert: dict) -> str:
    prompt = f"""You are a forest monitoring AI. An alert was received:
    - Confidence: {alert.get('confidence', 0)}%
    - Location: {alert.get('lat', 0)}, {alert.get('lon', 0)}
    - Battery: {alert.get('battery', 0)}%
    - Node: {alert.get('node_id', '')}
    Provide a brief analysis and threat level (Low/Medium/High/Critical)."""
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[{"role": "system", "content": "You are a concise forest monitoring assistant."},
                  {"role": "user", "content": prompt}],
        max_tokens=200
    )
    return response.choices[0].message['content']

def main(event: func.EventHubEvent):
    logging.info('AlertProcessor triggered.')
    body = event.get_body().decode('utf-8')
    alert = json.loads(body)
    if alert.get('type') != 'alert':
        return
    if alert.get('confidence', 0) < 70:
        return
    analysis = analyze_alert(alert)
    alert['ai_analysis'] = analysis
    # Store in Cosmos DB
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    db = client.get_database_client(COSMOS_DB)
    container = db.get_container_client(COSMOS_CONTAINER)
    container.upsert_item(alert)
    logging.info(f'Stored alert: {alert}')
