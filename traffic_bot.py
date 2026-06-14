#!/usr/bin/env python3
"""
Rocket News Adaptive Stealth Bot v3 — 2026
- 20+ browser fingerprint vectors covered
- Prototype-based webdriver hiding
- Canvas/WebGL/Audio spoofing
- Self scoring + continuous improvement
- Persistent fingerprint profile
"""

import sys, os, random, time, json, warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ["WDM_LOG"] = "0"

SITE = "https://rocketnewsdaily.vercel.app"
PROFILE_DIR = Path.home() / ".rocket-traffic-profile"
PROFILE_DIR.mkdir(exist_ok=True)
FINGERPRINT_FILE = PROFILE_DIR / "fingerprint.json"

FINGERPRINTS = [
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "platform": "Win32", "vendor": "Google Inc.",
        "renderer": "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)",
        "vendor_fl": "Google Inc. (Intel)", "plugins": 5, "mimetypes": 4,
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "platform": "MacIntel", "vendor": "Google Inc.",
        "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 OpenGL Engine)",
        "vendor_fl": "Google Inc. (Apple)", "plugins": 5, "mimetypes": 3,
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
        "platform": "Win32", "vendor": "",
        "renderer": "", "vendor_fl": "", "plugins": 5, "mimetypes": 3,
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "platform": "Win32", "vendor": "Google Inc.",
        "renderer": "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)",
        "vendor_fl": "Google Inc. (Intel)", "plugins": 5, "mimetypes": 3,
    },
]

VIEWPORTS = [
    (1366, 768), (1920, 1080), (1536, 864), (1440, 900),
    (1280, 720), (1600, 900), (1024, 768),
]

CHROMEDRIVER = "/snap/chromium/3459/usr/lib/chromium-browser/chromedriver"


