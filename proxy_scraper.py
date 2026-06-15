#!/usr/bin/env python3
"""
USA Proxy Aggregator v3 — Scrapes 15+ sources for fresh USA proxies
Output: ~/.rocket-traffic-profile/proxies.json (deduplicated, format for traffic_bot.py)
Run: python3 proxy_scraper.py
"""

import json, re, time, os, socket, threading, urllib.request, urllib.error, ssl
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = Path.home() / ".rocket-traffic-profile" / "proxies.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

TIMEOUT = 8  # fetch timeout per source
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=TIMEOUT):
    """Fetch URL with error handling"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        data = resp.read().decode("utf-8", errors="ignore")
        resp.close()
        return data
    except:
        return ""

def parse_proxies(text, pattern):
    """Extract ip:port pairs matching pattern"""
    found = set()
    for ip, port in re.findall(pattern, text):
        try:
            p = int(port)
            if 1 <= p <= 65535 and not ip.startswith("0.") and not ip.startswith("127.") and not ip.startswith("10.") and not ip.startswith("172.16.") and not ip.startswith("192.168."):
                found.add(f"{ip}:{p}")
        except:
            pass
    return found

def parse_proxies_with_country(text, pattern, country_field=1):
    """Extract ip:port from text with country marker"""
    found = set()
    for parts in re.finditer(pattern, text):
        g = parts.groups()
        try:
            ip = g[0]; port = g[1]
            p = int(port)
            country = g[country_field] if len(g) > country_field else ""
            if 1 <= p <= 65535 and not ip.startswith("0.") and not ip.startswith("127.") and not ip.startswith("10.") and not ip.startswith("172.16.") and not ip.startswith("192.168."):
                if "US" in country.upper() or country == "":
                    found.add(f"{ip}:{p}")
        except:
            pass
    return found

# ============================================================
# SOURCE SCRAPERS
# ============================================================

def scrape_proxyscrape():
    """ProxyScrape API — HTTP/HTTPS/SOCKS4/SOCKS5"""
    results = set()
    urls = [
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=ipport&format=text&country=US&protocol=http",
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=ipport&format=text&country=US&protocol=socks4",
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=ipport&format=text&country=US&protocol=socks5",
    ]
    for url in urls:
        txt = fetch(url)
        for line in txt.strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                results.add(line)
    return results

def scrape_geonode():
    """Geonode API"""
    results = set()
    for proto in ["http", "socks4", "socks5"]:
        url = f"https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols={proto}&countries=US"
        txt = fetch(url, timeout=10)
        try:
            data = json.loads(txt)
            for item in data.get("data", []):
                ip = item.get("ip", "")
                port = item.get("port", "")
                if ip and port:
                    results.add(f"{ip}:{port}")
        except:
            pass
    return results

def scrape_thespeedx():
    """TheSpeedX/PROXY-List GitHub"""
    results = set()
    for url in [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    ]:
        txt = fetch(url)
        for line in txt.strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                results.add(line)
    return results

def scrape_jetkai():
    """jetkai/proxy-list GitHub"""
    results = set()
    for url in [
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    ]:
        txt = fetch(url)
        for line in txt.strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                results.add(line)
    return results

def scrape_openproxy():
    """openproxy.space API"""
    results = set()
    txt = fetch("https://openproxy.space/list/http")
    try:
        data = json.loads(txt)
        if isinstance(data, list):
            for ip_port in data:
                if isinstance(ip_port, str) and re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", ip_port):
                    results.add(ip_port)
    except:
        pass
    return results

def scrape_proxyscan():
    """proxyscan.io API"""
    results = set()
    for type_ in ["http", "https", "socks4", "socks5"]:
        txt = fetch(f"https://www.proxyscan.io/api/proxy?format=txt&country=US&type={type_}&level=anonymous", timeout=8)
        for line in txt.strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                results.add(line)
    return results

def scrape_spys():
    """spys.me — SOCKS5 proxy list"""
    results = set()
    txt = fetch("https://spys.me/socks.txt")
    for line in txt.strip().splitlines():
        line = line.strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+", line):
            parts = line.split()
            ip_port = parts[0]
            if len(parts) > 1 and "US" in parts[1].upper():
                results.add(ip_port)
            elif len(parts) <= 1:
                results.add(ip_port)
    return results

def scrape_spys_http():
    """spys.me — HTTP/HTTPS proxy list"""
    results = set()
    txt = fetch("https://spys.me/proxy.txt")
    for line in txt.strip().splitlines():
        line = line.strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+", line):
            parts = line.split()
            ip_port = parts[0]
            if len(parts) > 1 and "US" in parts[1].upper():
                results.add(ip_port)
            elif len(parts) <= 1:
                results.add(ip_port)
    return results

def scrape_sslproxies():
    """sslproxies.org"""
    results = set()
    txt = fetch("https://www.sslproxies.org/")
    results.update(parse_proxies(txt, r"<td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>"))
    return results

def scrape_free_proxy_list():
    """free-proxy-list.net"""
    results = set()
    txt = fetch("https://free-proxy-list.net/")
    results.update(parse_proxies(txt, r"<td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>"))
    return results

def scrape_us_proxy():
    """us-proxy.org"""
    results = set()
    txt = fetch("https://www.us-proxy.org/")
    results.update(parse_proxies(txt, r"<td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>"))
    return results

def scrape_proxydb():
    """proxydb.net"""
    results = set()
    for proto in ["http", "https", "socks4", "socks5"]:
        txt = fetch(f"https://proxydb.net/?country=US&protocol={proto}&anonlvl=2&offset=0", timeout=8)
        results.update(parse_proxies(txt, r"(\d+\.\d+\.\d+\.\d+):(\d+)"))
    return results

def scrape_socks_proxy():
    """socks-proxy.net"""
    results = set()
    txt = fetch("https://www.socks-proxy.net/")
    results.update(parse_proxies(txt, r"<td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>"))
    return results

def scrape_roosterkid():
    """roosterkid/openproxylist GitHub"""
    results = set()
    for url in [
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTP.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5.txt",
    ]:
        txt = fetch(url)
        for line in txt.strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                results.add(line)
    return results

def scrape_hide_my_name():
    """hidemy.name"""
    results = set()
    for page in range(1, 4):
        txt = fetch(f"https://hidemy.name/en/proxy-list/?country=US&start={page}5", timeout=8)
        results.update(parse_proxies_with_country(txt, r"(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td><td>(\w+.*?)</td>", country_field=2))
    return results

def scrape_pubproxy():
    """pubproxy.com API"""
    results = set()
    txt = fetch("https://pubproxy.com/api/proxy?limit=20&country=US&format=txt", timeout=8)
    for line in txt.strip().splitlines():
        line = line.strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
            results.add(line)
    return results

# ============================================================
# MAIN
# ============================================================

SOURCES = [
    ("ProxyScrape", scrape_proxyscrape),
    ("TheSpeedX", scrape_thespeedx),
    ("jetkai", scrape_jetkai),
    ("free-proxy-list", scrape_free_proxy_list),
    ("us-proxy.org", scrape_us_proxy),
    ("socks-proxy", scrape_socks_proxy),
    ("sslproxies", scrape_sslproxies),
    ("spys HTTP", scrape_spys_http),
    ("spys SOCKS", scrape_spys),
    ("GeoNode", scrape_geonode),
    ("ProxyScan", scrape_proxyscan),
    ("ProxyDB", scrape_proxydb),
    ("openproxy", scrape_openproxy),
    ("roosterkid", scrape_roosterkid),
    ("hide.my.name", scrape_hide_my_name),
    ("pubproxy", scrape_pubproxy),
]

def run():
    print(f"🔍 Scraping {len(SOURCES)} sources for USA proxies...")
    
    all_proxies = set()
    source_stats = {}

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn): name for name, fn in SOURCES}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                proxies = fut.result()
                print(f"  {name}: {len(proxies)} proxies")
                all_proxies.update(proxies)
                source_stats[name] = len(proxies)
            except Exception as e:
                print(f"  {name}: ❌ {e}")

    print(f"\n📦 Total unique: {len(all_proxies)}")
    
    # Save
    output = {
        "scraped_at": datetime.utcnow().isoformat(),
        "total": len(all_proxies),
        "sources": source_stats,
        "proxies": sorted(all_proxies)
    }
    OUT.write_text(json.dumps(output, indent=2))
    print(f"💾 Saved to {OUT}")
    
    # Show top sources
    print(f"\n📊 Top sources:")
    for name, count in sorted(source_stats.items(), key=lambda x: -x[1])[:5]:
        print(f"  {name}: {count}")

if __name__ == "__main__":
    run()
