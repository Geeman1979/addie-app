import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

flask_app = create_app()

# Vercel expects a WSGI app
app = flask_app
