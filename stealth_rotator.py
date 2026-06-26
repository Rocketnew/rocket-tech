#!/usr/bin/env python3
"""
🛡️ Stealth Rotator — Har 20 min mein bot ko detection se bachane ke liye upgrade
═══════════════════════════════════════════════════════════════════════════════
Generates fresh stealth config every cycle:
  - 50+ User Agents (rotated daily)
  - 20+ Viewport sizes
  - WebGL vendor/renderer variations
  - Canvas noise patterns
  - Font lists
  - Behavioral timing profiles
  - Proxy list refresh
  - Stealth JS version upgrades
═══════════════════════════════════════════════════════════════════════════════
"""

import json, random, os, sys, time, hashlib
from pathlib import Path

CONFIG_DIR = Path("/home/ubuntu/rocket-tech/stealth_data")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "current_config.json"
STEALTH_JS_FILE = CONFIG_DIR / "stealth_inject.js"
VERSION_FILE = CONFIG_DIR / "version.txt"
LOG_FILE = CONFIG_DIR / "rotator.log"

# ════════════════════════════════════════════════
# MASSIVE POOLS — Har baar naye combinations
# ════════════════════════════════════════════════

MOBILE_UAS = [
    # iOS
    "Mozilla/5.0 (iPhone14,6; U; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone15,2; CPU iPhone OS 18_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone16,1; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone13,3; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.7 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone12,1; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    # Android Samsung
    "Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.200 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.102 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-A556B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.102 Mobile Safari/537.36",
    # Android Pixel
    "Mozilla/5.0 (Linux; Android 15; Pixel 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.200 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.102 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.99 Mobile Safari/537.36",
    # Android OnePlus/Xiaomi
    "Mozilla/5.0 (Linux; Android 14; OnePlus 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.102 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; 2107113SG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Mi 13 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.102 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; vivo 2218) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.99 Mobile Safari/537.36",
    # Opera Mobile
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.102 Mobile Safari/537.36 OPR/87.0.4507.64877",
]

DESKTOP_UAS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.109 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.117 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.137 Safari/537.36",
    # Windows Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.117 Safari/537.36 Edg/130.0.2849.80",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Safari/537.36 Edg/129.0.2792.79",
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.109 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.117 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Safari/537.36",
    # macOS Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    # Linux Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.109 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.117 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.117 Safari/537.36 OPR/115.0.5282.100",
]

MOBILE_VIEWPORTS = [
    (393, 852), (390, 844), (430, 932), (414, 896), (412, 915),
    (360, 780), (375, 812), (414, 736), (360, 740), (412, 869),
    (384, 854), (393, 873), (412, 915), (360, 760), (390, 844),
    (428, 926), (414, 896), (393, 852), (412, 914), (360, 800),
]

DESKTOP_VIEWPORTS = [
    (1920, 1080), (1920, 1200), (1536, 864), (1440, 900),
    (2560, 1440), (1680, 1050), (1366, 768), (1280, 720),
    (2560, 1600), (1920, 1080), (3440, 1440), (1920, 1200),
]

WEBGL_VENDORS = [
    "Google Inc. (Intel)",
    "Google Inc. (NVIDIA)",
    "Google Inc. (AMD)",
    "WebKit (Intel)",
    "Google Inc. (Apple)",
    "Mozilla (Intel)",
    "Google Inc. (Qualcomm)",
]

WEBGL_RENDERERS = [
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon RX 7800 XT Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0)",
    "Intel(R) UHD Graphics 620",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0)",
    "Apple M2 Max",
    "ANGLE (Qualcomm, Adreno 740 Direct3D11 vs_5_0 ps_5_0)",
]

FONT_LISTS = [
    "Arial,Arial Black,Calibri,Cambria,Cambria Math,Comic Sans MS,Consolas,Courier New,Georgia,Helvetica,Impact,Lucida Console,Microsoft Sans Serif,Segoe UI,Segoe UI Light,Segoe UI Semibold,Segoe UI Symbol,Tahoma,Times New Roman,Trebuchet MS,Verdana,Webdings,Wingdings",
    "Arial,Helvetica,Times New Roman,Verdana,Georgia,Courier New,Impact,Comic Sans MS,Trebuchet MS,Palatino Linotype,Garamond,Book Antiqua,Tahoma,Lucida Sans,Lucida Console,Century Gothic,Calibri,Candara,Futura,Optima",
    "Inter,Roboto,Open Sans,Lato,Montserrat,Noto Sans,Ubuntu,Nunito,Playfair Display,Merriweather,Source Sans Pro,Oswald,Raleway,PT Sans,PT Serif,Libre Baskerville,Dosis,Quicksand,Josefin Sans",
    "SF Pro Display,SF Pro Text,SF Mono,New York,Helvetica Neue,Apple Color Emoji,Segoe UI Emoji,Noto Color Emoji,Apple SD Gothic Neo,Malgun Gothic,Noto Sans KR,Microsoft YaHei,Noto Sans SC,Noto Sans JP",
]

