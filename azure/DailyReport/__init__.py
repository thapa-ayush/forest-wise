"""
Azure Function: DailyReport
Generates daily summary report using Azure OpenAI and stores in Cosmos DB.
"""
import os
import json
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
from datetime import datetime, timedelta
import openai

COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
COSMOS_DB = 'forestguardian'
COSMOS_CONTAINER_ALERTS = 'alerts'
COSMOS_CONTAINER_REPORTS = 'reports'

OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')

openai.api_key = OPENAI_KEY
openai.api_base = OPENAI_ENDPOINT
openai.api_type = 'azure'
openai.api_version = '2024-02-01'

def generate_report(alerts: list) -> str:
    prompt = f"""Summarize the last 24 hours of forest monitoring alerts:
    {json.dumps(alerts, default=str)}
    Include total alerts, risk areas, and recommendations."""
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[{"role": "system", "content": "You are a concise forest monitoring assistant."},
                  {"role": "user", "content": prompt}],
        max_tokens=400
    )
    return response.choices[0].message['content']

def main(timer: func.TimerRequest):
    logging.info('DailyReport triggered.')
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    db = client.get_database_client(COSMOS_DB)
    alerts_container = db.get_container_client(COSMOS_CONTAINER_ALERTS)
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    query = f"SELECT * FROM c WHERE c.timestamp > '{yesterday}'"
    alerts = list(alerts_container.query_items(query, enable_cross_partition_query=True))
    report = generate_report(alerts)
    reports_container = db.get_container_client(COSMOS_CONTAINER_REPORTS)
    reports_container.upsert_item({'id': datetime.utcnow().strftime('%Y-%m-%d'), 'report': report})
    logging.info('Daily report generated.')
