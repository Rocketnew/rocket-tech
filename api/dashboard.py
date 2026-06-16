"""Dashboard stats endpoint."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler
from lib.shared import json_response, get_build_stats, read_config

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        config, _ = read_config()
        stats = get_build_stats()
        stats['sources'] = 6
        stats['featured'] = len(config.get('featured_articles', []))
        stats['has_config'] = config is not None
        json_response(self, stats)
    
    def do_OPTIONS(self):
        self.do_GET()