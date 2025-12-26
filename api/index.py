import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from backend.app import app as flask_app

# Vercel expects a function named 'handler' that takes a request
# and returns a response dictionary

def handler(request):
    """Vercel handler for the Flask application"""
    try:
        # Convert Vercel request to WSGI environment
        environ = {
            'REQUEST_METHOD': request.method,
            'PATH_INFO': request.path,
            'QUERY_STRING': request.query_string.decode('utf-8') if request.query_string else '',
            'CONTENT_TYPE': request.headers.get('Content-Type', ''),
            'HTTP_ACCEPT': request.headers.get('Accept', '*/*'),
            'HTTP_ACCEPT_ENCODING': request.headers.get('Accept-Encoding', ''),
            'HTTP_ACCEPT_LANGUAGE': request.headers.get('Accept-Language', ''),
            'HTTP_HOST': request.headers.get('Host', ''),
            'HTTP_USER_AGENT': request.headers.get('User-Agent', ''),
            'HTTP_X_FORWARDED_FOR': request.headers.get('X-Forwarded-For', ''),
            'HTTP_X_FORWARDED_PROTO': request.headers.get('X-Forwarded-Proto', ''),
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': request.headers.get('X-Forwarded-Proto', 'http'),
            'wsgi.input': request.body,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': True,
        }
        
        # Handle content length
        content_length = len(request.body)
        if content_length > 0:
            environ['CONTENT_LENGTH'] = str(content_length)
        
        # Add all request headers to environ
        for key, value in request.headers.items():
            header_name = 'HTTP_' + key.upper().replace('-', '_')
            environ[header_name] = value
        
        # Collect response data
        response_data = []
        status_code = None
        response_headers = []
        
        def start_response(status, headers):
            nonlocal status_code, response_headers
            status_code = status
            response_headers = headers
            return response_data.append
        
        # Call the Flask app
        flask_app(environ, start_response)
        
        # Convert response to Vercel format
        status_code_num = int(status_code.split()[0])
        headers_dict = {}
        for header_name, header_value in response_headers:
            headers_dict[header_name] = header_value
        
        # Ensure CORS headers are present
        headers_dict.setdefault('Access-Control-Allow-Origin', '*')
        headers_dict.setdefault('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        headers_dict.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        
        return {
            'statusCode': status_code_num,
            'headers': headers_dict,
            'body': b''.join(response_data)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': f'{{"error": "{str(e)}"}}'
        }

# For local development
if __name__ == '__main__':
    flask_app.run(debug=True, host='0.0.0.0', port=5000)
