import threading
import time
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys



MAX_THREADS = 10
STATS_INTERVAL = 600
MAX_RUNTIME = 601

class BrowserTrafficGenerator:
    def __init__(self):
        self.stop_flag = False
        self.visits_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        self.last_stats_time = self.start_time
        self.lock = threading.Lock()
        
        self.user_agents = self._load_user_agents()
        self.resolutions = [
            (1920, 1080), (1366, 768), 
            (1536, 864), (1440, 900),
            (1280, 720), (1600, 900)
        ]
        
        self.browsers = []
        for _ in range(MAX_THREADS):
            t = threading.Thread(target=self.browser_worker)
            t.start()
            self.browsers.append(t)
    
    def _load_user_agents(self):
        return [
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 99)}.0.{random.randint(1000, 9999)}.{random.randint(100, 999)} Safari/537.36",
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{random.randint(80, 95)}.0) Gecko/20100101 Firefox/{random.randint(80, 95)}.0",
            f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(11, 15)}_{random.randint(0, 7)}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{random.randint(12, 15)}.{random.randint(0, 7)} Safari/605.1.15",
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {random.randint(12, 15)}_{random.randint(0, 7)} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{random.randint(12, 15)}.0 Mobile/15E148 Safari/604.1"
        ]
    
    def _create_browser(self):
        chrome_options = Options()
        ua = random.choice(self.user_agents)
        width, height = random.choice(self.resolutions)
        
        chrome_options.add_argument(f"user-agent={ua}")
        chrome_options.add_argument(f"window-size={width},{height}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        prefs = {
            "profile.managed_default_content_settings.images": random.randint(1, 2),
            "profile.default_content_setting_values.notifications": random.randint(0, 1),
            "profile.managed_default_content_settings.javascript": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def _human_like_interaction(self, driver):
        try:
            for _ in range(random.randint(2, 5)):
                scroll_px = random.randint(200, 800)
                driver.execute_script(f"window.scrollBy(0, {scroll_px})")
                time.sleep(random.uniform(0.5, 2.0))
            
            actions = ActionChains(driver)
            for _ in range(random.randint(3, 7)):
                x_offset = random.randint(-100, 100)
                y_offset = random.randint(-100, 100)
                actions.move_by_offset(x_offset, y_offset)
                actions.pause(random.uniform(0.1, 0.7))
            actions.perform()
            
            clickable_elements = driver.find_elements(By.XPATH, "//a | //button | //input[@type='submit']")
            if clickable_elements:
                random.choice(clickable_elements[:5]).click()
                time.sleep(random.uniform(1.0, 3.0))
            
            if random.random() > 0.7:
                inputs = driver.find_elements(By.XPATH, "//input[@type='text'] | //textarea")
                if inputs:
                    elem = random.choice(inputs)
                    elem.click()
                    for char in "Test input {}".format(random.randint(1, 100)):
                        elem.send_keys(char)
                        time.sleep(random.uniform(0.05, 0.2))
                    time.sleep(random.uniform(0.5, 1.5))
        except Exception:
            pass
    
    def browser_worker(self):
        while not self.stop_flag:
            driver = None
            try:
                driver = self._create_browser()
                driver.get(TARGET_URL)
                time.sleep(random.uniform(3.0, 8.0))
                self._human_like_interaction(driver)
                
                for _ in range(random.randint(1, 4)):
                    links = driver.find_elements(By.TAG_NAME, "a")
                    if links:
                        random.choice(links[:10]).click()
                        time.sleep(random.uniform(2.0, 5.0))
                        self._human_like_interaction(driver)
                
                with self.lock:
                    self.visits_count += 1
            except Exception as e:
                with self.lock:
                    self.error_count += 1
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                
                if not self.stop_flag:
                    time.sleep(random.uniform(5.0, 15.0))
    
    def show_stats(self, force=False):
        now = datetime.now()
        elapsed = (now - self.start_time).total_seconds()
        
        if force or (now - self.last_stats_time).total_seconds() >= STATS_INTERVAL:
            remaining_time = max(0, MAX_RUNTIME - elapsed)
            
            print("\n=== 浏览统计 ===")
            print(f"运行时间: {timedelta(seconds=int(elapsed))}")
            print(f"剩余时间: {timedelta(seconds=int(remaining_time))}")
            print(f"成功访问次数: {self.visits_count}")
            print(f"错误计数: {self.error_count}")
            print(f"活跃浏览器实例: {threading.active_count() - 1}")
            print("=====================\n")
            
            self.last_stats_time = now
    
    def runtime_monitor(self):
        while not self.stop_flag:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed >= MAX_RUNTIME:
                self.stop_flag = True
                break
            time.sleep(1)
    
    def run(self):
        print(f"=== 启动 ===")
        print(f"最大浏览器实例: {MAX_THREADS}")
        print(f"统计间隔: {STATS_INTERVAL//60}分钟")
        print(f"最大运行时间: {timedelta(seconds=MAX_RUNTIME)}")
        print("按 Ctrl+C 可提前停止运行\n")
        
        monitor_thread = threading.Thread(target=self.runtime_monitor, daemon=True)
        monitor_thread.start()
        
        try:
            while not self.stop_flag:
                self.show_stats()
                time.sleep(10)
        except KeyboardInterrupt:
            self.stop_flag = True
        finally:
            for t in self.browsers:
                t.join()
            
            self.show_stats(force=True)
            print("流量生成器已停止")

if __name__ == "__main__":
    generator = BrowserTrafficGenerator()
    generator.run()