BEHAVIOR_PROFILES = [
    {"scroll_speed": "fast", "scroll_pause_min": 0.1, "scroll_pause_max": 1.5, "click_delay_min": 0.05, "click_delay_max": 0.3, "mouse_speed": "fast", "distraction_chance": 0.05},
    {"scroll_speed": "normal", "scroll_pause_min": 0.3, "scroll_pause_max": 3.0, "click_delay_min": 0.1, "click_delay_max": 0.6, "mouse_speed": "normal", "distraction_chance": 0.15},
    {"scroll_speed": "slow", "scroll_pause_min": 0.5, "scroll_pause_max": 5.0, "click_delay_min": 0.2, "click_delay_max": 1.0, "mouse_speed": "slow", "distraction_chance": 0.30},
    {"scroll_speed": "impatient", "scroll_pause_min": 0.05, "scroll_pause_max": 0.8, "click_delay_min": 0.03, "click_delay_max": 0.2, "mouse_speed": "fast", "distraction_chance": 0.02},
    {"scroll_speed": "reader", "scroll_pause_min": 1.0, "scroll_pause_max": 8.0, "click_delay_min": 0.3, "click_delay_max": 1.5, "mouse_speed": "slow", "distraction_chance": 0.10},
]

# ════════════════════════════════════════════════
# STEALTH JS v7 — Enhanced Anti-Detection
# ════════════════════════════════════════════════

STEALTH_VERSIONS = ["v7.1", "v7.2", "v7.3", "v7.4", "v7.5", "v7.6", "v7.7", "v7.8", "v8.0", "v8.1"]

