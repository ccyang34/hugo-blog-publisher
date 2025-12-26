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

# Vercel handler function
def handler(request):
    """Vercel handler that proxies requests to the Flask app"""
    try:
        # Build the WSGI environment
        environ = {
            'REQUEST_METHOD': request.method,
            'PATH_INFO': request.path,
            'QUERY_STRING': request.query_string.decode('utf-8') if request.query_string else '',
            'CONTENT_TYPE': request.headers.get('Content-Type', ''),
            'CONTENT_LENGTH': str(len(request.get_data())),
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': request.headers.get('X-Forwarded-Proto', 'http'),
            'wsgi.input': BytesIO(request.get_data()),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': True,
        }

        # Add HTTP headers to the environment
        for key, value in request.headers.items():
            header_name = 'HTTP_' + key.upper().replace('-', '_')
            environ[header_name] = value

        # Create a response container
        response_data = []
        status_code = None
        headers = []

        def start_response(status, response_headers):
            nonlocal status_code, headers
            status_code = status
            headers = response_headers
            return response_data.append

        # Call the Flask app WSGI interface
        app(environ, start_response)

        # Convert to Vercel response format
        status_code_num = int(status_code.split()[0])
        headers_dict = dict(headers)

        # Ensure CORS headers
        headers_dict.setdefault('Access-Control-Allow-Origin', '*')
        headers_dict.setdefault('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        headers_dict.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization')

        return {
            'statusCode': status_code_num,
            'headers': headers_dict,
            'body': b''.join(response_data)
        }
    except Exception as e:
        # Return detailed error for debugging
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'text/plain',
                'Access-Control-Allow-Origin': '*'
            },
            'body': f"Error in handler: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        }

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
