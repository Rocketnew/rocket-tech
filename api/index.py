"""Vercel serverless entry point — handles all /api/* routes.
Security: rate-limited login, JWT-protected endpoints, safety headers."""
import sys, os, json, hashlib, hmac, base64, time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.shared import read_config, write_config, get_build_stats

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS_HASH = os.environ.get('ADMIN_PASS_HASH', '')
VERCEL_DEPLOY_HOOK = os.environ.get('VERCEL_DEPLOY_HOOK', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'rupeewa-secret-change-me')

# ─── RATE LIMITING ───
_login_attempts = defaultdict(list)
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW = 300  # 5 minutes
LOGIN_BLOCK_DURATION = 900  # 15 minutes

def _check_rate_limit(ip):
    now = time.time()
    # Clean old entries
    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > now - LOGIN_WINDOW]
    if len(_login_attempts[ip]) >= LOGIN_MAX_ATTEMPTS:
        # Check if block period has passed
        if _login_attempts[ip] and (now - _login_attempts[ip][0]) < LOGIN_BLOCK_DURATION:
            return False
        # Reset after block period
        _login_attempts[ip] = []
    return True

def _record_attempt(ip):
    _login_attempts[ip].append(time.time())

# ─── PASSWORD VERIFICATION ───
def _verify_password(password, stored_hash):
    if not stored_hash:
        return hashlib.sha256(password.encode()).hexdigest() == 'fake_default'
    try:
        parts = stored_hash.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        _, iters, salt_b64, hash_b64 = parts
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt_b64), int(iters))
        return base64.b64encode(dk).decode() == hash_b64
    except:
        return False

# ─── JWT ───
def _make_token(username):
    payload = json.dumps({"user": username, "exp": time.time() + 86400, "iat": time.time(), "jti": base64.b64encode(os.urandom(12)).decode()})
    encoded = base64.b64encode(payload.encode()).decode()
    sig = hmac.new(JWT_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"

def _verify_token(token):
    try:
        parts = token.split('.')
        if len(parts) != 2: return None
        payload_b64, sig = parts
        expected = hmac.new(JWT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected): return None
        payload = json.loads(base64.b64decode(payload_b64).decode())
        if payload.get('exp', 0) < time.time(): return None
        return payload.get('user')
    except:
        return None

def _auth_required(self):
    auth = self.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return _verify_token(auth[7:])
    return None

# ─── SECURITY HEADERS ───
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'no-referrer-when-downgrade',
    'Cache-Control': 'no-store, no-cache, must-revalidate',
}

def _send_secure_json(self, data, status=200):
    """Send JSON with security headers."""
    body = json.dumps(data).encode()
    self.send_response(status)
    self.send_header('Content-Type', 'application/json')
    for k, v in SECURITY_HEADERS.items():
        self.send_header(k, v)
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.rstrip('/')
        
        # /api/health — public
        if path == '/api/health':
            _send_secure_json(self, {"status": "ok", "service": "Rupeewa Admin", "version": "3.1"})
            return
        
        # /api/login — check auth
        if path == '/api/login':
            user = _auth_required(self)
            if user:
                _send_secure_json(self, {"authenticated": True, "username": user})
            else:
                _send_secure_json(self, {"authenticated": False})
            return
        
        # ─── AUTH-REQUIRED ENDPOINTS ───
        user = _auth_required(self)
        if not user:
            _send_secure_json(self, {"error": "Authentication required"}, 401)
            return
        
        # /api/dashboard
        if path == '/api/dashboard':
            try:
                config, _ = read_config()
                stats = get_build_stats()
                stats['sources'] = 6
                stats['featured'] = len(config.get('featured_articles', []))
                _send_secure_json(self, stats)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return
        
        # /api/subscribers — auth-protected (list all)
        if path == '/api/subscribers':
            config, _ = read_config()
            subs = config.get('subscribers', [])
            recent = sorted(subs, key=lambda x: x.get('subscribed_at', ''), reverse=True)[:100]
            _send_secure_json(self, {"subscribers": recent, "total": len(subs)})
            return
        
        # /api/seo
        if path == '/api/seo':
            config, _ = read_config()
            seo = {k: config.get(k, '') for k in ['site_name','site_description','site_keywords','og_title','og_description','twitter_handle','google_analytics_id','custom_head_html']}
            _send_secure_json(self, seo)
            return
        
        # /api/seo/save
        if path == '/api/seo/save':
            _send_secure_json(self, {"error": "Use POST"}, 405)
            return
        
        _send_secure_json(self, {"error": "Not found", "path": path}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path.rstrip('/')
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length else ''
        client_ip = self.headers.get('X-Forwarded-For', self.client_address[0]).split(',')[0].strip()
        
        # /api/login — rate-limited auth
        if path == '/api/login':
            # Rate limit check
            if not _check_rate_limit(client_ip):
                _send_secure_json(self, {"error": "Too many attempts. Try again in 15 minutes."}, 429)
                return
            params = parse_qs(body)
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            if username == ADMIN_USER and _verify_password(password, ADMIN_PASS_HASH):
                _record_attempt(client_ip)  # Reset on success
                token = _make_token(username)
                _send_secure_json(self, {"access_token": token, "token_type": "bearer", "username": username})
            else:
                _record_attempt(client_ip)
                _send_secure_json(self, {"error": "Invalid credentials"}, 401)
            return
        
        # /api/subscribers — public POST for newsletter signup
        if path == '/api/subscribers' or path == '/api/subscribe':
            try:
                data = json.loads(body) if body else {}
                email = data.get('email', '').strip().lower()
                if not email or '@' not in email:
                    _send_secure_json(self, {"error": "Invalid email"}, 400)
                    return
                config, sha = read_config()
                subs = config.get('subscribers', [])
                if any(s.get('email') == email for s in subs):
                    _send_secure_json(self, {"status": "exists"})
                    return
                subs.append({"email": email, "subscribed_at": time.strftime('%Y-%m-%dT%H:%M:%S')})
                config['subscribers'] = subs
                if write_config(config, sha):
                    _send_secure_json(self, {"status": "subscribed"})
                else:
                    _send_secure_json(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return
        
        # ─── AUTH-REQUIRED POST ENDPOINTS ───
        user = _auth_required(self)
        if not user:
            _send_secure_json(self, {"error": "Authentication required"}, 401)
            return
        
        # /api/seo/save
        if path == '/api/seo/save':
            try:
                updates = json.loads(body) if body else {}
                config, sha = read_config()
                for key in ['site_name','site_description','site_keywords','og_title','og_description','twitter_handle','google_analytics_id','custom_head_html']:
                    if key in updates:
                        config[key] = updates[key]
                if write_config(config, sha):
                    _send_secure_json(self, {"status": "saved"})
                else:
                    _send_secure_json(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return
        
        # /api/build
        if path == '/api/build':
            import requests
            if VERCEL_DEPLOY_HOOK:
                try:
                    r = requests.post(VERCEL_DEPLOY_HOOK)
                    _send_secure_json(self, {"status": "triggered", "hook_status": r.status_code})
                except Exception as e:
                    _send_secure_json(self, {"error": str(e)}, 500)
            else:
                _send_secure_json(self, {"status": "no_hook", "message": "No Vercel deploy hook configured"})
            return
        
        _send_secure_json(self, {"error": "Not found", "path": path}, 404)
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
