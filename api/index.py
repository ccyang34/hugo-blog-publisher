import sys
import os
import traceback
import pkgutil
from io import BytesIO

# Add debugging information
print(f"DEBUG: Current directory: {os.getcwd()}")
print(f"DEBUG: Python path: {sys.path}")
print(f"DEBUG: Current file path: {os.path.abspath(__file__)}")

# List all installed packages
try:
    installed_packages = [pkg for pkg in pkgutil.iter_modules()]
    print(f"DEBUG: Installed packages: {[pkg.name for pkg in installed_packages[:20]]}... (total: {len(installed_packages)})")
except Exception as e:
    print(f"DEBUG: Error listing packages: {e}")

# Try to import flask directly to check if it's installed
try:
    import flask
    print(f"DEBUG: Flask is installed, version: {flask.__version__}")
except ImportError:
    print("DEBUG: Flask is NOT installed")

# Set up paths
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"DEBUG: Base path: {base_path}")
sys.path.insert(0, base_path)

# Import the Flask app directly from the backend
try:
    from backend.app import app
    print("DEBUG: Successfully imported Flask app from backend.app")
except Exception as e:
    print(f"DEBUG: Error importing Flask app: {e}")
    traceback.print_exc()
    raise

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)