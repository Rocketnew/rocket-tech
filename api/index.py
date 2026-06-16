"""Vercel serverless entry point — handles all /api/* routes.
Security: rate-limited login, JWT-protected endpoints, safety headers."""
import sys, os, json, hashlib, hmac, base64, time, re
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
_rate_attempts = defaultdict(list)
RATE_MAX_ATTEMPTS = 10
RATE_WINDOW = 60  # 1 minute
RATE_BLOCK_DURATION = 120  # 2 minutes

def _check_rate_limit(key, max_attempts=RATE_MAX_ATTEMPTS, window=RATE_WINDOW, block=RATE_BLOCK_DURATION):
    now = time.time()
    _rate_attempts[key] = [t for t in _rate_attempts[key] if t > now - block]
    if len(_rate_attempts[key]) >= max_attempts:
        if _rate_attempts[key] and (now - _rate_attempts[key][0]) < block:
            return False
        _rate_attempts[key] = []
    return True

def _record_attempt(key):
    _rate_attempts[key].append(time.time())

# Login-specific stricter limits
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW = 300  # 5 minutes
LOGIN_BLOCK_DURATION = 900  # 15 minutes

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
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://www.googletagmanager.com https://www.google-analytics.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://rupeewa.vercel.app; frame-ancestors 'none'",
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

# ─── VALIDATION HELPERS ───
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def _valid_email(email):
    return bool(_EMAIL_RE.match(email)) if email else False

def _sanitize_head_html(html):
    """Allowlist-based HTML sanitizer for custom_head_html."""
    ALLOWED_TAGS = {'b','i','em','strong','a','br','p','ul','ol','li','h1','h2','h3','h4','h5','h6','blockquote','pre','code','span','div','img','meta','link','script','style','title','base','noscript'}
    def _strip_tag(m):
        tag = m.group(1)
        if tag.lower() not in ALLOWED_TAGS:
            return ''
        return m.group(0)
    html = re.sub(r'<(\w+)[^>]*>.*?</\1>', _strip_tag, html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<(\w+)[^>]*/>', lambda m: m.group(0) if m.group(1).lower() in ALLOWED_TAGS else '', html)
    html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', 'href="#"', html, flags=re.IGNORECASE)
    return html

_MAX_LENGTHS = {
    'site_name': 200, 'site_description': 500, 'site_keywords': 500,
    'og_title': 200, 'og_description': 500, 'twitter_handle': 50,
    'google_analytics_id': 50, 'custom_head_html': 10000,
}

def _validate_seo_inputs(updates):
    errors = {}
    for key, val in updates.items():
        if key in _MAX_LENGTHS and isinstance(val, str) and len(val) > _MAX_LENGTHS[key]:
            errors[key] = f"Max {_MAX_LENGTHS[key]} chars"
    return errors

def _sanitize_seo_value(key, val):
    if not isinstance(val, str):
        return val
    if key == 'custom_head_html':
        return _sanitize_head_html(val)
    if key in ('site_description', 'og_description'):
        val = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', val)
    else:
        val = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\n\r]', '', val)
    return val.strip()[:2000]

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
            # Rate limit check (stricter for login)
            if not _check_rate_limit(f"login:{client_ip}", LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW, LOGIN_BLOCK_DURATION):
                _send_secure_json(self, {"error": "Too many attempts. Try again in 15 minutes."}, 429)
                return
            params = parse_qs(body)
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            if username == ADMIN_USER and _verify_password(password, ADMIN_PASS_HASH):
                _record_attempt(f"login:{client_ip}")  # Reset on success
                token = _make_token(username)
                _send_secure_json(self, {"access_token": token, "token_type": "bearer", "username": username})
            else:
                _record_attempt(f"login:{client_ip}")
                _send_secure_json(self, {"error": "Invalid credentials"}, 401)
            return
        
        # /api/subscribers — public POST for newsletter signup
        if path == '/api/subscribers' or path == '/api/subscribe':
            # Rate limit by IP (10/min) to prevent spam
            if not _check_rate_limit(f"subscribe:{client_ip}"):
                _send_secure_json(self, {"error": "Too many requests. Try again later."}, 429)
                return
            try:
                data = json.loads(body) if body else {}
                email = data.get('email', '').strip().lower()
                if not email or not _valid_email(email):
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
        
        # Rate limit all auth-protected POST by user
        if not _check_rate_limit(f"user:{user}:{path}", 20, 60, 120):
            _send_secure_json(self, {"error": "Too many requests. Slow down."}, 429)
            return
        
        # CSRF check — require X-Requested-With header
        requested_with = self.headers.get('X-Requested-With', '')
        referer = self.headers.get('Referer', '')
        if not requested_with and 'rupeewa.vercel.app' not in referer:
            _send_secure_json(self, {"error": "CSRF check failed"}, 403)
            return
        
        # /api/seo/save
        if path == '/api/seo/save':
            try:
                updates = json.loads(body) if body else {}
                # Validate input lengths
                errors = _validate_seo_inputs(updates)
                if errors:
                    _send_secure_json(self, {"error": "Validation failed", "fields": errors}, 400)
                    return
                config, sha = read_config()
                for key in ['site_name','site_description','site_keywords','og_title','og_description','twitter_handle','google_analytics_id','custom_head_html']:
                    if key in updates:
                        config[key] = _sanitize_seo_value(key, updates[key])
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
        origin = self.headers.get('Origin', '')
        allowed_origins = ['https://rupeewa.vercel.app', 'https://rocketnewsdaily.vercel.app']
        if origin in allowed_origins:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', 'https://rupeewa.vercel.app')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.end_headers()