def build_stealth_js(fp):
    """Build complete stealth patch script with ALL anti-detection techniques"""
    ua = fp["ua"]
    plat = fp["platform"]
    vend = fp["vendor"]
    rend = fp["renderer"]
    vfl = fp["vendor_fl"]
    plen = fp["plugins"]
    mlen = fp["mimetypes"]

    return f"""
try {{
// === WEBDRIVER (prototype-chain override — survives page loads) ===
Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver', {{
    get: () => undefined,
    configurable: true
}});

// === USER AGENT + PLATFORM + VENDOR ===
try {{ Object.defineProperty(navigator.__proto__, 'userAgent', {{get: () => '{ua}', configurable: true}}); }} catch(e){{}}
try {{ Object.defineProperty(navigator.__proto__, 'platform', {{get: () => '{plat}', configurable: true}}); }} catch(e){{}}
try {{ Object.defineProperty(navigator.__proto__, 'vendor', {{get: () => '{vend}', configurable: true}}); }} catch(e){{}}
try {{ Object.defineProperty(navigator.__proto__, 'appVersion', {{get: () => navigator.userAgent, configurable: true}}); }} catch(e){{}}

// === PLUGINS ===
class _P {{ constructor(n) {{ this.name=n; this.filename=n+'.dll'; this.length=0; }} }}
try {{ Object.defineProperty(navigator.__proto__, 'plugins', {{
    get: () => {{
        let arr = [new _P('Chrome PDF Plugin'), new _P('Chrome PDF Viewer'), new _P('Native Client')];
        while (arr.length < {plen}) arr.push(new _P('Plugin ' + arr.length));
        arr.item = i => arr[i]; arr.namedItem = n => arr.find(x => x.name === n); arr.refresh = () =>{{}};
        return arr;
    }}, configurable: true
}}); }} catch(e){{}}

// === MIME TYPES ===
class _MT {{ constructor(t) {{ this.type=t; this.suffixes=''; this.enabledPlugin=new _P(t); }} }}
try {{ Object.defineProperty(navigator.__proto__, 'mimeTypes', {{
    get: () => {{
        let arr = [new _MT('application/pdf'), new _MT('text/pdf')];
        while (arr.length < {mlen}) arr.push(new _MT('application/x-type-' + arr.length));
        arr.item = i => arr[i]; arr.namedItem = n => arr.find(x => x.type === n); return arr;
    }}, configurable: true
}}); }} catch(e){{}}

// === LANGUAGES ===
try {{ Object.defineProperty(navigator.__proto__, 'languages', {{get: () => ['en-US','en'], configurable: true}}); }} catch(e){{}}
try {{ Object.defineProperty(navigator.__proto__, 'language', {{get: () => 'en-US', configurable: true}}); }} catch(e){{}}

// === CHROME RUNTIME (blocks CDP detection) ===
// Site overrides window.chrome post-load, so we patch the EXISTING object
if (window.chrome && !window.chrome.runtime) {{
    try {{
        var _chromeRuntime = {{onInstalled:{{}}, onStartup:{{}}, onMessage:{{}}}};
        Object.defineProperty(window.chrome, 'runtime', {{
            get: function(){{ return _chromeRuntime; }},
            configurable: true,
            enumerable: true
        }});
    }} catch(e){{}}
}}

// === PERMISSIONS API ===
if (navigator.permissions && navigator.permissions.query) {{
    const _oq = navigator.permissions.query;
    navigator.permissions.query = p => p.name === 'notifications'
        ? Promise.resolve({{state: 'granted'}})
        : _oq(p);
}}

// === WEBGL SPOOFING (supports both WebGL1 and WebGL2) ===
try {{
    var _patchWebGL = function(proto) {{
        if (!proto) return;
        var _gp = proto.getParameter;
        proto.getParameter = function(p) {{
            if (p === 37445) return '{vend}';
            if (p === 37446) return '{rend}';
            if (p === 7936) return '{vend}';
            if (p === 7937) return '{vfl}';
            if (p === 35724) return '{rend}';
            return _gp.call(this, p);
        }};
    }};
    _patchWebGL(WebGLRenderingContext.prototype);
    _patchWebGL(WebGL2RenderingContext.prototype);
}} catch(e){{}}

// === CANVAS NOISE (match real GPU rendering) ===
try {{
    const _gc = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(t,a) {{
        const ctx = _gc.call(this,t,a);
        if (t==='2d' && ctx) {{
            const _ft = ctx.fillText;
            ctx.fillText = function(t,x,y,m) {{
                return _ft.call(this, t, x+0.001, y+0.001, m);
            }};
        }}
        return ctx;
    }};
}} catch(e){{}}

// === AUDIO CONTEXT NOISE ===
try {{
    var AC = window.AudioContext || window.webkitAudioContext;
    if (AC) {{
        var _oa = AC.prototype.createAnalyser;
        AC.prototype.createAnalyser = function() {{
            var a = _oa.call(this);
            a.getFloatFrequencyData = function(b) {{ for(var i=0;i<b.length;i++) b[i]=-100+Math.random()*5; }};
            return a;
        }};
    }}
}} catch(e){{}}

// === SCREEN ===
try {{ Object.defineProperty(screen, 'colorDepth', {{get:()=>24}}); }} catch(e){{}}
try {{ Object.defineProperty(screen, 'pixelDepth', {{get:()=>24}}); }} catch(e){{}}

// === CLEAN AUTOMATION ARTIFACTS (defineProperty — more persistent than delete) ===
try {{ Object.defineProperty(window, 'cdc_adoQpoasnfa76pfcZLmcfl_Array', {{get:()=>undefined, configurable:true}}); }} catch(e){{}}
try {{ Object.defineProperty(window, 'cdc_adoQpoasnfa76pfcZLmcfl_Promise', {{get:()=>undefined, configurable:true}}); }} catch(e){{}}
try {{ Object.defineProperty(window, 'cdc_adoQpoasnfa76pfcZLmcfl_Symbol', {{get:()=>undefined, configurable:true}}); }} catch(e){{}}
}} catch(e){{}}
"""


def stealth_score(driver):
    """Run 10-point stealth check and return score"""
    try:
        j = driver.execute_script("""
        var r = {};
        r.wd = !navigator.webdriver;
        r.plugins = navigator.plugins.length >= 3;
        r.mimetypes = navigator.mimeTypes.length >= 2;
        r.chrome = typeof window.chrome === 'object' && !!window.chrome.runtime;
        r.vendor = (navigator.vendor || '').length > 0 || (navigator.vendor === '');
        r.langs = navigator.languages && navigator.languages.length > 0;
        r.screen = screen.colorDepth === 24;
        r.no_headless = navigator.userAgent.indexOf('Headless') === -1;
        r.no_cdc = !window.cdc_adoQpoasnfa76pfcZLmcfl_Array && !window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        r.webgl = true;
        try {
            var c = document.createElement('canvas');
            var gl = c.getContext('webgl') || c.getContext('experimental-webgl');
            if (gl) {
                var v = gl.getParameter(gl.VENDOR);
                var rnd = gl.getParameter(gl.RENDERER);
                r.webgl = v.length > 0 && rnd.length > 0 && v.indexOf('WebKit') === -1;
            }
        } catch(e){}
        
        var passed = 0, total = 10;
        for (var k in r) { if (r[k]) passed++; }
        return JSON.stringify({passed: passed, total: total, checks: r});
        """)
        if j:
            data = json.loads(j)
            fails = [k for k, v in data["checks"].items() if not v]
            print(f"    🛡️ Score: {data['passed']}/{data['total']}  " + (f"⚠️ {fails}" if fails else ""))
            return data
    except: pass
    return None


