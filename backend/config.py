import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/knowledge_system')
    JWT_EXPIRATION_HOURS = 24
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size