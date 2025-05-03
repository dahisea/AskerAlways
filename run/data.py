import threading
import requests
import time
import random
import socket
import struct
from datetime import datetime, timedelta



MAX_THREADS = 2000
STATS_INTERVAL = 600
MAX_RUNTIME = 4 * 3600
CHUNK_SIZE = 8192

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{0}.0.{1}.{2} Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{3}_{4}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{5}.0.{6} Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{7}.0) Gecko/20100101 Firefox/{8}.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS {9}_{10} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{11}.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android {12}; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{13}.0.{14}.{15} Mobile Safari/537.36"
]

def generate_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))

def generate_random_ua():
    template = random.choice(USER_AGENTS)
    if "Chrome" in template:
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

class TrafficGenerator:
    def __init__(self):
        self.url = TARGET_URL
        self.max_threads = MAX_THREADS
        self.current_threads = MAX_THREADS
        self.stop_flag = False
        self.total_bytes = 0
        self.error_count = 0
        self.start_time = datetime.now()
        self.last_stats_time = self.start_time
        self.lock = threading.Lock()
        
        self.workers = []
        for _ in range(self.max_threads):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            self.workers.append(t)
    
    def get_random_headers(self):
        ip = generate_random_ip()
        return {
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
            'X-Client-Version': str(random.randint(1, 10)) + '.' + str(random.randint(0, 9)),
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }
    
    def format_bytes(self, size):
        power = 2**10
        n = 0
        units = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
        while size > power and n < len(units)-1:
            size /= power
            n += 1
        return f"{size:.2f} {units[n]}"
    
    def show_stats(self, force=False):
        now = datetime.now()
        elapsed = (now - self.start_time).total_seconds()
        
        if force or (now - self.last_stats_time).total_seconds() >= STATS_INTERVAL:
            remaining_time = max(0, MAX_RUNTIME - elapsed)
            download_speed = self.total_bytes / max(elapsed, 1)
            
            print("\n=== 流量统计 ===")
            print(f"运行时间: {timedelta(seconds=int(elapsed))}")
            print(f"剩余时间: {timedelta(seconds=int(remaining_time))}")
            print(f"总流量: {self.format_bytes(self.total_bytes)}")
            print(f"平均速度: {self.format_bytes(download_speed)}/s")
            print(f"当前线程数: {self.current_threads}")
            print(f"错误计数: {self.error_count}")
            print("===============\n")
            
            self.last_stats_time = now
    
    def worker(self):
        while not self.stop_flag:
            try:
                headers = self.get_random_headers()
                with requests.get(
                    self.url, 
                    stream=True, 
                    timeout=30,
                    headers=headers
                ) as r:
                    r.raise_for_status()
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if self.stop_flag or not chunk:
                            break
                        with self.lock:
                            self.total_bytes += len(chunk)
            except Exception as e:
                with self.lock:
                    self.error_count += 1
                    if self.error_count % 5 == 0 and self.current_threads > 1:
                        self.current_threads -= 1
                        print(f"[警告] 网络不稳定，减少至 {self.current_threads} 线程 | 错误: {str(e)}")
    
    def adjust_threads(self):
        while not self.stop_flag:
            time.sleep(30)
            with self.lock:
                if self.error_count < 3 and self.current_threads < self.max_threads:
                    self.current_threads += 1
                    print(f"[优化] 网络状况良好，增加至 {self.current_threads} 线程")
    
    def runtime_monitor(self):
        while not self.stop_flag:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed >= MAX_RUNTIME:
                self.stop_flag = True
                print(f"\n[完成] 已达到最大运行时间 {timedelta(seconds=MAX_RUNTIME)}")
                break
            time.sleep(1)
    
    def run(self):
        print(f"=== 测试启动 ===")
        print(f"最大线程数: {self.max_threads}")
        print(f"统计间隔: {STATS_INTERVAL//60}分钟")
        print(f"最大运行时间: {timedelta(seconds=MAX_RUNTIME)}")
        print("按 Ctrl+C 可提前停止运行\n")
        
        adjust_thread = threading.Thread(target=self.adjust_threads, daemon=True)
        adjust_thread.start()
        
        monitor_thread = threading.Thread(target=self.runtime_monitor, daemon=True)
        monitor_thread.start()
        
        try:
            while not self.stop_flag:
                self.show_stats()
                time.sleep(10)
        except KeyboardInterrupt:
            self.stop_flag = True
            print("\n[中断] 用户请求停止")
        finally:
            monitor_thread.join()
            adjust_thread.join()
            
            self.show_stats(force=True)
            print("流量生成器已停止")

if __name__ == "__main__":
    generator = TrafficGenerator()
    generator.run()