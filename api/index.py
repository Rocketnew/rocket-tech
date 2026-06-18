"""Vercel serverless entry point — handles all /api/* routes.
Security: rate-limited login, JWT-protected endpoints, safety headers."""
import sys, os, json, hashlib, hmac, base64, time, re
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.shared import read_config, write_config, get_build_stats, GITHUB_TOKEN, REPO, read_github_file, write_github_file, upload_image, delete_github_file

ADMIN_USER = os.environ.get('ADMIN_USER', '')
ADMIN_PASS_HASH = os.environ.get('ADMIN_PASS_HASH', '')
VERCEL_DEPLOY_HOOK = os.environ.get('VERCEL_DEPLOY_HOOK', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'rupeewa-secret-change-me')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')

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
        return False
    try:
        parts = stored_hash.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        _, iters, salt_b64, hash_b64 = parts
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt_b64), int(iters))
        return base64.b64encode(dk).decode() == hash_b64
    except:
        return False

def _hash_password(password):
    """Generate PBKDF2-SHA256 hash for a password."""
    salt = os.urandom(32)
    iters = 600000
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iters)
    return f"pbkdf2_sha256${iters}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

# ─── CREDENTIALS FROM ENV + CONFIG FALLBACK ───
def _get_admin_creds():
    """Get admin creds from env vars (priority) or config.json."""
    user = ADMIN_USER
    pass_hash = ADMIN_PASS_HASH
    if not user or not pass_hash:
        try:
            config, _ = read_config()
            if config and isinstance(config, dict):
                user = config.get('admin_user') or user or 'admin'
                pass_hash = config.get('admin_pass_hash') or pass_hash or ''
        except:
            pass
    if not user:
        user = 'admin'
    return user, pass_hash

# ─── JWT ───
def _make_token(username):
    payload = json.dumps({
        "user": username, "exp": time.time() + 86400, "iat": time.time(),
        "jti": base64.b64encode(os.urandom(12)).decode()
    })
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

# ─── BODY PARSING ───
def _get_body(self):
    content_length = int(self.headers.get('Content-Length', 0))
    return self.rfile.read(content_length).decode() if content_length else ''

def _parse_json_body(body):
    try:
        return json.loads(body) if body else {}
    except (json.JSONDecodeError, TypeError):
        return {}

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

# ─── FETCH LIVE ARTICLES FROM INDEX.HTML ───
def _fetch_articles():
    """Parse articles from live rupeewa.vercel.app index.html."""
    import requests
    config, _ = read_config()
    overrides = {o['url']: o for o in config.get('article_overrides', [])}
    try:
        r = requests.get('https://rupeewa.vercel.app/', timeout=10)
        if r.status_code != 200:
            return [], 0, str(r.status_code)
        html = r.text
    except Exception as e:
        return [], 0, str(e)

    articles = []
    # Parse article cards
    card_re = re.compile(
        r'<article[^>]*>.*?<a\s+href="([^"]+)"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>',
        re.DOTALL
    )
    for m in card_re.finditer(html):
        url = m.group(1).strip()
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        override = overrides.get(url, {})
        articles.append({
            'url': url,
            'title': title[:120],
            'is_featured': override.get('is_featured', False),
            'is_hidden': override.get('is_hidden', False),
        })

    return articles, len(articles), None

# ─── SOURCE HELPERS ───
def _get_build_sources():
    """Parse RSS source URLs from build.py."""
    build_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build.py')
    sources = {}
    try:
        with open(build_py_path) as f:
            content = f.read()
        for m in re.finditer(r'rss_urls\[\s*"([^"]+)"\s*\]\s*=\s*"([^"]+)"', content):
            sources[m.group(1)] = m.group(2)
    except:
        pass
    return sources


# ─── VAPID / PUSH HELPERS ──────────────────────────────────────────

VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_SUBJECT = 'mailto:admin@rupeewa.vercel.app'

# In-memory latest notification for SW to fetch (also persisted in config)
_push_latest = {"title": "", "message": "", "timestamp": ""}

