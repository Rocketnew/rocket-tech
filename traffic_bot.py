#!/usr/bin/env python3
"""
Rocket Bot v5 — Clean Selenium traffic bot
- No nested retries, no bloat
- /tmp cleanup at startup
- Real HTTPS CONNECT proxy test
- Re-injects ad scripts after React hydration
"""

import json, time, random, socket, sys, os, subprocess
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ──
SITE = "https://rocketnewsdaily.vercel.app"
CHROME_BIN = "/home/ubuntu/chromium/chrome-linux64/chrome"
CHROMEDRIVER = "/tmp/chromedriver"
PROFILES_DIR = Path.home() / ".rocket-traffic-profile"
PROXIES_FILE = PROFILES_DIR / "proxies.json"
FINGERPRINT_FILE = PROFILES_DIR / "fingerprint.json"
PROFILES_DIR.mkdir(exist_ok=True)

VIEWPORTS = [(390, 844), (375, 812), (414, 896)]  # Mobile-first — Monetag ads show in phone viewport
MOBILE_UAS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
]
UAS = MOBILE_UAS

# ── Proxy Helpers ──

def load_proxies():
    if not PROXIES_FILE.exists():
        return []
    try:
        data = json.loads(PROXIES_FILE.read_text())
        raw = data if isinstance(data, list) else data.get("proxies", [])
        # Convert string format "ip:port" to dict format {ip, port, protocol}
        result = []
        for item in raw:
            if isinstance(item, dict):
                item["protocol"] = item.get("protocol", "socks5")
                result.append(item)
            elif isinstance(item, str) and ":" in item:
                parts = item.rsplit(":", 1)
                result.append({"ip": parts[0], "port": parts[1], "protocol": "socks5"})
        return result
    except:
        return []

