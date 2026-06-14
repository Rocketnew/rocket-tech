#!/usr/bin/env python3
"""
Rocket Bot Security Evolution Engine v2
- Runs every 5 min, tests stealth, logs proxy stats
- Telegram-friendly compact output
"""

import json, time, random, subprocess, sys, os, signal
from datetime import datetime
from pathlib import Path

PROFILE_DIR = Path.home() / ".rocket-traffic-profile"
PROFILE_DIR.mkdir(exist_ok=True)
EVOLUTION_LOG = PROFILE_DIR / "evolution.json"
PROXY_STATS_FILE = PROFILE_DIR / "proxy_stats.json"
PROXIES_FILE = PROFILE_DIR / "proxies.json"
SCRIPT = os.path.expanduser("~/rocket-tech/traffic_bot.py")
PROXY_SCRIPT = os.path.expanduser("~/rocket-tech/proxy_scraper.py")

PROXY_REFRESH_INTERVAL = 5  # every 5th cycle (25 min)


def cleanup_chrome():
    """Kill leftover Chrome processes before starting fresh"""
    try:
        subprocess.run(
            ["killall", "-q", "chrome", "chromedriver"],
            capture_output=True, timeout=5
        )
        subprocess.run(
            ["killall", "-q", "chromedriver"],
            capture_output=True, timeout=5
        )
    except:
        pass
    time.sleep(2)


def load_evolution():
    if EVOLUTION_LOG.exists():
        try:
            return json.loads(EVOLUTION_LOG.read_text())
        except: pass
    return {"runs": [], "best_score": 0, "best_fp": None, "total_runs": 0, "total_clicks": 0}


def save_evolution(data):
    data["runs"] = data["runs"][-500:]
    EVOLUTION_LOG.write_text(json.dumps(data, indent=2))


def load_proxy_stats():
    if PROXY_STATS_FILE.exists():
        try:
            return json.loads(PROXY_STATS_FILE.read_text())
        except: pass
    return {"proxies": {}, "total_attempts": 0, "total_failures": 0}


def save_proxy_stats(data):
    # Trim old entries (keep last 100 proxies)
    if len(data["proxies"]) > 100:
        data["proxies"] = dict(list(data["proxies"].items())[-100:])
    PROXY_STATS_FILE.write_text(json.dumps(data, indent=2))


def get_proxy_pool_info():
    """Return count by protocol"""
    if not PROXIES_FILE.exists():
        return None, {}
    try:
        data = json.loads(PROXIES_FILE.read_text())
        proxies = data if isinstance(data, list) else data.get("proxies", [])
        counts = {}
        for p in proxies:
            proto = p.get("protocol", "unknown")
            counts[proto] = counts.get(proto, 0) + 1
        return len(proxies), counts
    except:
        return None, {}


def compute_stats(data):
    scores = [r.get("score", 0) for r in data["runs"]]
    run_times = [r.get("elapsed", 0) for r in data["runs"]]
    recent = data["runs"][-20:] if len(data["runs"]) > 20 else data["runs"]
    recent_scores = [r.get("score", 0) for r in recent]
    
    return {
        "total_runs": data["total_runs"],
        "total_clicks": data["total_clicks"],
        "best_score": data["best_score"],
        "avg_score": round(sum(scores)/len(scores), 1) if scores else 0,
        "avg_recent_score": round(sum(recent_scores)/len(recent_scores), 1) if recent_scores else 0,
        "avg_time": round(sum(run_times)/len(run_times), 1) if run_times else 0,
        "last_run": data["runs"][-1]["time"] if data["runs"] else "Never",
    }


