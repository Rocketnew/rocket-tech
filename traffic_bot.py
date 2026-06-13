#!/usr/bin/env python3
"""
Rocket News Traffic Simulator — Cron-friendly
Each run simulates 1-3 real user visits to trigger Monetag popunders.
"""

import random
import re
import sys
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

SITE = "https://rocketnewsdaily.vercel.app"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

ACCEPT_LANGS = ["en-US,en;q=0.9", "en-IN;q=0.8,en;q=0.7", "hi;q=0.9,en;q=0.8", "en-GB,en;q=0.9"]


def fetch(url, referer="", retries=2):
    """Fetch a URL with random browser fingerprint"""
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGS),
        "Accept-Encoding": "gzip, deflate",
        "Referer": referer if referer else SITE,
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }
    for attempt in range(retries):
        try:
            req = Request(url, headers=headers)
            resp = urlopen(req, timeout=15)
            html = resp.read().decode("utf-8", errors="replace")
            return html, resp.status
        except URLError as e:
            if attempt < retries - 1:
                time.sleep(2)
    return None, 0


def extract_links(html):
    """Extract external article links from page HTML"""
    links = re.findall(r'href="(https?://[^"]+)"', html)
    exclude_domains = ["rocketnewsdaily.vercel.app", "monetag.com", "cdn.monetag.com", "quge5.com"]
    articles = [
        l for l in links
        if l.startswith("http") and not any(d in l for d in exclude_domains)
    ]
    return list(set(articles))


def simulate_visit():
    """Simulate one user visit with scrolling + optional article click"""
    results = {"visit": 0, "click": 0, "status": 0, "error": ""}
    
    # 1. Visit main page
    html, status = fetch(SITE)
    results["status"] = status
    if not html:
        results["error"] = f"Fetch failed: {status}"
        return results
    
    results["visit"] = 1
    print(f"  📄 Main page → {status}")
    
    # 2. Simulate reading (scroll delay)
    scroll_sleep = random.uniform(3, 12)
    time.sleep(scroll_sleep)
    
    # 3. Maybe click an article
    if random.random() < 0.5:  # 50% chance
        links = extract_links(html)
        if links:
            target = random.choice(links)
            _, art_status = fetch(target, SITE)
            results["click"] = 1
            print(f"  🖱️ Click → {target[:80]}... ({art_status})")
            
            # 4. Maybe click a 2nd article
            time.sleep(random.uniform(2, 6))
            if random.random() < 0.3:
                remaining = [l for l in links if l != target]
                if remaining:
                    t2 = random.choice(remaining)
                    fetch(t2, SITE)
                    results["click"] = 2
                    print(f"  🖱️ Click #2 → {t2[:80]}...")
    
    return results


def main():
    print(f"🤖 Traffic Bot — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Target: {SITE}")
    
    # Do 1-3 simulated visits per run
    num_visits = random.randint(1, 3)
    total_visits = 0
    total_clicks = 0
    
    for i in range(num_visits):
        # Random gap between visits within same run
        if i > 0:
            gap = random.randint(10, 60)
            time.sleep(gap)
        
        print(f"\n  ── Visit {i+1}/{num_visits} ──")
        result = simulate_visit()
        total_visits += result["visit"]
        total_clicks += result["click"]
    
    print(f"\n  📊 Done: {total_visits} visits, {total_clicks} clicks")


if __name__ == "__main__":
    main()