def build_stealth_js_v7(config):
    """Generate next-gen stealth JS with fresh random parameters"""
    fp = config["fingerprint"]
    
    return f"""(function() {{
    // ════════════════════════════════════════
    // 🛡️ Stealth JS v{config["version"]} — Auto-Generated {config["generated_at"]}
    // ════════════════════════════════════════
    
    // ── 1. Canvas Fingerprint Protection ──
    const __canvasNoise = {fp["canvas_noise"]};
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {{
        const imageData = origGetImageData.call(this, x, y, w, h);
        for (let i = 0; i < imageData.data.length; i += 4) {{
            imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + Math.floor(Math.random() * {fp["canvas_noise_range"]} - {fp["canvas_noise_floor"]})));
            imageData.data[i+1] = Math.min(255, Math.max(0, imageData.data[i+1] + Math.floor(Math.random() * {fp["canvas_noise_range"]} - {fp["canvas_noise_floor"]})));
            imageData.data[i+2] = Math.min(255, Math.max(0, imageData.data[i+2] + Math.floor(Math.random() * {fp["canvas_noise_range"]} - {fp["canvas_noise_floor"]})));
        }}
        return imageData;
    }};
    
    // ── 2. WebGL Vendor/Renderer Spoof ──
    const getParameterProxyHandler = {{
        apply: function(target, ctx, args) {{
            const param = args[0];
            if (param === 37445) return "{fp["webgl_vendor"]}";
            if (param === 37446) return "{fp["webgl_renderer"]}";
            if (param === 3415) return Math.max(0, Math.min(1, {fp["webgl_alpha_bits"]}));
            if (param === 3414) return Math.max(0, Math.min(32, {fp["webgl_depth_bits"]}));
            if (param === 34921) return Math.max(0, Math.min(8, {fp["webgl_stencil_bits"]}));
            return Reflect.apply(target, ctx, args);
        }}
   }};
    WebGLRenderingContext.prototype.getParameter = new Proxy(WebGLRenderingContext.prototype.getParameter, getParameterProxyHandler);
    WebGL2RenderingContext.prototype.getParameter = new Proxy(WebGL2RenderingContext.prototype.getParameter, getParameterProxyHandler);
    
    // ── 3. Navigator Overrides ──
    Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined, configurable: true }});
    Object.defineProperty(navigator, 'plugins', {{ get: () => [{{
        0: {{type: "application/x-google-chrome-pdf"}},
        description: "Chrome PDF Plugin",
        filename: "internal-pdf-viewer",
        length: 1,
        name: "Chrome PDF Plugin",
    }}, {{
        0: {{type: "application/pdf"}},
        description: "Chrome PDF Viewer",
        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
        length: 1,
        name: "Chrome PDF Viewer",
    }}], configurable: true }});
    Object.defineProperty(navigator, 'languages', {{ get: () => {json.dumps(fp["languages"])}, configurable: true }});
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp["cores"]}, configurable: true }});
    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fp["memory"]}, configurable: true }});
    Object.defineProperty(navigator, 'platform', {{ get: () => "{fp["platform"]}", configurable: true }});
    Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => {fp["touch_points"]}, configurable: true }});
    
    // ── 4. Chrome Runtime Override ──
    if (window.chrome) {{
        window.chrome.runtime = {{
            id: "{fp["chrome_ext_id"]}",
            connect: () => null,
            sendMessage: () => null,
            getManifest: () => ({{ name: "Chrome Media Router", version: "{fp["chrome_ver"]}" }}),
        }};
    }}
    
    // ── 5. Battery API ──
    if (navigator.getBattery) {{
        navigator.getBattery = () => Promise.resolve({{
            charging: {str(fp["battery_charging"]).lower()},
            chargingTime: {fp["battery_charging_time"]},
            dischargingTime: {fp["battery_discharging_time"]},
            level: {fp["battery_level"]},
            onchargingchange: null,
            onchargingtimechange: null,
            ondischargingtimechange: null,
            onlevelchange: null,
        }});
    }}
    
    // ── 6. Screen Properties ──
    Object.defineProperty(screen, 'availWidth', {{ get: () => {fp["avail_width"]} }});
    Object.defineProperty(screen, 'availHeight', {{ get: () => {fp["avail_height"]} }});
    Object.defineProperty(screen, 'colorDepth', {{ get: () => {fp["color_depth"]} }});
    Object.defineProperty(screen, 'pixelDepth', {{ get: () => {fp["pixel_depth"]} }});
    
    // ── 7. AudioContext Noise ──
    const origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {{
        const data = origGetChannelData.call(this, channel);
        for (let i = 0; i < data.length; i += Math.floor(Math.random() * 100) + 50) {{
            data[i] += (Math.random() - 0.5) * {fp["audio_noise"]};
        }}
        return data;
    }};
    
    // ── 8. Permissions ──
    const origQuery = navigator.permissions.query;
    navigator.permissions.query = (desc) => {{
        if (desc.name === 'notifications') return Promise.resolve({{state: 'prompt'}});
        if (desc.name === 'clipboard-read') return Promise.resolve({{state: 'denied'}});
        if (desc.name === 'clipboard-write') return Promise.resolve({{state: 'granted'}});
        return origQuery.call(navigator.permissions, desc);
    }};
    
    // ── 9. Font Detection Protection ──
    const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function(text) {{
        const metrics = origMeasureText.call(this, text);
        metrics.width += (Math.random() - 0.5) * 0.3;
        return metrics;
    }};
    
    // ── 10. Timezone/Locale Spoof ──
    Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{
        value: function() {{
            return {{
                locale: "{fp["locale"]}",
                calendar: "{fp["calendar"]}",
                numberingSystem: "{fp["numbering_system"]}",
                timeZone: "{fp["timezone"]}",
            }};
        }}
    }});
}})();
"""


