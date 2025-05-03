import time, random, requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from urllib.parse import urljoin, urlparse









HEADER_FIELDS = [
    'User-Agent',
    'Accept',
    'Accept-Language',
    'Accept-Encoding',
    'DNT',
    'Upgrade-Insecure-Requests',
    'Pragma',
    'Cache-Control'
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_{}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Mobile Safari/537.36"
]

def generate_random_headers():
    ua = random.choice(USER_AGENTS).format(random.randint(90, 110))
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': str(random.randint(0, 1)),
        'Upgrade-Insecure-Requests': '1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }
    return {k: v for k, v in headers.items() if k in HEADER_FIELDS}

def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollBy(0, window.innerHeight);")
        time.sleep(random.uniform(0.5, 2.0))
        new_height = driver.execute_script("return window.scrollY + window.innerHeight")
        if new_height >= last_height - 100:
            break

def use_requests(url, headers, cookies):
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    r = session.get(url, headers=headers, stream=True)
    print(f"[Requests] {url} - {r.status_code} - {r.headers.get('Content-Type', '')}")
    return r

def visit_url(url):
    headers = generate_random_headers()
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    for key, value in headers.items():
        if key.lower() == 'user-agent':
            options.add_argument(f"--user-agent={value}")
    
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(60)

    try:
        driver.get(url)
        time.sleep(random.uniform(1, 3))
        content_type = driver.execute_script(
            "return document.contentType || '';"
        )

        final_url = driver.current_url
        if 'html' in content_type:
            print(f"[Selenium] {final_url} - HTML content")
            scroll_page(driver)
        else:
            print(f"[Selenium→Requests] {final_url} - 非HTML内容")
            cookies = driver.get_cookies()
            driver.quit()
            r = use_requests(final_url, headers, cookies)
            return
    except Exception as e:
        print(f"[错误] {str(e)}")
    finally:
        driver.quit()

def main():
    while True:
        visit_url(TARGET_URL)
        print("[完成一次访问]\n")
        time.sleep(random.uniform(5, 15))  # 模拟用户停顿

if __name__ == '__main__':
    main()
