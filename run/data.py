import time
import random
import threading
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
import socket
import struct



MAX_THREADS = 5
MAX_RUNTIME = 61
STATS_INTERVAL = 60

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{0}.0.{1}.{2} Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{3}_{4}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{5}.0.{6} Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{7}.0) Gecko/20100101 Firefox/{8}.0",
]

def random_user_agent():
    template = random.choice(USER_AGENTS)
    return template.format(
        random.randint(90, 99),
        random.randint(1000, 9999),
        random.randint(100, 999),
        random.randint(11, 15),
        random.randint(0, 7),
        random.randint(12, 15),
        random.randint(0, 9),
        random.randint(80, 95),
        random.randint(80, 95),
    )

def generate_random_headers():
    ip = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
    headers = {
        'User-Agent': random_user_agent(),
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
        'X-Client-Version': str(random.randint(1, 10)) + '.' + str(random.randint(0, 9)),
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }
    return headers

class BrowserWorker:
    def __init__(self, url):
        self.url = url
        self.bytes_downloaded = 0
        self.error_count = 0
        self.cookies = {}

    def run(self):
        try:
            headers = generate_random_headers()
            response = requests.get(self.url, headers=headers, cookies=self.cookies, stream=True, timeout=30)
            
            if 'html' in response.headers.get('Content-Type', ''):
                # 如果内容类型是 HTML，使用 Selenium 模拟
                self.handle_html_with_selenium(headers)
            else:
                # 否则使用 Requests 下载
                self.handle_non_html_with_requests(response)

        except Exception as e:
            self.error_count += 1
            print(f"[错误] {e}")

    def handle_html_with_selenium(self, headers):
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument(f"user-agent={headers['User-Agent']}")
            options.page_load_strategy = 'eager'

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            driver.get(self.url)

            # 获取重定向后的 URL
            current_url = driver.current_url

            # 如果重定向到非 HTML 文件（例如图片、视频等），使用 requests 继续下载
            if 'html' not in driver.page_source:
                self.handle_non_html_with_requests(requests.get(current_url, headers=headers, cookies=self.cookies))

            else:
                # 如果仍然是 HTML 页面，模拟滚动
                self.scroll_page(driver)

            body = driver.page_source.encode("utf-8", errors="ignore")
            self.bytes_downloaded = len(body)
            self.cookies = driver.get_cookies()
            driver.quit()
        except Exception as e:
            self.error_count += 1
            print(f"[错误] {e}")

    def scroll_page(self, driver):
        # 模拟滚动页面
        scroll_pause = 1.5
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(10):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def handle_non_html_with_requests(self, response):
        try:
            self.bytes_downloaded = len(response.content)
            self.cookies = response.cookies
        except Exception as e:
            self.error_count += 1
            print(f"[错误] 下载失败: {e}")

class TrafficSimulator:
    def __init__(self):
        self.total_bytes = 0
        self.total_errors = 0
        self.total_visits = 0
        self.start_time = datetime.now()
        self.stop_flag = False
        self.lock = threading.Lock()

    def worker_loop(self):
        while not self.stop_flag:
            worker = BrowserWorker(TARGET_URL)
            worker.run()
            with self.lock:
                self.total_bytes += worker.bytes_downloaded
                self.total_errors += worker.error_count
                self.total_visits += 1
            # 停顿 1~5 秒
            time.sleep(random.uniform(1, 5))

    def show_stats(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print("\n=== 状态统计 ===")
        print(f"运行时间: {timedelta(seconds=int(elapsed))}")
        print(f"总访问: {self.total_visits}")
        print(f"下载总量: {self.total_bytes / 1024 / 1024:.2f} MB")
        print(f"错误次数: {self.total_errors}")
        print("=================\n")

    def run(self):
        print("=== 模拟开始 ===")
        threads = []
        for _ in range(MAX_THREADS):
            t = threading.Thread(target=self.worker_loop)
            t.start()
            threads.append(t)

        try:
            while not self.stop_flag:
                self.show_stats()
                time.sleep(STATS_INTERVAL)
                if (datetime.now() - self.start_time).total_seconds() >= MAX_RUNTIME:
                    self.stop_flag = True
        except KeyboardInterrupt:
            print("\n[中止] 手动终止")
            self.stop_flag = True

        for t in threads:
            t.join()

        self.show_stats()
        print("模拟结束")

if __name__ == "__main__":
    TrafficSimulator().run()
