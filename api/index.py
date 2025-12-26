import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import app

from vercel_wsgi import handle_wsgi_event

def handler(event, context):
    return handle_wsgi_event(app, event, context)