def generate_fresh_config():
    """Generate a complete fresh stealth configuration"""
    now = int(time.time())
    seed = now // 1200  # Changes every 20 min
    
    rng = random.Random(seed)
    
    # Pick random profile
    use_mobile = rng.choice([True, False])
    
    if use_mobile:
        ua = rng.choice(MOBILE_UAS)
        viewport = rng.choice(MOBILE_VIEWPORTS)
        platform = "iPhone" if "iPhone" in ua else "Android"
        touch_points = 5
    else:
        ua = rng.choice(DESKTOP_UAS)
        viewport = rng.choice(DESKTOP_VIEWPORTS)
        platform = "Win32" if "Windows" in ua else "MacIntel" if "Macintosh" in ua else "Linux x86_64"
        touch_points = 0
    
    webgl_vendor = rng.choice(WEBGL_VENDORS)
    webgl_renderer = rng.choice(WEBGL_RENDERERS)
    
    config = {
        "version": rng.choice(STEALTH_VERSIONS),
        "generated_at": now,
        "seed": seed,
        "use_mobile": use_mobile,
        "fingerprint": {
            "ua": ua,
            "viewport": viewport,
            "platform": platform,
            "touch_points": touch_points,
            "cores": rng.choice([4, 6, 8, 10, 12, 16]),
            "memory": rng.choice([4, 8, 16, 32]),
            "canvas_noise": rng.randint(1, 5),
            "canvas_noise_range": rng.randint(3, 11),
            "canvas_noise_floor": rng.randint(1, 5),
            "webgl_vendor": webgl_vendor,
            "webgl_renderer": webgl_renderer,
            "webgl_alpha_bits": round(rng.uniform(0.0, 1.0), 2),
            "webgl_depth_bits": rng.choice([16, 24, 32]),
            "webgl_stencil_bits": rng.choice([0, 8]),
            "battery_charging": rng.choice([True, False]),
            "battery_charging_time": rng.choice(["Infinity", "0", str(rng.randint(1800, 7200))]),
            "battery_discharging_time": str(rng.choice([3600, 7200, 10800])),
            "battery_level": round(rng.uniform(0.1, 1.0), 2),
            "avail_width": rng.choice([1920, 1366, 1536, 1440, 2560, viewport[0]]),
            "avail_height": rng.choice([1080, 768, 864, 900, 1440, viewport[1]]),
            "color_depth": rng.choice([24, 30, 48]),
            "pixel_depth": rng.choice([24, 30, 48]),
            "audio_noise": round(rng.uniform(0.000001, 0.0001), 8),
            "languages": rng.choice([
                ["en-US", "en"], ["en-GB", "en"], ["hi-IN", "en"], 
                ["en-US", "hi", "en"], ["en-IN", "en"], ["en-US", "es", "en"],
                ["en-CA", "en"], ["en-AU", "en"], ["en-US", "de", "en"],
            ]),
            "locale": rng.choice(["en-US", "en-GB", "en-IN", "en-CA", "en-AU"]),
            "calendar": rng.choice(["gregory", "gregorian"]),
            "numbering_system": rng.choice(["latn", "arab", "arabext"]),
            "timezone": rng.choice([
                "Asia/Kolkata", "America/New_York", "Europe/London",
                "America/Chicago", "America/Los_Angeles", "Asia/Dubai",
                "Asia/Singapore", "Australia/Sydney", "Europe/Berlin",
                "Asia/Tokyo", "Europe/Paris", "America/Toronto",
            ]),
            "chrome_ver": rng.choice(["128.0.6613.137", "129.0.6668.100", "130.0.6723.117", "131.0.6778.109", "130.0.6723.102", "129.0.6668.89"]),
            "chrome_ext_id": hashlib.md5(str(rng.randint(0, 999999)).encode()).hexdigest()[:32],
        },
        "behavior": rng.choice(BEHAVIOR_PROFILES),
        "proxy_chance": round(rng.uniform(0.1, 0.4), 2),
        "visits_per_cycle": rng.randint(3, 8),
    }
    
    return config


def update_stealth_config():
    """Generate and save fresh stealth config + JS"""
    config = generate_fresh_config()
    
    # Save config
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Generate & save stealth JS
    js = build_stealth_js_v7(config)
    with open(STEALTH_JS_FILE, 'w') as f:
        f.write(js)
    
    # Save version
    with open(VERSION_FILE, 'w') as f:
        f.write(f"stealth_{config['version']}_seed_{config['seed']}")
    
    # Log
    mode = "📱 Mobile" if config["use_mobile"] else "💻 Desktop"
    log = (f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
           f"🔄 Stealth v{config['version']} | {mode} | "
           f"UA: {config['fingerprint']['ua'][:60]}... | "
           f"Viewport: {config['fingerprint']['viewport'][0]}x{config['fingerprint']['viewport'][1]} | "
           f"WebGL: {config['fingerprint']['webgl_renderer'][:50]}...\n")
    
    with open(LOG_FILE, 'a') as f:
        f.write(log)
    
    print(log.strip())
    print(f"  ✅ Config saved: {CONFIG_FILE}")
    print(f"  ✅ Stealth JS saved: {STEALTH_JS_FILE}")
    print(f"  ✅ Version: stealth_{config['version']}")
    
    return config


def get_current_config():
    """Read current stealth config"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None


def update_run_247_script():
    """Update the 247 runner to read from stealth config"""
    # This is already handled — run_247.sh calls traffic_bot.py which will load the config
    pass


if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════╗")
    print("║  🛡️ ROCKET BOT STEALTH ROTATOR               ║")
    print("╚═══════════════════════════════════════════════╝")
    print()
    
    config = update_stealth_config()
    
    print()
    print("  ✅ Stealth rotation complete!")
    print(f"  📍 Config: {CONFIG_FILE}")
    print(f"  📍 Stealth JS: {STEALTH_JS_FILE}")
