"""Admin login endpoint."""
import sys, os, json, hashlib, hmac, base64, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler
from lib.shared import json_response

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS_HASH = os.environ.get('ADMIN_PASS_HASH', '')

def _simple_hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def _make_token(username):
    payload = json.dumps({"user": username, "exp": time.time() + 86400, "iat": time.time()})
    encoded = base64.b64encode(payload.encode()).decode()
    sig = hmac.new(b"rupeewa-secret", encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"

def _verify_token(token):
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected = hmac.new(b"rupeewa-secret", payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.b64decode(payload_b64).decode())
        if payload.get('exp', 0) < time.time():
            return None
        return payload.get('user')
    except:
        return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Check if authenticated
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            user = _verify_token(auth[7:])
            if user:
                json_response(self, {"authenticated": True, "username": user})
                return
        json_response(self, {"authenticated": False}, 200)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length else ''
        import urllib.parse
        params = urllib.parse.parse_qs(body)
        username = params.get('username', [''])[0]
        password = params.get('password', [''])[0]
        
        expected_hash = ADMIN_PASS_HASH or _simple_hash('admin123')
        if username == ADMIN_USER and _simple_hash(password) == expected_hash:
            token = _make_token(username)
            json_response(self, {"access_token": token, "token_type": "bearer", "username": username})
        else:
            json_response(self, {"error": "Invalid credentials"}, 401)
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()