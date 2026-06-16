import json
import os
from http.server import BaseHTTPRequestHandler

# In-memory storage (for production, use Vercel KV, Redis, or database)
SUBSCRIPTIONS_FILE = '/tmp/push_subscriptions.json'

def load_subscriptions():
    if os.path.exists(SUBSCRIPTIONS_FILE):
        try:
            with open(SUBSCRIPTIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_subscriptions(subs):
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subs, f)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        subs = load_subscriptions()
        
        # Check for duplicate
        endpoint = data.get('endpoint')
        if endpoint and not any(s.get('endpoint') == endpoint for s in subs):
            subs.append(data)
            save_subscriptions(subs)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True, 'count': len(subs)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()