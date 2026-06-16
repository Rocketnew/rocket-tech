"""Vercel serverless entry point — handles all /api/* routes."""
import sys, os, json, hashlib, hmac, base64, time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.shared import json_response, read_config, write_config, get_build_stats, GITHUB_TOKEN, write_github_file

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS_HASH = os.environ.get('ADMIN_PASS_HASH', '')
VERCEL_DEPLOY_HOOK = os.environ.get('VERCEL_DEPLOY_HOOK', '')

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
        if len(parts) != 2: return None
        payload_b64, sig = parts
        expected = hmac.new(b"rupeewa-secret", payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected): return None
        payload = json.loads(base64.b64decode(payload_b64).decode())
        if payload.get('exp', 0) < time.time(): return None
        return payload.get('user')
    except: return None

def _auth_required(self):
    auth = self.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return _verify_token(auth[7:])
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.rstrip('/')
        
        # /api/health
        if path == '/api/health':
            json_response(self, {"status": "ok", "service": "Rupeewa Admin", "version": "3.0"})
            return
        
        # /api/debug
        if path == '/api/debug':
            token = os.environ.get('GITHUB_TOKEN', '')
            json_response(self, {
                "has_token": bool(token),
                "token_prefix": token[:8] + '...' if token else '',
                "token_len": len(token),
                "python_version": sys.version,
                "cwd": os.getcwd(),
            })
            return
        
        # /api/login (GET = check auth)
        if path == '/api/login':
            user = _auth_required(self)
            if user:
                json_response(self, {"authenticated": True, "username": user})
            else:
                json_response(self, {"authenticated": False})
            return
        
        # /api/dashboard
        if path == '/api/dashboard':
            try:
                config, _ = read_config()
                stats = get_build_stats()
                stats['sources'] = 6
                stats['featured'] = len(config.get('featured_articles', []))
                json_response(self, stats)
            except Exception as e:
                json_response(self, {"error": str(e)}, 500)
            return
        
        # /api/subscribers
        if path == '/api/subscribers':
            config, _ = read_config()
            subs = config.get('subscribers', [])
            recent = sorted(subs, key=lambda x: x.get('subscribed_at', ''), reverse=True)[:100]
            json_response(self, {"subscribers": recent, "total": len(subs)})
            return
        
        # /api/seo
        if path == '/api/seo':
            config, _ = read_config()
            seo = {k: config.get(k, '') for k in ['site_name','site_description','site_keywords','og_title','og_description','twitter_handle','google_analytics_id','custom_head_html']}
            json_response(self, seo)
            return
        
        # /api/seo/save
        if path == '/api/seo/save':
            json_response(self, {"error": "Use POST"}, 405)
            return
        
        json_response(self, {"error": "Not found", "path": path}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path.rstrip('/')
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length else ''
        
        # /api/login (POST = authenticate)
        if path == '/api/login':
            params = parse_qs(body)
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            expected_hash = ADMIN_PASS_HASH or _simple_hash('admin123')
            if username == ADMIN_USER and _simple_hash(password) == expected_hash:
                token = _make_token(username)
                json_response(self, {"access_token": token, "token_type": "bearer", "username": username})
            else:
                json_response(self, {"error": "Invalid credentials"}, 401)
            return
        
        # /api/seo/save (POST = save settings)
        if path == '/api/seo/save':
            try:
                updates = json.loads(body) if body else {}
                config, sha = read_config()
                for key in ['site_name','site_description','site_keywords','og_title','og_description','twitter_handle','google_analytics_id','custom_head_html']:
                    if key in updates:
                        config[key] = updates[key]
                if write_config(config, sha):
                    json_response(self, {"status": "saved"})
                else:
                    json_response(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                json_response(self, {"error": str(e)}, 500)
            return
        
        # /api/subscribers (POST = subscribe)
        if path == '/api/subscribers' or path == '/api/subscribe':
            try:
                data = json.loads(body) if body else {}
                email = data.get('email', '').strip().lower()
                if not email or '@' not in email:
                    json_response(self, {"error": "Invalid email"}, 400)
                    return
                config, sha = read_config()
                subs = config.get('subscribers', [])
                if any(s.get('email') == email for s in subs):
                    json_response(self, {"status": "exists"})
                    return
                subs.append({"email": email, "subscribed_at": time.strftime('%Y-%m-%dT%H:%M:%S')})
                config['subscribers'] = subs
                if write_config(config, sha):
                    json_response(self, {"status": "subscribed"})
                else:
                    json_response(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                json_response(self, {"error": str(e)}, 500)
            return
        
        # /api/build (POST = trigger build)
        if path == '/api/build':
            import requests
            if VERCEL_DEPLOY_HOOK:
                try:
                    r = requests.post(VERCEL_DEPLOY_HOOK)
                    json_response(self, {"status": "triggered", "hook_status": r.status_code})
                except Exception as e:
                    json_response(self, {"error": str(e)}, 500)
            else:
                json_response(self, {"status": "no_hook", "message": "No Vercel deploy hook configured"})
            return
        
        json_response(self, {"error": "Not found", "path": path}, 404)
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()