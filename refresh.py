import json
import os
import time
import logging
import random
from urllib.parse import quote_plus
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

AMAZON_URL = "https://www.amazon.fr/"
SELLER_URL = "https://sellercentral-europe.amazon.com/"

PROXY = os.getenv("PROXY")
HEADLESS = False

REQUIRED_COOKIES = {
    "aws-waf-token",
    "session-id",
    "session-id-time",
    "i18n-prefs",
    "lc-acbfr",
    "ubid-acbfr",
    "csm-hit",
    "session-token",
    "ad-privacy",
    "rxc"
}

def parse_proxy(proxy_str):
    if not proxy_str:
        return None
    try:
        if "@" in proxy_str:
            creds, server = proxy_str.split("@")
            creds = creds.replace("http://", "")
            username, password = creds.split(":")
            return {
                "server": f"http://{server}",
                "username": username,
                "password": password
            }
        return {"server": proxy_str}
    except Exception as e:
        logging.warning(f"Proxy parsing failed: {e}")
        return None

proxy_config = parse_proxy(str(PROXY))

def launch_browser(playwright):
    return playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox"
        ]
    )

def create_context(browser):
    return browser.new_context(
        proxy=proxy_config,
        viewport={
            "width": random.randint(1200, 1920),
            "height": random.randint(800, 1080)
        },
        user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   f"(KHTML, like Gecko) Chrome/{random.randint(100, 120)}.0.0.0 Safari/537.36"
    )

def cookies_to_string(cookies):
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)

def load_existing_cookies(path="cookies.json"):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load existing cookies: {e}")
            return {}
    return {}

def save_cookies(data, path="cookies.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def fetch_amazon_cookies(playwright, query, max_retries=50):
    encoded_query = quote_plus(query)

    for attempt in range(1, max_retries + 1):
        browser = None
        try:
            logging.info(f"Amazon attempt {attempt}")
            browser = launch_browser(playwright)
            context = create_context(browser)
            page = context.new_page()

            page.goto(AMAZON_URL, timeout=60000)
            page.wait_for_load_state("load")
            time.sleep(random.uniform(2, 4))

            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            time.sleep(random.uniform(1, 2))
            page.mouse.wheel(0, random.randint(300, 1000))
            time.sleep(random.uniform(2, 4))

            page.goto(f"https://www.amazon.fr/s?k={encoded_query}", timeout=60000)
            page.wait_for_load_state("load")
            time.sleep(random.uniform(3, 6))

            page.mouse.move(random.randint(100, 800), random.randint(100, 800))
            time.sleep(random.uniform(1, 2))
            page.mouse.wheel(0, random.randint(500, 1500))
            time.sleep(random.uniform(2, 4))

            cookies = context.cookies()
            cookie_names = {c["name"] for c in cookies}
            missing = REQUIRED_COOKIES - cookie_names

            if not missing:
                logging.info("All required Amazon cookies acquired")
                return cookies_to_string(cookies)

            logging.warning(f"Missing cookies: {missing}")

        except PlaywrightTimeoutError:
            logging.warning("Amazon timeout, retrying...")
        except Exception as e:
            logging.error(f"Amazon error: {e}")
        finally:
            if browser:
                browser.close()

        time.sleep(random.uniform(3, 6))

    raise RuntimeError("Failed to retrieve Amazon cookies")

def main():
    cookie_sets = load_existing_cookies()

    with sync_playwright() as playwright:
        for i in range(1, 6):
            query = f"Jeux {random.randint(1, 999999)}"
            cookie_sets[f"amazon{i}"] = fetch_amazon_cookies(playwright, query)

    save_cookies(cookie_sets)
    logging.info("Cookies saved to cookies.json")

if __name__ == "__main__":
    main()
