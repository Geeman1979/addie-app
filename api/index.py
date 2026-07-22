import sys
import os

# Ensure the project root is on the path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Change to root directory so relative paths work
os.chdir(_root)

from app import create_app

flask_app = create_app()
app = flask_app
