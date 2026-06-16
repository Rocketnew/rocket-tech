"""Subscribers API endpoint."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler
from lib.shared import json_response, read_config, write_config

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        config, _ = read_config()
        subs = config.get('subscribers', [])
        recent = sorted(subs, key=lambda x: x.get('subscribed_at', ''), reverse=True)[:100]
        json_response(self, {"subscribers": recent, "total": len(subs)})
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length else '{}'
        data = json.loads(body) if body else {}
        email = data.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            json_response(self, {"error": "Invalid email"}, 400)
            return
        
        config, sha = read_config()
        subs = config.get('subscribers', [])
        
        if any(s.get('email') == email for s in subs):
            json_response(self, {"status": "exists", "message": "Already subscribed"})
            return
        
        import datetime
        subs.append({"email": email, "subscribed_at": datetime.datetime.now().isoformat()})
        config['subscribers'] = subs
        
        if write_config(config, sha):
            json_response(self, {"status": "subscribed", "message": "Welcome!"})
        else:
            json_response(self, {"error": "Failed to save"}, 500)
    
    def do_DELETE(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length else '{}'
        data = json.loads(body) if body else {}
        email = data.get('email', '').strip().lower()
        
        config, sha = read_config()
        config['subscribers'] = [s for s in config.get('subscribers', []) if s.get('email') != email]
        
        if write_config(config, sha):
            json_response(self, {"status": "deleted"})
        else:
            json_response(self, {"error": "Failed to save"}, 500)
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()