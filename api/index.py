import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import app

from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    from backend.app import app as flask_app
    with flask_app.test_request_context():
        return flask_app.full_dispatch_request()

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_proxy(path):
    from backend.app import app as flask_app
    with flask_app.test_request_context():
        return flask_app.full_dispatch_request()

@app.route('/static/<path:path>')
def static_proxy(path):
    from backend.app import app as flask_app
    return flask_app.send_static_file(path)

if __name__ == '__main__':
    app.run()
