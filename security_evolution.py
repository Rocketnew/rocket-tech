#!/usr/bin/env python3
"""
Rocket Bot Security Evolution Engine
Runs every 5 min, tests stealth, improves, logs everything
"""

import json, time, random, subprocess, sys, os
from datetime import datetime
from pathlib import Path

PROFILE_DIR = Path.home() / ".rocket-traffic-profile"
PROFILE_DIR.mkdir(exist_ok=True)
EVOLUTION_LOG = PROFILE_DIR / "evolution.json"
SCRIPT = os.path.expanduser("~/rocket-tech/traffic_bot.py")
PROXY_SCRIPT = os.path.expanduser("~/rocket-tech/proxy_scraper.py")

# Proxy refresh: every 5th cycle (25 min)
PROXY_REFRESH_INTERVAL = 5


def load_evolution():
    if EVOLUTION_LOG.exists():
        try:
            return json.loads(EVOLUTION_LOG.read_text())
        except: pass
    return {"runs": [], "best_score": 0, "best_fp": None, "total_runs": 0, "total_clicks": 0}


def save_evolution(data):
    # Keep last 500 runs
    data["runs"] = data["runs"][-500:]
    EVOLUTION_LOG.write_text(json.dumps(data, indent=2))


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
        "score_trend": "📈" if len(recent_scores) >= 5 and recent_scores[-1] > recent_scores[0] else ("📉" if len(recent_scores) >= 5 and recent_scores[-1] < recent_scores[0] else "➡️"),
        "last_run": data["runs"][-1]["time"] if data["runs"] else "Never",
    }


def main():
    evo = load_evolution()
    
    print(f"🤖 ROCKET BOT EVOLUTION ENGINE")
    print(f"{'='*45}")
    print(f"📊 Already done: {evo['total_runs']} runs | {evo['total_clicks']} clicks")
    if evo["runs"]:
        last = evo["runs"][-1]
        print(f"📈 Last score: {last.get('score', '?')}/10 | time: {last.get('elapsed', '?')}s")
    print()
    
    # Run the traffic bot
    start = time.time()
    result = subprocess.run(
        [sys.executable, SCRIPT],
        capture_output=True, text=True, timeout=120
    )
    elapsed = time.time() - start
    
    # Parse score from output
    score = 0
    for line in result.stdout.split('\n'):
        if 'Score:' in line:
            try:
                score = int(line.split(':')[1].strip().split('/')[0])
            except: pass
    
    # Parse clicks
    clicks = 0
    for line in result.stdout.split('\n'):
        if 'click' in line.lower() and '✅' in line:
            try:
                parts = line.split(',')
                for p in parts:
                    if 'click' in p:
                        clicks = int(p.split(':')[-1].strip().split()[0])
            except: pass
    
    # Parse proxy usage from output
    used_proxy = None
    for line in result.stdout.split('\n'):
        if 'Using proxy:' in line:
            try:
                used_proxy = line.split('proxy:')[1].strip()
            except: pass
    
    # Record this run
    run = {
        "time": datetime.now().isoformat(),
        "score": score,
        "elapsed": round(elapsed, 1),
        "clicks": clicks,
        "proxy": used_proxy or "direct",
    }
    evo["runs"].append(run)
    evo["total_runs"] += 1
    evo["total_clicks"] += clicks
    
    if score > evo["best_score"]:
        evo["best_score"] = score
        evo["best_fp"] = run
        print(f"\n🎯 NEW BEST! Score: {score}/10")
        
        # Save fingerprint if it was good
        fp_file = PROFILE_DIR / "fingerprint.json"
        if fp_file.exists():
            print(f"📌 Fingerprint locked for future runs")
    
    # Compute and log stats
    stats = compute_stats(evo)
    
    # Check if we should refresh proxies (every 5th cycle)
    proxy_refreshed = False
    if evo["total_runs"] % PROXY_REFRESH_INTERVAL == 0:
        print(f"\n📡 Refreshing proxy list...")
        try:
            proxy_result = subprocess.run(
                [sys.executable, PROXY_SCRIPT],
                capture_output=True, text=True, timeout=60
            )
            print(proxy_result.stdout.strip())
            proxy_refreshed = True
        except subprocess.TimeoutExpired:
            print(f"  ⏰ Proxy refresh timed out")
        except Exception as e:
            print(f"  ❌ Proxy refresh failed: {e}")
    
    # Count proxy vs direct runs
    proxy_runs = sum(1 for r in evo["runs"] if r.get("proxy", "direct") != "direct")
    
    print(f"\n{'='*45}")
    print(f"📊 EVOLUTION REPORT")
    print(f"   Total runs: {stats['total_runs']}")
    print(f"   Total clicks: {stats['total_clicks']}")
    print(f"   Best score: {stats['best_score']}/10")
    print(f"   Avg score: {stats['avg_score']}/10")
    print(f"   Recent avg: {stats['avg_recent_score']}/10 {stats['score_trend']}")
    print(f"   Avg runtime: {stats['avg_time']}s")
    print(f"   Proxy runs: {proxy_runs}/{stats['total_runs']}")
    print(f"   Last run: {stats['last_run']}")
    if proxy_refreshed:
        try:
            pf = PROFILE_DIR / "proxies.json"
            if pf.exists():
                data = json.loads(pf.read_text())
                print(f"   Proxy pool: {data['count']} USA proxies")
        except: pass
    print(f"{'='*45}")
    
    save_evolution(evo)
    
    # Alert if score drops significantly
    if len(evo["runs"]) >= 3:
        recent_avg = stats['avg_recent_score']
        if recent_avg < 7:
            print(f"\n⚠️  SCORE DROP DETECTED! Recent avg: {recent_avg}/10")
            print(f"   Clearing fingerprint cache...")
            fp_file = PROFILE_DIR / "fingerprint.json"
            if fp_file.exists():
                fp_file.unlink()
            print(f"   ✅ Cache cleared — next run will use fresh fingerprint")


if __name__ == "__main__":
    main()
