"""Admin health check — Gunicorn/Uvicorn-style entry point for Vercel."""
from http.server import BaseHTTPRequestHandler
from datetime import datetime
import json
import sys
import os

# Add parent dir for shared module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        data = {
            "status": "ok",
            "service": "Rupeewa Admin",
            "version": "2.0",
            "time": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()