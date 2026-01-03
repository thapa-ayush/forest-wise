# config.py - Forest Guardian Hub
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///forest_guardian.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Azure IoT Hub
    AZURE_IOTHUB_CONN_STR = os.getenv('AZURE_IOTHUB_CONN_STR')
    
    # Azure OpenAI (GPT-4o Vision for spectrogram analysis)
    AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')
    
    # Azure Custom Vision (Alternative AI for spectrogram classification)
    AZURE_CUSTOM_VISION_ENDPOINT = os.getenv('AZURE_CUSTOM_VISION_ENDPOINT')
    AZURE_CUSTOM_VISION_KEY = os.getenv('AZURE_CUSTOM_VISION_KEY')
    AZURE_CUSTOM_VISION_PROJECT_ID = os.getenv('AZURE_CUSTOM_VISION_PROJECT_ID')
    AZURE_CUSTOM_VISION_ITERATION = os.getenv('AZURE_CUSTOM_VISION_ITERATION', 'production')
    
    # AI Mode: 'gpt4o', 'custom_vision', or 'auto'
    DEFAULT_AI_MODE = os.getenv('DEFAULT_AI_MODE', 'gpt4o')
    
    # Azure Cosmos DB
    AZURE_COSMOS_KEY = os.getenv('AZURE_COSMOS_KEY')
    AZURE_COSMOS_ENDPOINT = os.getenv('AZURE_COSMOS_ENDPOINT')
    
    # Azure Communication Services (SMS alerts)
    AZURE_COMMUNICATION_CONN_STR = os.getenv('AZURE_COMMUNICATION_CONN_STR')
    
    # Spectrogram settings
    SPECTROGRAM_DIR = os.getenv('SPECTROGRAM_DIR', 'static/spectrograms')
    AUTO_ANALYZE_SPECTROGRAMS = os.getenv('AUTO_ANALYZE_SPECTROGRAMS', 'true').lower() == 'true'
    
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF token
    RATELIMIT_DEFAULT = '50 per 15 minutes'
    RATELIMIT_STORAGE_URI = 'memory://'
