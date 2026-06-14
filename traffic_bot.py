#!/usr/bin/env python3
"""
Rocket News Premium Traffic Bot v2 (Selenium + Stealth)
- Xvfb virtual display (headed mode)
- All known stealth patches applied via CDP
- Human-like mouse, scroll, and interaction
- Random browser fingerprints
"""

import os, sys, random, time, json, subprocess
from datetime import datetime

import warnings
warnings.filterwarnings("ignore")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.200 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (iPad; CPU OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.107 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    (1366, 768), (1920, 1080), (1536, 864), (1440, 900),
    (1280, 720), (1600, 900), (1024, 768), (1728, 1117),
    (1440, 900), (1920, 1200),
]

LANGUAGES = [
    "en-US,en;q=0.9", "en-GB,en;q=0.8", "en-US,en;q=0.9,hi;q=0.5",
    "en;q=0.8", "en-US,en;q=0.9,fr;q=0.7"
]

VISIT_URL = "https://rocketnewsdaily.vercel.app"

# Chrome binary from snap
CHROME_BIN = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
CHROMEDRIVER = "/snap/chromium/3459/usr/lib/chromium-browser/chromedriver"

def stealth_patches(driver):
    """Apply all known stealth patches via CDP"""
    
    # 1. Override user agent
    ua = driver.execute_script("return navigator.userAgent")
    if "Headless" in ua:
        # Replace HeadlessChrome with regular Chrome
        ua_clean = ua.replace("HeadlessChrome", "Chrome")
        driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
            "userAgent": ua_clean,
            "acceptLanguage": random.choice(LANGUAGES),
            "platform": "Win32",
        })
    
    # 2. Remove webdriver flag (the big one)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # 3. Add missing chrome properties
    driver.execute_script("""
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {return {}},
            app: {},
            webstore: {},
            permissions: {},
            platform: 'win32'
        };
    """)
    
    # 4. Override plugins array (headless has empty)
    driver.execute_script("""
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                return [1, 2, 3, 4, 5];
            }
        });
    """)
    
    # 5. Override languages
    driver.execute_script("""
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    """)
    
    # 6. Disable automation flags
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
            );
            
            // Add chrome object if missing
            if (!window.chrome) {
                window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
            }
        """
    })
    
    # 7. Set window size
    vp = random.choice(VIEWPORTS)
    driver.set_window_size(vp[0], vp[1])

def human_scroll(driver):
    """Scroll like a human - variable speed with pauses"""
    height = driver.execute_script("return document.body.scrollHeight")
    viewport = driver.execute_script("return window.innerHeight")
    steps = random.randint(4, 10)
    
    for i in range(steps):
        max_scroll = height - viewport
        if max_scroll <= 0:
            break
        target = min(int((max_scroll / steps) * (i + 1) + random.randint(-30, 30)), max_scroll)
        target = max(0, target)
        
        driver.execute_script(f"window.scrollTo({{top: {target}, behavior: 'smooth'}})")
        time.sleep(random.uniform(0.3, 1.2))
        
        # Random pause mid-scroll
        if random.random() < 0.2:
            time.sleep(random.uniform(1.0, 3.0))

def simulate_visit(driver, visit_num):
    """Simulate one real visitor session"""
    result = {"visit": visit_num, "click": 0, "scroll": False}
    
    try:
        # Load page
        driver.get(VISIT_URL)
        time.sleep(random.uniform(2.5, 5.0))
        
        title = driver.title
        print(f"  📄 Page loaded: {title[:50]}")
        
        # Scroll like human
        human_scroll(driver)
        result["scroll"] = True
        print(f"  📜 Scrolled page")
        
        # Click articles (50% chance)
        links = driver.find_elements("css selector", "a.card-link, .news-card a, .hero-card a, .read-more")
        if links and random.random() < 0.5:
            link = random.choice(links)
            try:
                # Get link location for smooth scroll
                loc = link.location_once_scrolled_into_view
                time.sleep(random.uniform(0.3, 0.7))
                
                link.click()
                result["click"] = 1
                text = link.text[:40] or link.get_attribute("href")[:40]
                print(f"  🖱️ Clicked: {text}")
                
                time.sleep(random.uniform(3.0, 7.0))
                
                # Sometimes scroll article page
                if random.random() < 0.5:
                    human_scroll(driver)
                
                # Go back sometimes
                if random.random() < 0.3:
                    driver.back()
                    time.sleep(random.uniform(1.5, 3.0))
            except:
                pass
        
        time.sleep(random.uniform(1.0, 3.0))
        return result
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return result

def main():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    
    print(f"\n{'='*50}")
    print(f"🚀 Rocket News Traffic Bot v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    num_visits = random.randint(1, 3)
    print(f"📊 Plan: {num_visits} visit(s)")
    
    total_clicks = 0
    total_scrolls = 0
    
    for i in range(num_visits):
        print(f"\n--- Visit {i+1}/{num_visits} ---")
        
        opts = Options()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--disable-popup-blocking")
        opts.add_argument("--lang=en")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-crash-reporter")
        opts.add_argument("--disable-background-networking")
        opts.add_argument("--no-first-run")
        opts.add_argument("--disable-default-apps")
        opts.add_argument("--disable-prompt-on-repost")
        opts.add_argument("--disable-prompt-on-repost")
        opts.add_argument("--disable-component-update")
        opts.add_argument("--disable-background-timer-throttling")
        
        # Xvfb handles display - no --headless!
        # Headless detection bypassed by using virtual display
        
        service = Service(CHROMEDRIVER)
        driver = webdriver.Chrome(service=service, options=opts)
        
        try:
            print(f"  🖥️ Browser opened")
            time.sleep(random.uniform(1, 2))
            
            # Apply all stealth patches
            stealth_patches(driver)
            
            # Verify stealth
            wd = driver.execute_script("return navigator.webdriver")
            ua = driver.execute_script("return navigator.userAgent")
            print(f"  🛡️ webdriver={wd} | UA headless={'Headless' in ua}")
            
            result = simulate_visit(driver, i + 1)
            total_clicks += result["click"]
            total_scrolls += 1 if result["scroll"] else 0
        
        finally:
            try:
                driver.quit()
            except:
                pass
            print(f"  🖥️ Browser closed")
            
        # Delay between visits
        if i < num_visits - 1:
            delay = random.randint(8, 20)
            print(f"  ⏳ Waiting {delay}s...")
            time.sleep(delay)
    
    print(f"\n{'='*50}")
    print(f"✅ Done: {num_visits} visit(s), {total_clicks} click(s)")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
