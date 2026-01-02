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
    AZURE_IOTHUB_CONN_STR = os.getenv('AZURE_IOTHUB_CONN_STR')
    AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_COSMOS_KEY = os.getenv('AZURE_COSMOS_KEY')
    AZURE_COSMOS_ENDPOINT = os.getenv('AZURE_COSMOS_ENDPOINT')
    AZURE_COMMUNICATION_CONN_STR = os.getenv('AZURE_COMMUNICATION_CONN_STR')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF token
    RATELIMIT_DEFAULT = '50 per 15 minutes'
    RATELIMIT_STORAGE_URI = 'memory://'