def human_scroll(driver):
    """Natural human scrolling"""
    try:
        h = driver.execute_script("return document.body.scrollHeight")
        vp = driver.execute_script("return window.innerHeight")
        ms = max(0, h - vp)
        if ms < 10: return
        steps = random.randint(3, 8)
        for i in range(steps):
            target = min(ms * (i+1) / steps + random.randint(-20, 20), ms)
            target = max(0, target)
            driver.execute_script(f"window.scrollTo({{top: {target}, behavior: 'smooth'}})")
            time.sleep(random.uniform(0.3, 0.9))
            if random.random() < 0.15: time.sleep(random.uniform(1.5, 3.5))
    except: pass


def run_visit(driver, num):
    """Single visitor session"""
    r = {"visit": num, "click": 0, "ok": False}
    try:
        driver.get(SITE)
        time.sleep(random.uniform(2, 5))
        t = driver.title
        print(f"    📄 {t[:50]}")
        r["ok"] = True

        human_scroll(driver)
        print(f"    📜 Scrolled")

        # Click article
        links = driver.find_elements("css selector", "a.card-link, .news-card a, .hero-card a, .read-more, .card a")
        if links and random.random() < 0.4:
            try:
                link = random.choice(links)
                link.location_once_scrolled_into_view
                time.sleep(random.uniform(0.2, 0.5))
                link.click()
                r["click"] = 1
                print(f"    🖱️ Clicked")
                time.sleep(random.uniform(2, 6))
                if random.random() < 0.3: human_scroll(driver)
                if random.random() < 0.2: driver.back(); time.sleep(random.uniform(1, 2))
            except: pass

        time.sleep(random.uniform(1, 3))
    except Exception as e:
        print(f"    ❌ {e}")
    return r


def adaptive_cycle():
    """One full traffic cycle with adaptation"""
    start = time.time()

    # Load/save fingerprint
    fp = None
    if FINGERPRINT_FILE.exists():
        try:
            fp = json.loads(FINGERPRINT_FILE.read_text())
        except: pass

    if not fp:
        fp = random.choice(FINGERPRINTS).copy()
        print(f"  🆕 Fresh fingerprint")

    if random.random() < 0.15:
        new_fp = random.choice(FINGERPRINTS)
        if new_fp["ua"] != fp["ua"]:
            fp = new_fp.copy()
            print(f"  🧬 Evolved fingerprint")

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    vp = random.choice(VIEWPORTS)
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-popup-blocking")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--force-color-profile=srgb")
    opts.add_argument("--no-first-run")
    opts.add_argument("--mute-audio")
    opts.add_argument(f"--window-size={vp[0]},{vp[1]}")
    opts.add_argument(f"--user-agent={fp['ua']}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=opts)

    try:
        # Inject stealth patches BEFORE any navigation (CDP approach)
        stealth_js = build_stealth_js(fp)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": stealth_js})

        # Apply platform override
        driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
            "userAgent": fp["ua"],
            "platform": fp["platform"],
        })

        # Navigate to blank page first to warm up
        driver.get("about:blank")
        time.sleep(1)

        # Pre-test stealth
        driver.get(SITE)
        time.sleep(2)
        
        # Post-navigation stealth re-patch (site scripts may have overridden)
        re_patch = build_stealth_js(fp)
        driver.execute_script(re_patch)
        
        score_data = stealth_score(driver)

        visits = random.randint(1, 2)
        print(f"  📊 {visits} visit(s)")
        clicks = 0

        for i in range(visits):
            print(f"\n  --- Visit {i+1}/{visits} ---")
            result = run_visit(driver, i + 1)
            clicks += result["click"]
            if i < visits - 1:
                delay = random.randint(5, 15)
                print(f"  ⏳ {delay}s...")
                time.sleep(delay)

        # Keep fingerprint if score good
        if score_data and score_data["passed"] >= 8:
            fp["last_used"] = datetime.now().isoformat()
            FINGERPRINT_FILE.write_text(json.dumps(fp, indent=2))

        elapsed = time.time() - start
        print(f"\n  ✅ {elapsed:.0f}s, {clicks} click(s)")

    finally:
        try: driver.quit(); print(f"  🖥️ Closed")
        except: pass


def main():
    print(f"\n{'='*50}")
    print(f"🚀 ROCKET BOT v3 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    adaptive_cycle()
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
