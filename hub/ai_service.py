# ai_service.py - Forest Guardian Hub
import os
import openai
from config import Config

openai.api_key = Config.AZURE_OPENAI_KEY
openai.api_base = Config.AZURE_OPENAI_ENDPOINT
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

def generate_daily_report(alerts: list) -> str:
    prompt = f"""Summarize the last 24 hours of forest monitoring alerts:
    {alerts}
    Include total alerts, risk areas, and recommendations."""
    response = openai.ChatCompletion.create(
        engine="gpt-4o",
        messages=[{"role": "system", "content": "You are a concise forest monitoring assistant."},
                  {"role": "user", "content": prompt}],
        max_tokens=400
    )
    return response.choices[0].message['content']

def generate_sms_text(alert: dict) -> str:
    return f"ALERT: Chainsaw detected near ({alert.get('lat', 0)}, {alert.get('lon', 0)}). Confidence: {alert.get('confidence', 0)}%."
