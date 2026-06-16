"""Build trigger endpoint — deploys via Vercel webhook."""
import sys, os, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler
from lib.shared import json_response

VERCEL_DEPLOY_HOOK = os.environ.get('VERCEL_DEPLOY_HOOK', '')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Option 1: Use deploy hook URL
        if VERCEL_DEPLOY_HOOK:
            import requests
            try:
                r = requests.post(VERCEL_DEPLOY_HOOK)
                json_response(self, {
                    "status": "triggered",
                    "message": "Build queued on Vercel",
                    "hook_status": r.status_code
                })
                return
            except Exception as e:
                json_response(self, {"error": str(e)}, 500)
                return
        
        # Option 2: No deploy hook configured
        json_response(self, {
            "status": "no_hook",
            "message": "No Vercel deploy hook configured. Config update saved.",
            "note": "Set VERCEL_DEPLOY_HOOK env var for auto-deploy on config changes"
        })
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()