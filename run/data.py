import threading
import time
import random
import socket
import struct
import requests
import json
from datetime import datetime, timedelta
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from requests.exceptions import RequestException
from urllib.parse import urlparse, urljoin




MAX_THREADS = 20
STATS_INTERVAL = 30
MAX_RUNTIME = 18000
REQUEST_TIMEOUT = 10
WEBDRIVER_TIMEOUT = 30
CHUNK_SIZE = 8192

HEADER_FIELDS = [
    'User-Agent', 'Accept', 'Accept-Language', 'Accept-Encoding',
    'Connection', 'DNT', 'Upgrade-Insecure-Requests', 'X-Real-IP',
    'X-Forwarded-For', 'Remote-Addr', 'X-Request-ID', 'X-Client-Version',
    'Pragma', 'Cache-Control'
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{0}.0.{1}.{2} Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{0}_{1}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{2}.0.{3} Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{0}.0) Gecko/20100101 Firefox/{1}.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS {0}_{1} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{2}.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android {0}; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{1}.0.{2}.{3} Mobile Safari/537.36"
]

class TrafficSimulator:
    def __init__(self):
        self.total_bytes = 0
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.redirect_count = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
        self.running = True
        self.domains = {urlparse(url).netloc for url in TARGET_URLS}
        
        # Per-domain statistics
        self.domain_stats = {domain: {
            'requests': 0,
            'success': 0,
            'errors': 0,
            'bytes': 0
        } for domain in self.domains}

    def get_random_target(self):
        """Select a random target URL from the list"""
        return random.choice(TARGET_URLS)

    def is_same_domain(self, url, current_domain):
        """Check if URL belongs to one of our target domains"""
        if not url:
            return False
        parsed = urlparse(url)
        return parsed.netloc in self.domains or not parsed.netloc

    def generate_random_url(self, base_url):
        """Generate a random URL based on the selected target"""
        random_path = ''.join(random.choices('0123456789', k=6))
        return urljoin(base_url.rstrip('/') + '/', random_path)

    def generate_random_ip(self):
        return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))

    def generate_random_ua(self):
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
        except (IndexError, KeyError):
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 99)}.0.{random.randint(1000, 9999)}.{random.randint(100, 999)} Safari/537.36"

    def generate_headers(self):
        ip = self.generate_random_ip()
        headers = {
            'User-Agent': self.generate_random_ua(),
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

    def handle_redirects(self, response, session, current_domain):
        if response.is_redirect and response.next:
            next_url = response.next.url
            if self.is_same_domain(next_url, current_domain):
                with self.lock:
                    self.redirect_count += 1
                    print(f"[Redirect] Following")
                return session.get(next_url, timeout=REQUEST_TIMEOUT)
        return response

    def interact_with_page(self, headers, target_url):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        for header, value in headers.items():
            options.add_argument(f'--header={header}: {value}')

        driver = None
        current_domain = urlparse(target_url).netloc
        try:
            driver = Chrome(options=options)
            driver.set_page_load_timeout(WEBDRIVER_TIMEOUT)
            
            random_url = self.generate_random_url(target_url)
            driver.get(random_url)
            
            html_size = 0
            logs = driver.get_log('performance')
            for entry in logs:
                try:
                    message = json.loads(entry['message'])['message']
                    if message['method'] == 'Network.responseReceived':
                        url = message['params']['response']['url']
                        if self.is_same_domain(url, current_domain):
                            size = message['params']['response'].get('encodedDataLength', 0)
                            html_size += size
                except (KeyError, ValueError):
                    continue

            current_url = driver.current_url
            if current_url != random_url:
                if not self.is_same_domain(current_url, current_domain):
                    raise Exception(f"Redirected to external domain")
                with self.lock:
                    self.redirect_count += 1
                    print(f"[Redirect] Browser followed")

            actions = ActionChains(driver)
            actions.send_keys(Keys.PAGE_DOWN).perform()
            time.sleep(random.uniform(10.5, 15))

            content_type = driver.execute_script("return document.contentType")
            cookies = driver.get_cookies()
            html_size += len(driver.page_source.encode('utf-8'))
            
            return content_type, cookies, driver.current_url, html_size, current_domain
        except WebDriverException as e:
            raise Exception(f"Selenium error: {str(e)}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def download_with_requests(self, cookies, headers, target_url, current_domain):
        random_url = self.generate_random_url(target_url)
        try:
            with requests.Session() as s:
                for c in cookies:
                    s.cookies.set(c['name'], c['value'])
                
                r = s.get(random_url, headers=headers, stream=True, timeout=REQUEST_TIMEOUT, allow_redirects=False)
                r = self.handle_redirects(r, s, current_domain)
                r.raise_for_status()
                final_url = r.url
                
                if not self.is_same_domain(final_url, current_domain):
                    raise Exception(f"Attempted to leave target domain")

                total = 0
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        break
                    total += len(chunk)
                return total, final_url
        except RequestException as e:
            raise Exception(f"Request error: {str(e)}")

    def update_domain_stats(self, domain, success=False, bytes_transferred=0):
        """Update statistics for a specific domain"""
        with self.lock:
            self.domain_stats[domain]['requests'] += 1
            if success:
                self.domain_stats[domain]['success'] += 1
                self.domain_stats[domain]['bytes'] += bytes_transferred
            else:
                self.domain_stats[domain]['errors'] += 1

    def simulate_session(self):
        while self.running and (datetime.now() - self.start_time).total_seconds() < MAX_RUNTIME:
            try:
                target_url = self.get_random_target()
                current_domain = urlparse(target_url).netloc
                
                with self.lock:
                    self.request_count += 1
                    self.domain_stats[current_domain]['requests'] += 1

                headers = self.generate_headers()
                content_type, cookies, used_url, html_size, domain = self.interact_with_page(headers, target_url)
                
                if not self.is_same_domain(used_url, domain):
                    raise Exception(f"Navigated away from target domain")

                with self.lock:
                    self.total_bytes += html_size
                    self.success_count += 1
                    self.domain_stats[domain]['success'] += 1
                    self.domain_stats[domain]['bytes'] += html_size
                    print(f"[Page Load] {html_size} bytes from (HTML)")

                if 'html' not in content_type.lower():
                    size, used_url = self.download_with_requests(cookies, headers, target_url, domain)
                    with self.lock:
                        self.total_bytes += size
                        self.domain_stats[domain]['bytes'] += size
                        print(f"[Download] {size} bytes")
            except Exception as e:
                with self.lock:
                    self.error_count += 1
                    if 'domain' in locals():
                        self.domain_stats[domain]['errors'] += 1
                    print(f"[Error] {str(e)}")
            
            time.sleep(random.uniform(1, 3))

    def print_stats(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        mb_transferred = self.total_bytes / (1024 * 1024)
        req_rate = self.request_count / elapsed if elapsed > 0 else 0
        success_rate = (self.success_count / self.request_count * 100) if self.request_count > 0 else 0
        
        print("\n=== Global Statistics ===")
        print(f"Running for: {timedelta(seconds=int(elapsed))}")
        print(f"Total requests: {self.request_count}")
        print(f"Successful: {self.success_count} ({success_rate:.1f}%)")
        print(f"Errors: {self.error_count}")
        print(f"Redirects: {self.redirect_count}")
        print(f"Data transferred: {mb_transferred:.2f} MB")
        print(f"Request rate: {req_rate:.2f} req/sec")
        
        print("\n=== Per-Domain Statistics ===")
        for domain, stats in self.domain_stats.items():
            domain_req_rate = stats['requests'] / elapsed if elapsed > 0 else 0
            domain_success_rate = (stats['success'] / stats['requests'] * 100) if stats['requests'] > 0 else 0
            domain_mb = stats['bytes'] / (1024 * 1024)
            
            print(f"  Requests: {stats['requests']} ({domain_req_rate:.2f} req/sec)")
            print(f"  Successful: {stats['success']} ({domain_success_rate:.1f}%)")
            print(f"  Errors: {stats['errors']}")
            print(f"  Data transferred: {domain_mb:.2f} MB")
        
        print("\n=================\n")

    def run(self):
        print(f"Maximum runtime: {timedelta(seconds=MAX_RUNTIME)}")
        print(f"Maximum threads: {MAX_THREADS}")
        
        threads = []
        for _ in range(min(MAX_THREADS, 20)):
            t = threading.Thread(target=self.simulate_session)
            t.daemon = True
            t.start()
            threads.append(t)

        try:
            while (datetime.now() - self.start_time).total_seconds() < MAX_RUNTIME:
                time.sleep(STATS_INTERVAL)
                self.print_stats()
        except KeyboardInterrupt:
            print("\nReceived interrupt signal, shutting down...")
        finally:
            self.running = False
            for t in threads:
                t.join(timeout=1)
            
            self.print_stats()
            print("Simulation completed.")

if __name__ == "__main__":
    simulator = TrafficSimulator()
    simulator.run()
