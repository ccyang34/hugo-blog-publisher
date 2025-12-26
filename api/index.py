"""
Vercel Serverless Function Entry Point for Flask App
"""
import sys
import os

# Set up paths for importing backend module
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_path not in sys.path:
    sys.path.insert(0, base_path)

# Import the Flask app
from backend.app import app

# Vercel expects a variable named 'app' or 'application' for WSGI apps
# The Flask app instance is already named 'app', so Vercel will automatically detect it