def _send_manual_push(subscription, payload_json, vapid_private_key, vapid_public_key):
    """Send push via VAPID JWT. No encrypted payload — SW fetches content from /api/push/latest."""
    import json, time, base64, struct
    from urllib.parse import urlparse
    from http.client import HTTPSConnection

    try:
        # Build VAPID JWT
        hdr = '{"typ":"JWT","alg":"ES256"}'
        dom = urlparse(subscription['endpoint']).hostname
        claims = json.dumps({"aud": dom, "exp": int(time.time()) + 43200, "sub": VAPID_SUBJECT},
                           separators=(',',':'))
        def b64url(d):
            return base64.urlsafe_b64encode(d.encode() if isinstance(d, str) else d).rstrip(b'=').decode()
        sig_in = f"{b64url(hdr)}.{b64url(claims)}".encode()

        # ES256 sign with cryptography
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization, hashes
        key = serialization.load_pem_private_key(vapid_private_key.encode(), password=None)
        der_sig = key.sign(sig_in, ec.ECDSA(hashes.SHA256()))
        # DER to raw r||s
        r_len = der_sig[3]
        r = der_sig[4:4+r_len]
        s = der_sig[5+r_len:]
        sig_b64 = b64url(r.rjust(32, b'\x00') + s.rjust(32, b'\x00'))
        jwt = f"{b64url(hdr)}.{b64url(claims)}.{sig_b64}"

        # POST to endpoint
        parsed = urlparse(subscription['endpoint'])
        conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=10)
        conn.request("POST", parsed.path,
            body=b"",
            headers={
                "TTL": "86400",
                "Content-Type": "application/octet-stream",
                "Authorization": f"vapid t={jwt}, k={vapid_public_key}"
            })
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp.status in (201, 202, 204)
    except:
        return False


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.rstrip('/')

        # /api/health — public
        if path == '/api/health':
            _send_secure_json(self, {"status": "ok", "service": "Rupeewa Admin", "version": "3.2"})
            return

        # /api/auth/me — check token (used by admin.html init)
        if path == '/api/auth/me':
            user = _auth_required(self)
            if user:
                _send_secure_json(self, {"username": user, "is_active": True, "authenticated": True})
            else:
                _send_secure_json(self, {"authenticated": False}, 401)
            return

        # /api/login — check auth (legacy)
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
                stats['now'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                # Add recent builds from config
                build_logs = config.get('build_logs', [])
                stats['recent_builds'] = build_logs[-5:] if build_logs else []
                stats['visits_7d'] = 0
                stats['db_articles'] = stats.get('article_count', 0)
                stats['db_sources'] = 6
                _send_secure_json(self, stats)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/articles
        if path == '/api/articles':
            articles, total, err = _fetch_articles()
            if err:
                _send_secure_json(self, {"error": f"Failed to fetch articles: {err}"}, 500)
                return
            # Parse limit from query
            qs = parse_qs(urlparse(self.path).query)
            limit = int(qs.get('limit', ['200'])[0])
            _send_secure_json(self, {"articles": articles[:limit], "total": total})
            return

        # /api/articles/custom — list custom articles from GitHub
        if path == '/api/articles/custom':
            try:
                custom, _ = read_github_file('admin/custom_articles.json')
                arts = custom.get('articles', []) if custom else []
                _send_secure_json(self, {"articles": arts, "total": len(arts)})
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/sources
        if path == '/api/sources':
            config, _ = read_config()
            db_sources = config.get('db_sources', [])
            build_sources = _get_build_sources()
            _send_secure_json(self, {
                "db_sources": db_sources,
                "build_sources": build_sources,
                "count": len(db_sources)
            })
            return

        # /api/build/logs
        if path == '/api/build/logs':
            config, _ = read_config()
            logs = config.get('build_logs', [])
            _send_secure_json(self, {"logs": logs[-20:]})
            return

        # /api/push/latest — latest notification for SW to fetch (public)
        if path == '/api/push/latest':
            config, _ = read_config()
            latest = config.get('push_latest', {})
            if not latest.get('timestamp'):
                latest = _push_latest
            _send_secure_json(self, latest)
            return

        # /api/images — list uploaded images from GitHub
        if path == '/api/images':
            try:
                import requests
                url = f'https://api.github.com/repos/{REPO}/contents/admin/images'
                headers = {'User-Agent': 'rupeewa-admin', 'Accept': 'application/vnd.github.v3+json'}
                if GITHUB_TOKEN:
                    headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code != 200:
                    _send_secure_json(self, {"images": [], "total": 0})
                    return
                files = r.json()
                images = [{
                    'name': f['name'],
                    'size': f['size'],
                    'url': f['download_url'],
                    'sha': f['sha']
                } for f in files if isinstance(f, dict) and f.get('type') == 'file' and f['name'].lower().rsplit('.', 1)[-1] in ('png','jpg','jpeg','gif','webp','svg','ico')]
                _send_secure_json(self, {"images": images, "total": len(images)})
            except Exception as e:
                _send_secure_json(self, {"images": [], "total": 0, "error": str(e)})
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

        # /api/subscribers
        if path == '/api/subscribers':
            config, _ = read_config()
            subs = config.get('subscribers', [])
            recent = sorted(subs, key=lambda x: x.get('subscribed_at', ''), reverse=True)[:100]
            _send_secure_json(self, {"subscribers": recent, "total": len(subs)})
            return

        # /api/search?q=...
        if path == '/api/search':
            q = parse_qs(urlparse(self.path).query).get('q', [''])[0].strip().lower()
            if not q or len(q) < 2:
                _send_secure_json(self, {"results": [], "query": q})
                return
            try:
                import requests as req
                base_url = 'https://rupeewa.vercel.app'
                r = req.get(f'{base_url}/api/articles', timeout=5,
                            headers={'Authorization': self.headers.get('Authorization', '')})
                if r.status_code == 200:
                    data = r.json()
                    articles = data.get('articles', [])
                    results = [a for a in articles if q in a.get('title', '').lower() or q in a.get('description', '').lower()]
                    _send_secure_json(self, {"results": results[:20], "total": len(results), "query": q})
                else:
                    _send_secure_json(self, {"results": [], "query": q})
            except:
                _send_secure_json(self, {"results": [], "query": q})
            return

        _send_secure_json(self, {"error": "Not found", "path": path}, 404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip('/')
        body = _get_body(self)
        client_ip = self.headers.get('X-Forwarded-For', self.client_address[0]).split(',')[0].strip()

        # /api/login — rate-limited auth
        if path == '/api/login':
            if not _check_rate_limit(f"login:{client_ip}", LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW, LOGIN_BLOCK_DURATION):
                _send_secure_json(self, {"error": "Too many attempts. Try again in 15 minutes."}, 429)
                return
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, TypeError):
                data = {}
            username = data.get('username', '').strip()
            password = data.get('password', '')

            # Check credentials from env + config fallback
            admin_user, admin_hash = _get_admin_creds()
            if username == admin_user and _verify_password(password, admin_hash):
                _record_attempt(f"login:{client_ip}")
                token = _make_token(username)
                _send_secure_json(self, {"access_token": token, "token_type": "bearer", "username": username})
            else:
                _record_attempt(f"login:{client_ip}")
                _send_secure_json(self, {"error": "Invalid credentials"}, 401)
            return

        # /api/subscribers — public POST for newsletter signup
        if path == '/api/subscribers' or path == '/api/subscribe':
            if not _check_rate_limit(f"subscribe:{client_ip}"):
                _send_secure_json(self, {"error": "Too many requests. Try again later."}, 429)
                return
            try:
                data = _parse_json_body(body)
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

        # /api/push/subscribe — public push subscription (no auth)
        if path == '/api/push/subscribe':
            try:
                sub_data = _parse_json_body(body)
                if 'subscription' in sub_data:
                    sub_data = sub_data['subscription']
                endpoint = sub_data.get('endpoint', '')
                if not endpoint:
                    _send_secure_json(self, {"error": "Missing endpoint"}, 400)
                    return
                config, sha = read_config()
                subs = config.get('push_subscriptions', [])
                subs = [s for s in subs if s.get('endpoint') != endpoint]
                subs.append({
                    'endpoint': endpoint,
                    'keys': sub_data.get('keys'),
                    'subscribed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                })
                config['push_subscriptions'] = subs
                write_config(config, sha)
                _send_secure_json(self, {"status": "saved", "total": len(subs)})
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/push/unsubscribe — public push unsubscription (no auth)
        if path == '/api/push/unsubscribe':
            try:
                data = _parse_json_body(body)
                endpoint = data.get('endpoint', '')
                if not endpoint:
                    _send_secure_json(self, {"error": "Missing endpoint"}, 400)
                    return
                config, sha = read_config()
                subs = config.get('push_subscriptions', [])
                before = len(subs)
                subs = [s for s in subs if s.get('endpoint') != endpoint]
                config['push_subscriptions'] = subs
                write_config(config, sha)
                _send_secure_json(self, {"status": "removed", "removed": before - len(subs)})
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

        # CSRF check
        requested_with = self.headers.get('X-Requested-With', '')
        referer = self.headers.get('Referer', '')
        if not requested_with and 'rupeewa.vercel.app' not in referer:
            _send_secure_json(self, {"error": "CSRF check failed"}, 403)
            return

        # /api/seo or /api/seo/save — save SEO settings
        if path in ('/api/seo', '/api/seo/save'):
            try:
                updates = _parse_json_body(body)
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

        # /api/articles/override
        if path == '/api/articles/override':
            try:
                data = _parse_json_body(body)
                url = data.get('url', '')
                if not url:
                    _send_secure_json(self, {"error": "url required"}, 400)
                    return
                config, sha = read_config()
                overrides = config.get('article_overrides', [])
                # Find existing override or add new
                found = False
                for o in overrides:
                    if o.get('url') == url:
                        if 'is_featured' in data:
                            o['is_featured'] = bool(data['is_featured'])
                        if 'is_hidden' in data:
                            o['is_hidden'] = bool(data['is_hidden'])
                        found = True
                        break
                if not found:
                    overrides.append({
                        'url': url,
                        'is_featured': bool(data.get('is_featured', False)),
                        'is_hidden': bool(data.get('is_hidden', False)),
                        'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                    })
                config['article_overrides'] = overrides
                if write_config(config, sha):
                    _send_secure_json(self, {"status": "ok"})
                else:
                    _send_secure_json(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/articles/create — custom article with text + image
        if path == '/api/articles/create':
            try:
                data = _parse_json_body(body)
                title = data.get('title', '').strip()
                content = data.get('content', '').strip()
                image_url = data.get('image_url', '').strip()
                author = data.get('author', 'Admin').strip()
                if not title:
                    _send_secure_json(self, {"error": "title required"}, 400)
                    return
                # Load existing custom articles from GitHub
                CUSTOM_PATH = 'admin/custom_articles.json'
                articles, sha = read_github_file(CUSTOM_PATH)
                if articles is None:
                    articles = {"articles": []}
                new_id = max([a.get('id', 0) for a in articles.get('articles', [])], default=0) + 1
                article = {
                    'id': new_id,
                    'title': title,
                    'content': content,
                    'image_url': image_url,
                    'author': author,
                    'source': 'Custom',
                    'is_featured': bool(data.get('is_featured', False)),
                    'is_hidden': bool(data.get('is_hidden', False)),
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                }
                articles['articles'].append(article)
                if write_github_file(CUSTOM_PATH, articles, sha, f'admin: custom article "{title}"'):
                    _send_secure_json(self, {"status": "created", "id": new_id, "article": article})
                else:
                    _send_secure_json(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/upload — upload an image to GitHub repo
        if path == '/api/upload':
            try:
                data = _parse_json_body(body)
                filename = data.get('filename', 'image.png')
                img_data = data.get('data', '')
                if not img_data:
                    _send_secure_json(self, {"error": "No image data provided"}, 400)
                    return
                url = upload_image(filename, img_data)
                if url:
                    _send_secure_json(self, {"url": url})
                else:
                    _send_secure_json(self, {"error": "Upload failed"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/seo — get/set SEO settings including Google Analytics ID
        if path == '/api/seo':
            try:
                config, sha = read_config()
                if method == 'GET':
                    _send_secure_json(self, {
                        "site_name": config.get('site_name', ''),
                        "site_description": config.get('site_description', ''),
                        "site_keywords": config.get('site_keywords', ''),
                        "og_title": config.get('og_title', ''),
                        "og_description": config.get('og_description', ''),
                        "twitter_handle": config.get('twitter_handle', ''),
                        "google_analytics_id": config.get('google_analytics_id', ''),
                        "custom_head_html": config.get('custom_head_html', '')
                    })
                elif method == 'POST':
                    data = _parse_json_body(body)
                    for key in ('site_name', 'site_description', 'site_keywords',
                                'og_title', 'og_description', 'twitter_handle',
                                'google_analytics_id', 'custom_head_html'):
                        if key in data:
                            config[key] = data[key]
                    if write_config(config, sha):
                        _send_secure_json(self, {"status": "ok"})
                    else:
                        _send_secure_json(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/sources/add
        if path == '/api/sources/add':
            try:
                data = _parse_json_body(body)
                name = data.get('name', '').strip()
                rss_url = data.get('rss_url', '').strip()
                if not name or not rss_url:
                    _send_secure_json(self, {"error": "name and rss_url required"}, 400)
                    return
                config, sha = read_config()
                db_sources = config.get('db_sources', [])
                # Check for duplicate
                if any(s.get('rss_url') == rss_url for s in db_sources):
                    _send_secure_json(self, {"error": "Source already exists"}, 400)
                    return
                new_id = max([s.get('id', 0) for s in db_sources], default=0) + 1
                db_sources.append({
                    'id': new_id,
                    'name': name,
                    'rss_url': rss_url,
                    'is_active': True,
                    'article_limit': int(data.get('article_limit', 30)),
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                })
                config['db_sources'] = db_sources
                if write_config(config, sha):
                    _send_secure_json(self, {"status": "ok", "id": new_id, "name": name})
                else:
                    _send_secure_json(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/build or /api/build/trigger — trigger GitHub Actions workflow (Build + Deploy)
        if path in ('/api/build', '/api/build/trigger'):
            import requests as req
            from lib.shared import GITHUB_TOKEN, REPO
            if not GITHUB_TOKEN:
                _send_secure_json(self, {"status": "no_token", "message": "No GitHub token configured — builds work automatically on git push"}, 200)
                return
            # Record build log
            config, sha = read_config()
            build_logs = config.get('build_logs', [])
            build_logs.append({
                'status': 'triggered',
                'articles': 0,
                'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'error': None
            })
            config['build_logs'] = build_logs
            write_config(config, sha)
            # Trigger GitHub Actions workflow_dispatch
            try:
                wf_url = f"https://api.github.com/repos/{REPO}/actions/workflows/deploy.yml/dispatches"
                r = req.post(wf_url, json={"ref": "main"}, headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "User-Agent": "rupeewa-admin",
                    "Accept": "application/vnd.github+json"
                }, timeout=15)
                status = "triggered" if r.status_code in (204, 201, 200) else "trigger_failed"
                # Update last log entry
                config, sha = read_config()
                logs = config.get('build_logs', [])
                if logs:
                    logs[-1]['status'] = status
                    logs[-1]['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    if status == "trigger_failed":
                        logs[-1]['error'] = f"GitHub API returned {r.status_code}"
                config['build_logs'] = logs
                write_config(config, sha)
                _send_secure_json(self, {
                    "status": status,
                    "hook_status": r.status_code,
                    "output": f"Build workflow {'triggered' if status == 'triggered' else f'failed ({r.status_code})'}"
                })
            except Exception as e:
                # Mark last log as failed
                config, sha = read_config()
                logs = config.get('build_logs', [])
                if logs:
                    logs[-1]['status'] = 'failed'
                    logs[-1]['error'] = str(e)
                config['build_logs'] = logs
                write_config(config, sha)
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # /api/push/send — send notification to all subscribers (admin only)
        if path == '/api/push/send':
            user = _auth_required(self)
            if not user:
                _send_secure_json(self, {"error": "Authentication required"}, 401)
                return
            try:
                data = _parse_json_body(body)
                title = data.get('title', 'Rupeewa News')
                message = data.get('message', 'New tech news available!')
                icon_url = data.get('icon', '/icons/icon-192.png')

                config, sha = read_config()
                subs = config.get('push_subscriptions', [])
                if not subs:
                    _send_secure_json(self, {"status": "ok", "sent": 0, "message": "No subscribers"})
                    return

                vapid_private = VAPID_PRIVATE_KEY or config.get('vapid_private_key', '')
                vapid_public = VAPID_PUBLIC_KEY or config.get('vapid_public_key', '')
                if not vapid_private or not vapid_public:
                    _send_secure_json(self, {"error": "VAPID keys not configured"}, 500)
                    return

                payload = json.dumps({
                    'title': title,
                    'message': message,
                    'icon': icon_url,
                    'badge': '/icons/icon-96.png',
                    'url': 'https://rupeewa.vercel.app/',
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                })

                # Save latest notification for SW to fetch
                latest_data = {"title": title, "message": message, "icon": icon_url, "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
                global _push_latest
                _push_latest = latest_data
                config['push_latest'] = latest_data
                write_config(config, sha_)

                sent = 0
                errors = []

                # Try pywebpush first, fallback to manual
                try:
                    from pywebpush import webpush, WebPushException
                    HAS_PYWEBPUSH = True
                except ImportError:
                    HAS_PYWEBPUSH = False

                for sub in subs:
                    try:
                        if HAS_PYWEBPUSH:
                            push_info = {'endpoint': sub['endpoint'], 'keys': sub.get('keys', {})}
                            webpush(
                                subscription_info=push_info,
                                data=payload,
                                vapid_private_key=vapid_private,
                                vapid_claims={"sub": "mailto:admin@rupeewa.vercel.app"}
                            )
                            sent += 1
                        else:
                            # Manual VAPID push - ES256 JWT + encrypted payload
                            if _send_manual_push(sub, payload, vapid_private, vapid_public):
                                sent += 1
                            else:
                                errors.append({"endpoint": sub['endpoint'][:30]+"...", "error": "manual push failed"})
                    except Exception as e:
                        err_msg = str(e)[:80]
                        if '410' in err_msg or 'Gone' in err_msg or 'expired' in err_msg.lower():
                            errors.append({"endpoint": sub['endpoint'][:30]+"...", "error": "expired"})
                        else:
                            errors.append({"endpoint": sub['endpoint'][:30]+"...", "error": err_msg})

                _send_secure_json(self, {
                    "status": "ok",
                    "sent": sent,
                    "total": len(subs),
                    "errors": errors if errors else None
                })
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        _send_secure_json(self, {"error": "Not found", "path": path}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip('/')
        body = _get_body(self)
        client_ip = self.headers.get('X-Forwarded-For', self.client_address[0]).split(',')[0].strip()

        # Auth check
        user = _auth_required(self)
        if not user:
            _send_secure_json(self, {"error": "Authentication required"}, 401)
            return

        # DELETE /api/articles/{id} — delete custom article by ID
        art_match = re.match(r'^/api/articles/(\d+)$', path)
        if art_match:
            try:
                article_id = int(art_match.group(1))
                CUSTOM_PATH = 'admin/custom_articles.json'
                articles, sha = read_github_file(CUSTOM_PATH)
                if articles is None:
                    _send_secure_json(self, {"error": "No custom articles found"}, 404)
                    return
                before = len(articles.get('articles', []))
                articles['articles'] = [a for a in articles.get('articles', []) if a.get('id') != article_id]
                if len(articles['articles']) == before:
                    _send_secure_json(self, {"error": "Article not found"}, 404)
                    return
                if write_github_file(CUSTOM_PATH, articles, sha, f'admin: deleted article #{article_id}'):
                    _send_secure_json(self, {"status": "deleted", "id": article_id})
                else:
                    _send_secure_json(self, {"error": "Failed to delete"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # DELETE /api/uploads/{filename} — delete uploaded image from GitHub
        up_match = re.match(r'^/api/uploads/(.+)$', path)
        if up_match:
            try:
                filename = up_match.group(1)
                img_path = f'admin/images/{filename}'
                # Get SHA of the file first
                content, sha = read_github_file(img_path)
                if sha is None:
                    _send_secure_json(self, {"error": "Image not found"}, 404)
                    return
                if delete_github_file(img_path, sha, f'admin: delete image {filename}'):
                    _send_secure_json(self, {"status": "deleted", "filename": filename})
                else:
                    _send_secure_json(self, {"error": "Failed to delete image"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
            return

        # DELETE /api/sources/{id}
        src_match = re.match(r'^/api/sources/(\d+)$', path)
        if src_match:
            try:
                source_id = int(src_match.group(1))
                config, sha = read_config()
                db_sources = config.get('db_sources', [])
                new_sources = [s for s in db_sources if s.get('id') != source_id]
                if len(new_sources) == len(db_sources):
                    _send_secure_json(self, {"error": "Source not found"}, 404)
                    return
                config['db_sources'] = new_sources
                if write_config(config, sha):
                    _send_secure_json(self, {"status": "ok", "deleted": source_id})
                else:
                    _send_secure_json(self, {"error": "Failed to save"}, 500)
            except Exception as e:
                _send_secure_json(self, {"error": str(e)}, 500)
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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.end_headers()
