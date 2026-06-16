"""SEO settings API endpoint."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler
from lib.shared import json_response, read_config, write_config

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        config, sha = read_config()
        seo = {
            'site_name': config.get('site_name', ''),
            'site_description': config.get('site_description', ''),
            'site_keywords': config.get('site_keywords', ''),
            'og_title': config.get('og_title', ''),
            'og_description': config.get('og_description', ''),
            'twitter_handle': config.get('twitter_handle', ''),
            'google_analytics_id': config.get('google_analytics_id', ''),
            'custom_head_html': config.get('custom_head_html', ''),
        }
        json_response(self, seo)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length else '{}'
        updates = json.loads(body) if body else {}
        
        config, sha = read_config()
        for key in ['site_name', 'site_description', 'site_keywords', 'og_title',
                     'og_description', 'twitter_handle', 'google_analytics_id', 'custom_head_html']:
            if key in updates:
                config[key] = updates[key]
        
        if write_config(config, sha):
            json_response(self, {"status": "saved", "message": "SEO settings updated"})
        else:
            json_response(self, {"error": "Failed to save"}, 500)
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()