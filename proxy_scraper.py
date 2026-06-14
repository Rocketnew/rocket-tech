#!/usr/bin/env python3
"""
USA Proxy Scraper v2 — Fast, country-filtered, auto-refresh
Sources: ProxyScrape USA + Geonode
Output: ~/.rocket-traffic-profile/proxies.json
"""

import json, re, os, random, urllib.request
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

PROFILE_DIR = Path.home() / ".rocket-traffic-profile"
PROFILE_DIR.mkdir(exist_ok=True)
PROXIES_FILE = PROFILE_DIR / "proxies.json"
TIMEOUT = 15

# ONLY country-filtered sources
SOURCES = [
    {
        "name": "ProxyScrape USA",
        "url": "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text&country=us",
        "parser": "ipport"  # protocol://ip:port
    },
    {
        "name": "Geonode US",
        "url": "https://proxylist.geonode.com/api/proxy-list?limit=200&page=1&sort_by=lastChecked&sort_type=desc&country=US&protocols=http%2Chttps%2Csocks4%2Csocks5",
        "parser": "geonode"
    },
    {
        "name": "Geonode US p2",
        "url": "https://proxylist.geonode.com/api/proxy-list?limit=200&page=2&sort_by=lastChecked&sort_type=desc&country=US&protocols=http%2Chttps%2Csocks4%2Csocks5",
        "parser": "geonode"
    },
]


def fetch(url, name=""):
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0",
            "Accept": "text/plain,application/json,*/*",
        })
        with urlopen(req, timeout=TIMEOUT) as r:
            data = r.read().decode("utf-8", errors="replace")
        print(f"  ✅ {name}: {len(data)}b")
        return data
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return None


def parse_ipport(text):
    proxies = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line: continue
        m = re.match(r'(?:(\w+)://)?([\d.]+):(\d+)', line)
        if m:
            proto = (m.group(1) or "http").lower()
            if proto not in ("http", "https", "socks4", "socks5"): continue
            proxies.append({"ip": m.group(2), "port": m.group(3), "protocol": proto})
    return proxies


def parse_geonode(text):
    proxies = []
    try:
        data = json.loads(text)
        for item in data.get("data", []):
            ip = item.get("ip")
            port = item.get("port")
            if not ip or not port: continue
            for proto in (item.get("protocols") or ["http"]):
                p = proto.lower().replace("https", "http")
                if p in ("http", "socks4", "socks5"):
                    proxies.append({"ip": ip, "port": str(port), "protocol": p})
    except: pass
    return proxies


def get_public_ip():
    """Get our current public IP"""
    try:
        req = Request("https://api.ipify.org?format=json", headers={"User-Agent": "curl/8.0"})
        with urlopen(req, timeout=5) as r:
            return json.loads(r.read())["ip"]
    except:
        return "unknown"


def format_selenium(proxy):
    """Format proxy for Selenium ChromeOptions"""
    return f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"


def main():
    our_ip = get_public_ip()
    print(f"\n🇺🇸  USA PROXY SCRAPER v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Our IP: {our_ip}")
    print(f"{'='*50}")
    
    all_proxies = []
    seen = set()
    
    for src in SOURCES:
        print(f"\n📡 {src['name']}")
        text = fetch(src["url"], src["name"])
        if not text: continue
        
        if src["parser"] == "ipport":
            proxies = parse_ipport(text)
        elif src["parser"] == "geonode":
            proxies = parse_geonode(text)
        else:
            continue
        
        added = 0
        for p in proxies:
            key = f"{p['ip']}:{p['port']}:{p['protocol']}"
            if key not in seen:
                seen.add(key)
                all_proxies.append(p)
                added += 1
        print(f"   → {added} new")
    
    print(f"\n{'='*50}")
    print(f"📊 Total unique USA proxies: {len(all_proxies)}")
    
    # Save all (unverified — let traffic bot test at runtime)
    output = {
        "updated": datetime.now().isoformat(),
        "our_ip": our_ip,
        "count": len(all_proxies),
        "proxies": all_proxies
    }
    PROXIES_FILE.write_text(json.dumps(output, indent=2))
    
    # Also save simple text format (protocol://ip:port per line)
    txt_path = PROFILE_DIR / "proxies.txt"
    with open(txt_path, "w") as f:
        for p in all_proxies:
            f.write(f"{p['protocol']}://{p['ip']}:{p['port']}\n")
    
    # Stats
    by_proto = {}
    for p in all_proxies:
        by_proto[p["protocol"]] = by_proto.get(p["protocol"], 0) + 1
    
    print(f"\n📈 Protocol breakdown:")
    for proto, count in sorted(by_proto.items()):
        print(f"   {proto.upper():8s}: {count}")
    
    print(f"\n📁 Saved:")
    print(f"   {PROXIES_FILE}")
    print(f"   {txt_path}")
    
    # Show first 5
    print(f"\n🔰 Sample proxies:")
    for p in all_proxies[:5]:
        print(f"   {format_selenium(p)}")
    
    print(f"{'='*50}\n")
    return all_proxies


if __name__ == "__main__":
    main()
