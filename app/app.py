from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    env = os.environ.get('APP_ENV', 'development')
    return f"<h1>Hello from Python App!</h1><p>Environment: {env}</p>"

@app.route('/health')
def health():
    return {"status": "healthy"}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)