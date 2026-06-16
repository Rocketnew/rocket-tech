"""Shared helpers for Rupeewa admin serverless functions."""

import os
import json
import base64
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
REPO = 'Rocketnew/rocket-tech'
CONFIG_PATH = 'admin/config.json'

def json_response(handler, data, status=200):
    handler.send_response(status)
    handler.send_header('Content-type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())

def read_github_file(path):
    """Read a file from GitHub repo using the API."""
    import requests
    url = f'https://api.github.com/repos/{REPO}/contents/{path}'
    headers = {'User-Agent': 'rupeewa-admin'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode()
        return json.loads(content), r.json().get('sha')
    return None, None

def write_github_file(path, data, sha=None, message='admin config update'):
    """Write a file to GitHub repo using the API."""
    import requests
    url = f'https://api.github.com/repos/{REPO}/contents/{path}'
    headers = {'User-Agent': 'rupeewa-admin'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'
    
    payload = {
        'message': message,
        'content': base64.b64encode(json.dumps(data, indent=2).encode()).decode(),
    }
    if sha:
        payload['sha'] = sha
    
    r = requests.put(url, json=payload, headers=headers)
    return r.status_code in (200, 201)

def read_config():
    """Read admin config from GitHub."""
    config, sha = read_github_file(CONFIG_PATH)
    if config is None:
        config = {
            'site_name': 'Rupeewa News Daily',
            'site_description': 'Latest tech news curated daily from top sources',
            'site_keywords': 'tech news, technology, startups, AI, gadgets',
            'og_title': '',
            'og_description': '',
            'twitter_handle': '',
            'google_analytics_id': '',
            'custom_head_html': '',
            'featured_articles': [],
            'subscribers': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    return config, sha

def write_config(config, sha):
    """Write admin config to GitHub."""
    config['updated_at'] = datetime.now().isoformat()
    return write_github_file(CONFIG_PATH, config, sha, 'admin: config updated')

def update_cron_schedule(schedule):
    """Update the cron schedule for the site."""
    pass  # Will implement if needed

def get_build_stats():
    """Get stats from the current build."""
    import requests
    stats = {
        'article_count': 0,
        'source_count': 0,
        'index_size': 0,
        'last_build': None,
        'subscribers': 0
    }
    
    # Read config
    config, _ = read_config()
    if config:
        stats['subscribers'] = len(config.get('subscribers', []))
    
    # Read index.html from live site
    try:
        r = requests.get('https://rupeewa.vercel.app/', timeout=5)
        if r.status_code == 200:
            stats['index_size'] = len(r.content)
            stats['article_count'] = r.text.count('news-card')
            stats['last_build'] = datetime.now().isoformat()
    except:
        pass
    
    return stats