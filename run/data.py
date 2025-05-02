import threading
import requests
import time
from queue import Queue
from datetime import datetime, timedelta



MAX_THREADS = 2000                                    # 最大线程数
STATS_INTERVAL = 600                                # 统计间隔(秒)
CHUNK_SIZE = 8192                                  # 每次读取块大小

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
        self.queue = Queue()
        
        # 初始化工作线程
        self.workers = []
        for _ in range(self.max_threads):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            self.workers.append(t)
    
    def format_bytes(self, size):
        """将字节数转换为易读格式"""
        power = 2**10
        n = 0
        units = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
        while size > power and n < len(units)-1:
            size /= power
            n += 1
        return f"{size:.2f} {units[n]}"
    
    def show_stats(self, force=False):
        """显示统计信息"""
        now = datetime.now()
        elapsed = (now - self.start_time).total_seconds()
        
        if force or (now - self.last_stats_time).total_seconds() >= STATS_INTERVAL:
            download_speed = self.total_bytes / max(elapsed, 1)
            
            print("\n=== 流量统计 ===")
            print(f"运行时间: {timedelta(seconds=int(elapsed))}")
            print(f"总流量: {self.format_bytes(self.total_bytes)}")
            print(f"平均速度: {self.format_bytes(download_speed)}/s")
            print(f"当前线程数: {self.current_threads}")
            print(f"错误计数: {self.error_count}")
            print("===============\n")
            
            self.last_stats_time = now
    
    def worker(self):
        """工作线程，只下载数据不保存"""
        while not self.stop_flag:
            try:
                with requests.get(self.url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if self.stop_flag or not chunk:
                            break
                        with self.lock:
                            self.total_bytes += len(chunk)
            except Exception as e:
                with self.lock:
                    self.error_count += 1
                    # 错误较多时自动减少线程数
                    if self.error_count % 5 == 0 and self.current_threads > 1:
                        self.current_threads -= 1
                        print(f"网络不稳定，减少至 {self.current_threads} 线程")
    
    def adjust_threads(self):
        """动态调整线程数"""
        while not self.stop_flag:
            time.sleep(30)  # 每30秒检查一次
            with self.lock:
                if self.error_count < 3 and self.current_threads < self.max_threads:
                    self.current_threads += 1
                    print(f"网络状况良好，增加至 {self.current_threads} 线程")
    
    def run(self):
        print(f"=== 启动 ===")
        print(f"目标URL: {self.url}")
        print(f"最大线程数: {self.max_threads}")
        print(f"统计间隔: {STATS_INTERVAL//60}分钟")
        print("按 Ctrl+C 停止运行\n")
        
        # 启动线程调整器
        adjust_thread = threading.Thread(target=self.adjust_threads, daemon=True)
        adjust_thread.start()
        
        try:
            while not self.stop_flag:
                self.show_stats()
                time.sleep(10)  # 每10秒检查一次是否需要显示统计
        except KeyboardInterrupt:
            self.stop_flag = True
            adjust_thread.join()
            self.show_stats(force=True)
            print("\n流量生成器已停止")

if __name__ == "__main__":
    generator = TrafficGenerator()
    generator.run()
