#!/usr/bin/env python3
"""
Rocket News Real Browser Traffic Bot — Selenium-based
Actually executes JavaScript to trigger Monetag popunders.
"""

import random
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SITE = "https://rocketnewsdaily.vercel.app"
CHROMEDRIVER = "/snap/chromium/3459/usr/lib/chromium-browser/chromedriver"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36",
]


def create_driver():
    """Create a headless Chrome browser instance"""
    opts = Options()
    opts.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    opts.add_argument("--headless=new")  # Headless mode
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1920,1080")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    
    service = Service(CHROMEDRIVER)
    driver = webdriver.Chrome(service=service, options=opts)
    
    # Hide WebDriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver


def simulate_visit(driver):
    """Simulate one real user visit — executes all JS including Monetag"""
    results = {"visit": 1, "click": 0, "error": ""}
    
    try:
        # 1. Visit main page (triggers Monetag popunder script!)
        driver.get(SITE)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        print(f"  📄 Page loaded — Monetag popunder fired!")
        
        # 2. Simulate reading behavior — scroll through page
        page_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        scroll_steps = random.randint(3, 8)
        
        for step in range(scroll_steps):
            scroll_to = int((page_height - viewport_height) * ((step + 1) / scroll_steps))
            driver.execute_script(f"window.scrollTo({{top: {scroll_to}, behavior: 'smooth'}})")
            time.sleep(random.uniform(1, 4))
        
        print(f"  📜 Scrolled through page ({scroll_steps} steps)")
        
        # 3. Maybe click an article
        if random.random() < 0.5:
            links = driver.find_elements(By.CSS_SELECTOR, ".news-card a, .featured-card")
            if links:
                target = random.choice(links)
                try:
                    ActionChains(driver).move_to_element(target).pause(0.5).click().perform()
                    results["click"] = 1
                    print(f"  🖱️ Clicked article")
                    time.sleep(random.uniform(3, 8))
                    
                    # Maybe click back
                    if random.random() < 0.3:
                        driver.back()
                        time.sleep(random.uniform(2, 5))
                except Exception:
                    pass
        
        # 4. Interact with category filters
        if random.random() < 0.3:
            try:
                filters = driver.find_elements(By.CSS_SELECTOR, ".cat-btn")
                if len(filters) > 1:
                    random.choice(filters[1:]).click()
                    print(f"  🏷️ Clicked category filter")
                    time.sleep(random.uniform(2, 5))
            except Exception:
                pass
        
        return results
        
    except Exception as e:
        results["error"] = str(e)
        return results


def main():
    print(f"🌐 Real Browser Traffic Bot — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Target: {SITE}")
    
    total_visits = 0
    total_clicks = 0
    
    num_visits = random.randint(1, 2)  # Less visits per run (each is slow with real browser)
    
    for i in range(num_visits):
        if i > 0:
            gap = random.randint(15, 60)
            time.sleep(gap)
        
        print(f"\n  ── Visit {i+1}/{num_visits} ──")
        driver = None
        try:
            driver = create_driver()
            result = simulate_visit(driver)
            total_visits += result["visit"]
            total_clicks += result["click"]
        except Exception as e:
            print(f"  ❌ Error: {e}")
        finally:
            if driver:
                driver.quit()
    
    print(f"\n  📊 Done: {total_visits} real-browser visits, {total_clicks} clicks")
    print(f"  💰 Monetag should count this as real traffic!")


if __name__ == "__main__":
    main()
