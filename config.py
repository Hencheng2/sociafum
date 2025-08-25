# config.py

import os

# --- Flask Secret Key ---
# A strong secret key is crucial for session security.
# It's recommended to load this from an environment variable in production.
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', '09da35833ef9cb699888f08d66a0cfb827fb10e53f6c1549')

# --- Gemini API Key ---
# Your API key for Google Gemini. Keep this secure.
# If you are deploying, consider using environment variables for this.
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', "AIzaSyAnuXwyHYkpuLtxM5x9LTC12ER8ajjttxU")

# --- Firebase Admin SDK Credentials Path ---
# Path to your Firebase service account key JSON file.
# Make sure firebase_admin_key.json is uploaded to your project directory.
FIREBASE_ADMIN_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "firebase_admin_key.json")

# --- Firebase Client-Side Configuration ---
# This configuration is typically used for client-side Firebase SDKs (e.g., in JavaScript).
FIREBASE_CLIENT_CONFIG = {
    "apiKey": os.getenv('FIREBASE_API_KEY', "AIzaSyDU9AsIqG2yCkOtl_RCNvhxayVuT4tjkY0"),
    "authDomain": "henley-23.firebaseapp.com",
    "projectId": "henley-23",
    "storageBucket": "henley-23.firebasestorage.app",
    "messagingSenderId": "406631846317",
    "appId": "1:406631846317:web:ee9165b6afbb1b61cd9124",
    "measurementId": "G-7RE2TW0JQ9"
}

# --- Canvas App ID (if applicable) ---
# An identifier for your application within a Canvas environment.
CANVAS_APP_ID = os.getenv('CANVAS_APP_ID', "your_family_tree_app")

# --- Admin User Credentials ---
# Hardcoded admin username and password hash for initial setup.
# In a real-world scenario, you'd manage admin accounts more securely.
ADMIN_USERNAME = "Henry"
# IMPORTANT: This password is hashed in app.py during registration,
# but for initial setup or direct DB insertion, use this raw password.
# The system will check against the hash stored in the DB.
ADMIN_PASSWORD_RAW = "Dec@2003"
