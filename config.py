import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Keep your existing secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or '09da35833ef9cb699888f08d66a0cfb827fb10e53f6c1549'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'sociafam.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
    
    # Admin credentials (keep these)
    ADMIN_USERNAME = 'Henry'
    ADMIN_PASS = 'Dec@2003'
    
    # AI configuration (optional - keep if you need it)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or "AIzaSyAnuXwyHYkpuLtxM5x9LTC12ER8ajjttxU"
    AI_USER_PASSWORD = "Dec@2003"
    
    # Canvas App ID (optional - keep if you need it)
    CANVAS_APP_ID = "your_family_tree_app"
    
    # Remove these Firebase-related lines completely:
    # FIREBASE_ADMIN_CREDENTIALS_PATH = "firebase_admin_key.json"
    # FIREBASE_CLIENT_CONFIG = { ... }
