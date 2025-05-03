import threading
import time
import random
import socket
import struct
import requests
from datetime import datetime, timedelta
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys




HEADER_FIELDS = [
    'User-Agent', 'Accept', 'Accept-Language', 'Accept-Encoding',
    'Connection', 'DNT', 'Upgrade-Insecure-Requests', 'X-Real-IP',
    'X-Forwarded-For', 'Remote-Addr', 'X-Request-ID', 'X-Client-Version',
    'Pragma', 'Cache-Control'
]
MAX_THREADS = 100
STATS_INTERVAL = 30
MAX_RUNTIME = 18000
CHUNK_SIZE = 8192

USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{0}.0.{1}.{2} Safari/537.36",
    # Mac Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{0}_{1}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{2}.0.{3} Safari/605.1.15",
    # Windows Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{0}.0) Gecko/20100101 Firefox/{1}.0",
    # iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS {0}_{1} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{2}.0 Mobile/15E148 Safari/604.1",
    # Android Chrome
    "Mozilla/5.0 (Linux; Android {0}; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{1}.0.{2}.{3} Mobile Safari/537.36"
]

def generate_random_url(base_url):
    """在基础URL后添加随机"""
    random_str = ''.join(random.choices('0123456789', k=35))
    return f"{base_url}{random_str}"

def generate_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
    
def generate_random_ua():
    template = random.choice(USER_AGENTS)
    try:
        if "Chrome" in template and "Windows" in template:
            return template.format(
                random.randint(90, 99),
                random.randint(1000, 9999),
                random.randint(100, 999))
        elif "Safari" in template and "Mac" in template:
            return template.format(
                random.randint(11, 15),
                random.randint(0, 7),
                random.randint(12, 15),
                random.randint(0, 7))
        elif "Firefox" in template:
            return template.format(
                random.randint(80, 95),
                random.randint(80, 95))
        elif "iPhone" in template:
            return template.format(
                random.randint(12, 15),
                random.randint(0, 7),
                random.randint(12, 15))
        elif "Android" in template:
            return template.format(
                random.randint(8, 11),
                random.randint(90, 99),
                random.randint(1000, 9999),
                random.randint(100, 999))
        else:
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 99)}.0.{random.randint(1000, 9999)}.{random.randint(100, 999)} Safari/537.36"
    except (IndexError, KeyError):
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def generate_headers():
    ip = generate_random_ip()
    headers = {
        'User-Agent': generate_random_ua(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'DNT': str(random.randint(0, 1)),
        'Upgrade-Insecure-Requests': '1',
        'X-Real-IP': ip,
        'X-Forwarded-For': ip,
        'Remote-Addr': ip,
        'X-Request-ID': ''.join(random.choices('0123456789abcdef', k=32)),
        'X-Client-Version': f"{random.randint(1, 10)}.{random.randint(0, 9)}",
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }
    return {k: headers[k] for k in HEADER_FIELDS if k in headers}

def interact_with_page(url, headers):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    for header, value in headers.items():
        options.add_argument(f'--header={header}: {value}')

    driver = Chrome(options=options)
    try:
        random_url = generate_random_url(url)
        driver.get(random_url)
        
        actions = ActionChains(driver)
        actions.send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(random.uniform(1, 2))

        content_type = driver.execute_script("return document.contentType")
        cookies = driver.get_cookies()
        return content_type, cookies, random_url
    finally:
        driver.quit()

def download_with_requests(url, cookies, headers):
    random_url = generate_random_url(url)
    s = requests.Session()
    for c in cookies:
        s.cookies.set(c['name'], c['value'])
    r = s.get(random_url, headers=headers, stream=True, timeout=3)
    r.raise_for_status()
    total = 0
    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
        if not chunk:
            break
        total += len(chunk)
    return total, random_url

class TrafficSimulator:
    def __init__(self, url):
        self.url = url
        self.total_bytes = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()

    def simulate(self):
        while (datetime.now() - self.start_time).total_seconds() < MAX_RUNTIME:
            headers = generate_headers()
            try:
                content_type, cookies, used_url = interact_with_page(self.url, headers)
                if 'html' in content_type:
                    with self.lock:
                        print(f"[模拟] HTML页面加载完成")
                else:
                    size, used_url = download_with_requests(self.url, cookies, headers)
                    with self.lock:
                        self.total_bytes += size
                        print(f"[下载] 非HTML内容: {size} 字节")
            except Exception as e:
                print(f"[错误] {e}")
            time.sleep(random.uniform(1, 2))

    def run(self):
        threads = []
        for _ in range(min(MAX_THREADS, 5)):
            t = threading.Thread(target=self.simulate)
            t.start()
            threads.append(t)

        while (datetime.now() - self.start_time).total_seconds() < MAX_RUNTIME:
            time.sleep(STATS_INTERVAL)
            with self.lock:
                print(f"[统计] 当前总下载: {self.total_bytes/1024/1024:.2f} MB")

        for t in threads:
            t.join(timeout=1)

if __name__ == "__main__":
    print("模拟启动")
    print(f"最大运行时间: {MAX_RUNTIME//60}分钟")
    
    simulator = TrafficSimulator(TARGET_URL)
    simulator.run()
    print("模拟结束")