def main():
    evo = load_evolution()
    pstats = load_proxy_stats()
    
    # Clean up leftover Chrome processes before each run
    cleanup_chrome()
    
    # ─── Run the traffic bot ───
    start = time.time()
    result = subprocess.run(
        [sys.executable, SCRIPT],
        capture_output=True, text=True, timeout=180
    )
    elapsed = round(time.time() - start, 1)
    output = result.stdout
    
    # ─── Parse results ───
    score = 0
    for line in output.split('\n'):
        if 'Score:' in line:
            try: score = int(line.split(':')[1].strip().split('/')[0])
            except: pass
    
    clicks = 0
    for line in output.split('\n'):
        if 'click' in line.lower() and '✅' in line:
            try:
                for p in line.split(','):
                    if 'click' in p:
                        clicks = int(p.split(':')[-1].strip().split()[0])
            except: pass
    
    # Parse proxy info
    proxy_str = "direct"
    visits = 0
    for line in output.split('\n'):
        if 'Using proxy:' in line:
            try: proxy_str = line.split('proxy:')[1].strip()
            except: pass
        if 'visit(s)' in line:
            try: visits = int(line.strip().split()[1])
            except: pass
    
    # Track proxy success
    proxy_success = '❌' not in output.split('--- Visit')[1] if '--- Visit' in output and proxy_str != "direct" else True
    
    pstats["total_attempts"] += 1
    if not proxy_success:
        pstats["total_failures"] += 1
    
    # Track per-proxy stats
    if proxy_str != "direct":
        pkey = proxy_str.replace("HTTP ", "").replace("SOCKS5 ", "").strip()
        if pkey:
            if pkey not in pstats["proxies"]:
                pstats["proxies"][pkey] = {"uses": 0, "fails": 0}
            pstats["proxies"][pkey]["uses"] += 1
            if not proxy_success:
                pstats["proxies"][pkey]["fails"] += 1
    save_proxy_stats(pstats)
    
    # ─── Record run ───
    run = {
        "time": datetime.now().isoformat(),
        "score": score,
        "elapsed": elapsed,
        "clicks": clicks,
        "proxy": proxy_str,
        "visits": visits,
    }
    evo["runs"].append(run)
    evo["total_runs"] += 1
    evo["total_clicks"] += clicks
    
    if score > evo["best_score"]:
        evo["best_score"] = score
        evo["best_fp"] = run
    
    stats = compute_stats(evo)
    
    # ─── Proxy refresh ───
    proxy_refreshed = False
    pool_count, pool_protos = get_proxy_pool_info()
    if evo["total_runs"] % PROXY_REFRESH_INTERVAL == 0:
        try:
            subprocess.run(
                [sys.executable, PROXY_SCRIPT],
                capture_output=True, text=True, timeout=60
            )
            proxy_refreshed = True
            pool_count, pool_protos = get_proxy_pool_info()
        except: pass
    
    proxy_runs = sum(1 for r in evo["runs"] if r.get("proxy", "direct") != "direct")
    proxy_fail_pct = round(pstats["total_failures"] / max(pstats["total_attempts"], 1) * 100)
    
    # ─── Telegram-friendly output ───
    print(f"🤖 Rocket Bot Update #{evo['total_runs']}")
    print(f"")
    print(f"🛡️ Score: {score}/10 | {visits} visits | {clicks} clicks | {elapsed}s")
    print(f"🔌 Proxy: {proxy_str}")
    print(f"")
    
    # Proxy health
    print(f"🌐 Proxy Health:")
    print(f"   ├─ Pool: {pool_count or '?'} USA proxies")
    print(f"   ├─ Active: {proxy_runs}/{stats['total_runs']} runs via proxy")
    if proxy_str != "direct":
        pkey_short = proxy_str.replace("HTTP ", "").replace("SOCKS5 ", "").strip()
        pinfo = pstats["proxies"].get(pkey_short, {})
        puses = pinfo.get("uses", 0)
        pfails = pinfo.get("fails", 0)
        pstatus = "✅" if proxy_success else "❌"
        print(f"   └─ This proxy: used {puses}x | {pfails} fails | last: {pstatus}")
    else:
        print(f"   └─ Direct (no proxy available)")
    print(f"")
    
    # Overall stats
    print(f"📊 Overall ({stats['total_runs']} runs):")
    print(f"   ├─ Avg score: {stats['avg_score']}/10")
    if proxy_runs > 0:
        print(f"   ├─ Proxy success: {100-proxy_fail_pct}% ({proxy_runs - pstats['total_failures']} ok / {proxy_runs} total)")
    print(f"   ├─ Avg runtime: {stats['avg_time']}s")
    print(f"   └─ Clicks: {stats['total_clicks']} total")
    print(f"")
    
    if proxy_refreshed and pool_count:
        proto_str = ", ".join([f"{k.upper()}: {v}" for k, v in (pool_protos or {}).items()])
        print(f"📡 Proxy pool refreshed: {pool_count} proxies ({proto_str})")
        print(f"")
    
    # Score warning
    if score < 7:
        print(f"⚠️ Low score! Evolve...")
        fp_file = PROFILE_DIR / "fingerprint.json"
        if fp_file.exists():
            fp_file.unlink()
    
    if len(evo["runs"]) >= 3:
        recent_avg = stats['avg_recent_score']
        if recent_avg < 7:
            print(f"⚠️ Score drop! Recent avg: {recent_avg}/10 — cache cleared")
            fp_file = PROFILE_DIR / "fingerprint.json"
            if fp_file.exists():
                fp_file.unlink()
    
    save_evolution(evo)


if __name__ == "__main__":
    main()