def test_proxy_connect(proxy, timeout=3):
    """HTTPS CONNECT test via raw socket"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((proxy['ip'], int(proxy['port'])))
        if proxy.get('protocol') in ('socks5', 'socks'):
            s.sendall(b'\x05\x02\x00\x02')
            resp = s.recv(2)
            s.close()
            return resp == b'\x05\x00'
        s.sendall(b"CONNECT rocketnewsdaily.vercel.app:443 HTTP/1.1\r\n"
                  b"Host: rocketnewsdaily.vercel.app:443\r\n"
                  b"Proxy-Connection: Keep-Alive\r\n\r\n")
        resp = s.recv(32)
        s.close()
        return b"200" in resp
    except:
        return False

def find_working_proxy(proxies, max_checks=20):
    """Test up to max_checks proxies, return first working one"""
    pool = list(proxies)
    random.shuffle(pool)
    for p in pool[:max_checks]:
        if test_proxy_connect(p):
            return p
    return None

# ── Chrome Launcher ──

def launch_chrome(fp, proxy=None, max_retries=3):
    """Start Chrome headless with retry on startup crash"""
    for attempt in range(max_retries):
        try:
            import tempfile, uuid
            chrome_dir = tempfile.mkdtemp(prefix=f"cr_{uuid.uuid4().hex[:8]}_")
            vp = fp.get("viewport", [1280, 720])
            opts = Options()
            opts.binary_location = CHROME_BIN
            opts.add_argument(f"--user-data-dir={chrome_dir}")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--disable-popup-blocking")
            opts.add_argument("--disable-notifications")
            opts.add_argument("--disable-background-networking")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--no-first-run")
            opts.add_argument("--mute-audio")
            opts.add_argument(f"--window-size={vp[0]},{vp[1]}")
            opts.add_argument(f"--user-agent={fp['ua']}")
            opts.add_argument("--ignore-certificate-errors")
            opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            opts.add_experimental_option("useAutomationExtension", False)

            if proxy and proxy.get("ip"):
                proto = proxy.get("protocol", "http").lower()
                if proto.startswith("socks"):
                    proxy_str = f"socks5://{proxy['ip']}:{proxy['port']}"
                else:
                    proxy_str = f"http://{proxy['ip']}:{proxy['port']}"
                opts.add_argument(f"--proxy-server={proxy_str}")

            driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=opts)
            driver._proxy_set = bool(proxy and proxy.get("ip"))
            driver.set_page_load_timeout(12)
            return driver
        except Exception as e:
            err = str(e).lower()
            if attempt < max_retries - 1 and ('tab crashed' in err or 'invalid session' in err
                                               or 'cannot connect' in err or 'session deleted' in err):
                print(f"  🔄 Chrome startup crash (attempt {attempt+1}/{max_retries})")
                time.sleep(1)
                continue
            raise
    return None

# ── Stealth JS ──

def build_stealth_js(fp):
    """Build stealth injection JS for the specific fingerprint"""
    return f"""
    Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
    Object.defineProperty(navigator, 'plugins', {{get: () => [1,2,3,4,5]}});
    Object.defineProperty(navigator, 'languages', {{get: () => ['en-US', 'en']}});
    Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {random.randint(4, 16)}}});
    Object.defineProperty(navigator, 'deviceMemory', {{get: () => {random.choice([4, 8])}}});
    // Hide headless chrom
    window.chrome = {{runtime: {{}}}};
    """

# ── Page Visit ──

def find_ad_elements(driver):
    """Find Monetag injected ad elements on the page"""
    try:
        all_ads = []
        
        # Strategy 1: Look for iframes dynamically added (Monetag ads often in iframes)
        try:
            iframes = driver.execute_script("""
                var results = [];
                var ifs = document.querySelectorAll('iframe');
                for (var i = 0; i < ifs.length; i++) {
                    var f = ifs[i];
                    var r = f.getBoundingClientRect();
                    if (r.top < window.innerHeight && r.bottom > 0) {
                        results.push({tag: 'iframe', x: parseInt(r.x + r.width/2), y: parseInt(r.top + r.height/2), w: f.offsetWidth, h: f.offsetHeight, el: f});
                    }
                }
                return results;
            """)
            if iframes:
                all_ads.extend(iframes)
        except:
            pass
        
        # Strategy 2: Look for fixed/absolute positioned divs with high z-index (overlay ads)
        try:
            overlays = driver.execute_script("""
                var results = [];
                var all = document.querySelectorAll('div, section, ins');
                for (var i = 0; i < all.length; i++) {
                    var e = all[i];
                    var cs = window.getComputedStyle(e);
                    var z = parseInt(cs.zIndex) || 0;
                    if ((cs.position === 'fixed' || z > 100) && e.offsetWidth > 50 && e.offsetHeight > 30) {
                        var r = e.getBoundingClientRect();
                        if (r.top < 300 && r.bottom > 0) {
                            results.push({
                                el: e, tag: e.tagName.toLowerCase(),
                                x: parseInt(r.x + r.width/2), y: parseInt(r.top + r.height/2),
                                w: e.offsetWidth, h: e.offsetHeight, z: z
                            });
                        }
                    }
                }
                return results;
            """)
            if overlays:
                all_ads.extend(overlays)
        except:
            pass
        
        # Strategy 3: Look for any element with Monetag/PP/ad-related classes/ids
        try:
            monetag_els = driver.execute_script("""
                var results = [];
                var selectors = 'div[id*="pp_"], div[class*="pp_"], iframe[id*="pp_"], ' +
                    'div[id*="monetag"], div[class*="monetag"], ' +
                    'ins[class*="ads"], div[id*="ad_"], div[class*="ad_"]';
                var els = document.querySelectorAll(selectors);
                for (var i = 0; i < els.length; i++) {
                    var e = els[i];
                    var r = e.getBoundingClientRect();
                    if (r.top < window.innerHeight && r.bottom > 0 && e.offsetWidth > 30) {
                        results.push({
                            el: e, tag: e.tagName.toLowerCase(),
                            x: parseInt(r.x + r.width/2), y: parseInt(r.top + r.height/2),
                            w: e.offsetWidth, h: e.offsetHeight
                        });
                    }
                }
                return results;
            """)
            if monetag_els:
                all_ads.extend(monetag_els)
        except:
            pass
        
        # Deduplicate by position proximity
        deduped = []
        for a in all_ads:
            dup = False
            for d in deduped:
                if abs(a['x'] - d['x']) < 30 and abs(a['y'] - d['y']) < 30:
                    dup = True
                    break
            if not dup:
                deduped.append(a)
        
        return deduped
    except:
        return []

def click_element_at(driver, x, y):
    """Click at page coordinates using ActionChains"""
    from selenium.webdriver.common.action_chains import ActionChains
    try:
        actions = ActionChains(driver)
        # Move to coordinate and click
        driver.execute_script(f"window.scrollTo(0, 0);")
        time.sleep(0.3)
        actions.move_by_offset(x, y).click().perform()
        # Reset mouse position
        actions.move_by_offset(-x, -y).perform()
        return True
    except:
        return False

def do_visit(driver):
    """Full page visit with ad click focus — mobile viewport, wait for Monetag ads"""
    try:
        driver.get(SITE)
    except Exception as e:
        err = str(e).lower()
        is_proxy_err = ('proxy' in err or 'err_tunnel' in err 
                        or 'err_connection' in err or 'name not resolved' in err)
        if 'timeout' in err:
            is_proxy_err = driver._proxy_set if hasattr(driver, '_proxy_set') else False
        return {"ok": False, "proxy_err": is_proxy_err}

    # Wait ~1.5s for Monetag ads to start loading
    wait_time = random.uniform(1.0, 1.8)
    time.sleep(wait_time)

    # Hijack — scroll to top so header/ad area is visible
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)

    # Re-inject Monetag scripts (React hydration removes them)
    driver.execute_script("""
        ['https://auqot.com/pfe/current/tag.min.js?z=11121546',
         'https://jmosl.com/vignette.min.js?z=11121545',
         'https://094kk.com/tag.min.js?z=11121544'].forEach(function(src) {
            var domain = src.split('/')[2];
            if (!document.querySelector('script[src*="' + domain + '"]')) {
                var s = document.createElement('script');
                s.src = src; s.async = true;
                document.head.appendChild(s);
            }
        });
    """)
    
    # Wait for injected scripts to load
    time.sleep(random.uniform(0.5, 1.2))
    
    # Scroll slowly through page (human-like, also helps trigger ads)
    for _ in range(random.randint(1, 2)):
        driver.execute_script(f"window.scrollBy(0, {random.randint(100, 250)})")
        time.sleep(random.uniform(0.3, 0.5))
    
    # Scroll back to top where Monetag ads appear
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)

    # ─── Try to find and click Monetag ads ───
    clicks = 0
    try:
        ad_elements = find_ad_elements(driver)
        
        if ad_elements:
            # Click Monetag ads first
            for ad in ad_elements[:2]:
                try:
                    el = ad.get('el')
                    if el:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                        time.sleep(0.3)
                        el.click()
                    else:
                        # Click at coordinates
                        driver.execute_script(f"window.scrollTo(0, 0);")
                        click_element_at(driver, ad['x'], ad['y'])
                    clicks += 1
                    print(f"    🖱️ Ad Click: {ad.get('tag','ad')} @({ad['x']},{ad['y']})")
                    time.sleep(random.uniform(0.5, 1.2))
                except:
                    continue
        else:
            # Fallback: click on the TOP area where ads should be
            # On mobile (390x844 viewport), ads appear in top 15-30% 
            vp_height = 844  # mobile viewport
            ad_y = int(vp_height * random.uniform(0.12, 0.28))
            ad_x = random.randint(60, vp_height - 60) if vp_height > 300 else 150
            # Try to click at the ad area
            if click_element_at(driver, ad_x, ad_y):
                clicks += 1
                print(f"    🖱️ Area Click: @({ad_x},{ad_y})")
                time.sleep(random.uniform(0.5, 1.0))
            
            # Fallback to article link clicks
            links = driver.find_elements(By.TAG_NAME, "a")
            ext_links = []
            for l in links:
                href = l.get_attribute("href")
                if href and "://" in href and "rocketnewsdaily" not in href and "quge5" not in href:
                    ext_links.append(l)
            random.shuffle(ext_links)

            for link in ext_links[:1]:  # Only 1 fallback click per visit
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    driver.execute_script("window.open(arguments[0], '_blank');", href)
                    time.sleep(random.uniform(0.5, 1))
                    handles = driver.window_handles
                    if len(handles) > 1:
                        driver.switch_to.window(handles[-1])
                        time.sleep(0.5)
                        driver.close()
                        driver.switch_to.window(handles[0])
                    clicks += 1
                    print(f"    🖱️ Click: {href.split('//')[1][:40]}")
                except:
                    continue
    except Exception:
        pass

    return {"ok": True, "clicks": clicks, "proxy_err": False}

# ── Score Check ──

def check_score(driver):
    """Run stealth checks and return score 0-10"""
    try:
        result = driver.execute_script("""
            var flags = [];
            if (navigator.webdriver === true || navigator.webdriver === undefined) flags.push(0);
            if (navigator.plugins.length === 0) flags.push(1);
            if (!navigator.languages || navigator.languages.length === 0) flags.push(2);
            if (window.chrome === undefined) flags.push(3);
            return {score: 10 - flags.length, flags: flags};
        """)
        return result.get("score", 5)
    except:
        return 0

# ── Main ──

def gen_fingerprint():
    vp = random.choice(VIEWPORTS)
    ua = random.choice(UAS)
    platform = "iPhone" if "iPhone" in ua else "Android" if "Android" in ua else "Win32"
    return {
        "ua": ua,
        "viewport": vp,
        "platform": platform,
    }

def main():
    # ─── Cleanup ───
    subprocess.run(["killall", "-q", "chrome"], capture_output=True, timeout=5)
    subprocess.run(["killall", "-q", "chromedriver"], capture_output=True, timeout=5)
    import shutil
    for p in Path("/tmp").iterdir():
        if p.name.startswith("cr_") or ".com.google.Chrome" in p.name:
            try: shutil.rmtree(p)
            except: pass
    time.sleep(1)

    # ─── Setup ───
    fp = gen_fingerprint()
    FINGERPRINT_FILE.write_text(json.dumps(fp))

    proxies = load_proxies()
    proxy = None
    if proxies and False:  # Direct mode — skip proxy search
        proxy = find_working_proxy(proxies, max_checks=15)

    protocol = proxy.get('protocol', 'direct').upper()[:6] if proxy else 'DIRECT'
    print(f"==================================================")
    print(f"🚀 ROCKET BOT v5")
    print(f"==================================================")
    print(f"  📦 Proxies: {len(proxies)}")
    print(f"  🔌 Proxy: direct (stable)")

    # ─── Launch Chrome ───
    driver = launch_chrome(fp, None)

    try:
        # ─── Stealth injection ───
        stealth_js = build_stealth_js(fp)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": stealth_js})
        driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
            "userAgent": fp["ua"],
            "platform": fp["platform"],
        })

        # ─── Visit cycle ───
        start = time.time()
        total_clicks = 0
        visit_count = 0

        for visit_num in range(1, 4):  # 3 visits per cycle
            visit_count = visit_num
            print(f"\n  📄 Visit {visit_num}")
            result = do_visit(driver)
            if not result["ok"]:
                print(f"    ❌ Visit failed (proxy: {result['proxy_err']})")
                if result["proxy_err"] and proxy:
                    print(f"    🔄 Proxy failed, switching to direct")
                    driver.quit()
                    driver = launch_chrome(fp, None)
                    if not driver:
                        break
                    stealth_js = build_stealth_js(fp)
                    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": stealth_js})
                    driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
                        "userAgent": fp["ua"], "platform": fp["platform"],
                    })
                    proxy = None
                    result = do_visit(driver)
                if not result["ok"]:
                    continue
            total_clicks += result.get("clicks", 0)
            time.sleep(random.uniform(1, 2))

        # ─── Score ───
        score = check_score(driver)
        elapsed = round(time.time() - start, 1)
        print(f"  🧬 Score: {score}/10")
        print(f"  🖥️ Visits: {visit_count} | Clicks: {total_clicks} | ⏱️ {elapsed}s")

    except Exception as e:
        print(f"  ❌ Error: {str(e)[:80]}")
    finally:
        try: driver.quit()
        except: pass

    print(f"  ✅ Done")

if __name__ == "__main__":
    main()
