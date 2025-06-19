#!/usr/bin/env python3
"""
NCCU 機房監控系統 - 優化版本
專注於效能優化和儲存空間管理
"""

import os
import sys
import time
import signal
import logging
import traceback
import threading
import queue
import gc
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

# 確保在正確的目錄下運行
SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

# 設定日誌系統 - 優化版本
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

class RotatingFileHandler(logging.FileHandler):
    """自定義的日誌輪轉處理器，避免日誌檔案過大"""
    def __init__(self, filename, max_bytes=10*1024*1024, backup_count=3):
        super().__init__(filename)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
    def emit(self, record):
        if self.stream and self.stream.tell() > self.max_bytes:
            self.rotate()
        super().emit(record)
        
    def rotate(self):
        self.close()
        for i in range(self.backup_count - 1, 0, -1):
            old_name = f"{self.baseFilename}.{i}"
            new_name = f"{self.baseFilename}.{i + 1}"
            if os.path.exists(old_name):
                os.rename(old_name, new_name)
        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, f"{self.baseFilename}.1")
        self.stream = self._open()

# 設定優化的日誌系統
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(LOG_DIR / "monitor.log", max_bytes=10*1024*1024, backup_count=5),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 全域變數
running = True
restart_count = 0
max_restarts = 10

def signal_handler(signum, frame):
    """處理系統信號，優雅關閉"""
    global running
    logger.info(f"收到信號 {signum}，準備關閉系統...")
    running = False

def import_monitor_modules():
    """優化的模組導入"""
    try:
        import io
        import zipfile
        import smtplib
        from collections import deque
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email import encoders
        from picamera import PiCamera
        from PIL import Image
        import board
        import digitalio
        from dotenv import load_dotenv
        import numpy as np
        
        return {
            'io': io, 'zipfile': zipfile, 'smtplib': smtplib,
            'deque': deque, 'MIMEMultipart': MIMEMultipart,
            'MIMEBase': MIMEBase, 'MIMEText': MIMEText,
            'encoders': encoders, 'PiCamera': PiCamera,
            'Image': Image, 'board': board, 'digitalio': digitalio,
            'load_dotenv': load_dotenv, 'np': np
        }
    except Exception as e:
        logger.error(f"模組導入失敗: {e}")
        return None

class StorageManager:
    """儲存空間管理器"""
    
    def __init__(self, base_dir, max_size_gb=2.0, max_age_days=30):
        self.base_dir = Path(base_dir)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.max_age_days = max_age_days
        
    def get_directory_size(self):
        """計算目錄大小"""
        total_size = 0
        try:
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"計算目錄大小失敗: {e}")
        return total_size
    
    def cleanup_old_files(self):
        """清理過期檔案"""
        try:
            cutoff_time = time.time() - (self.max_age_days * 24 * 3600)
            deleted_count = 0
            freed_bytes = 0
            
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        freed_bytes += file_size
                    except Exception as e:
                        logger.warning(f"無法刪除檔案 {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"清理過期檔案: {deleted_count} 個檔案, 釋放 {freed_bytes/1024/1024:.1f} MB")
                
        except Exception as e:
            logger.error(f"清理過期檔案失敗: {e}")
    
    def cleanup_by_size(self):
        """按大小清理檔案"""
        try:
            current_size = self.get_directory_size()
            if current_size <= self.max_size_bytes:
                return
            
            # 取得所有檔案並按時間排序（舊的先刪除）
            files_with_time = []
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file():
                    files_with_time.append((file_path.stat().st_mtime, file_path))
            
            files_with_time.sort()  # 按時間排序
            
            deleted_count = 0
            freed_bytes = 0
            target_size = self.max_size_bytes * 0.8  # 清理到 80% 容量
            
            for mtime, file_path in files_with_time:
                if current_size - freed_bytes <= target_size:
                    break
                    
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    freed_bytes += file_size
                except Exception as e:
                    logger.warning(f"無法刪除檔案 {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"空間清理: 刪除 {deleted_count} 個檔案, 釋放 {freed_bytes/1024/1024:.1f} MB")
                
        except Exception as e:
            logger.error(f"空間清理失敗: {e}")
    
    def perform_cleanup(self):
        """執行清理作業"""
        logger.info("開始儲存空間清理...")
        self.cleanup_old_files()
        self.cleanup_by_size()
        
        # 強制垃圾回收
        gc.collect()

class PerformanceMonitor:
    """效能監控器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.frame_count = 0
        self.last_report_time = time.time()
        self.last_frame_count = 0
        
    def update_frame_count(self):
        """更新幀數計數"""
        self.frame_count += 1
        
    def get_fps(self):
        """計算 FPS"""
        current_time = time.time()
        elapsed = current_time - self.last_report_time
        if elapsed >= 60:  # 每分鐘報告一次
            frames_in_period = self.frame_count - self.last_frame_count
            fps = frames_in_period / elapsed
            self.last_report_time = current_time
            self.last_frame_count = self.frame_count
            return fps
        return None
    
    def get_uptime(self):
        """取得運行時間"""
        return time.time() - self.start_time

class OptimizedMonitorSystem:
    """優化的監控系統核心類別"""
    
    def __init__(self):
        self.modules = None
        self.camera = None
        self.mq2 = None
        self.flame = None
        self.buffer = None
        self.smtp_config = {}
        self.storage_manager = None
        self.performance_monitor = PerformanceMonitor()
        self.last_cleanup_time = 0
        self.email_queue = queue.Queue(maxsize=10)  # 限制郵件佇列大小
        self.email_thread = None
        self.last_alert_time = {}  # 防止重複警報
        
    def initialize(self):
        """初始化系統"""
        try:
            # 導入模組
            self.modules = import_monitor_modules()
            if not self.modules:
                return False
                
            # 載入環境變數
            self.modules['load_dotenv']()
            
            # SMTP 設定
            self.smtp_config = {
                'HOST': os.getenv("SMTP_HOST"),
                'PORT': int(os.getenv("SMTP_PORT", 587)),
                'USER': os.getenv("SMTP_USER"),
                'PASS': os.getenv("SMTP_PASS"),
                'ALERT_TO': os.getenv("ALERT_TO")
            }
            
            # 檢查必要設定
            if not all(self.smtp_config.values()):
                logger.warning("SMTP 設定不完整，警報功能可能無法使用")
            
            # 監控參數 - 優化版本
            self.BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", 15))  # 減少緩衝區大小
            self.CAP_INTERVAL = int(os.getenv("CAP_INTERVAL", 10))  # 增加間隔時間
            self.ROI = (
                int(os.getenv("ROI_X", 100)),
                int(os.getenv("ROI_Y", 80)),
                int(os.getenv("ROI_WIDTH", 200)),
                int(os.getenv("ROI_HEIGHT", 150))
            )
            self.OUT_DIR = "captures"
            self.IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", 75))  # JPEG 品質
            self.ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", 300))  # 警報冷卻時間(秒)
            
            # 建立輸出目錄
            os.makedirs(self.OUT_DIR, exist_ok=True)
            
            # 初始化儲存管理器
            max_storage_gb = float(os.getenv("MAX_STORAGE_GB", 1.0))
            max_age_days = int(os.getenv("MAX_AGE_DAYS", 7))
            self.storage_manager = StorageManager(self.OUT_DIR, max_storage_gb, max_age_days)
            
            # 初始化感測器
            board = self.modules['board']
            digitalio = self.modules['digitalio']
            
            self.mq2 = digitalio.DigitalInOut(board.D17)
            self.mq2.direction = digitalio.Direction.INPUT
            
            self.flame = digitalio.DigitalInOut(board.D27)
            self.flame.direction = digitalio.Direction.INPUT
            
            # 初始化攝影機 - 優化設定
            self.camera = self.modules['PiCamera']()
            self.camera.resolution = (320, 240)  # 降低解析度提升效能
            self.camera.framerate = 10  # 降低幀率
            self.camera.start_preview()
            time.sleep(2)
            
            # 初始化緩衝區
            self.buffer = self.modules['deque'](maxlen=self.BUFFER_SIZE)
            
            # 啟動郵件發送執行緒
            self.start_email_thread()
            
            logger.info("優化版監控系統初始化完成")
            logger.info(f"設定: 緩衝區={self.BUFFER_SIZE}, 間隔={self.CAP_INTERVAL}s, 品質={self.IMAGE_QUALITY}")
            return True
            
        except Exception as e:
            logger.error(f"系統初始化失敗: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def start_email_thread(self):
        """啟動郵件發送執行緒"""
        def email_worker():
            while running:
                try:
                    email_data = self.email_queue.get(timeout=5)
                    if email_data is None:  # 結束信號
                        break
                    self._send_email_sync(email_data)
                    self.email_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"郵件發送執行緒錯誤: {e}")
        
        self.email_thread = threading.Thread(target=email_worker, daemon=True)
        self.email_thread.start()
    
    def capture_roi_optimized(self):
        """優化的 ROI 擷取"""
        try:
            stream = self.modules['io'].BytesIO()
            self.camera.capture(stream, format='jpeg', quality=self.IMAGE_QUALITY)
            stream.seek(0)
            
            # 直接裁切，避免完整解碼
            img = self.modules['Image'].open(stream)
            x, y, w, h = self.ROI
            
            # 先裁切再轉換，減少記憶體使用
            roi_img = img.crop((x, y, x + w, y + h))
            roi_array = self.modules['np'].array(roi_img)
            
            # 手動清理
            img.close()
            del img
            roi_img.close()
            del roi_img
            
            return roi_array
            
        except Exception as e:
            logger.error(f"優化影像擷取失敗: {e}")
            return None
    
    def should_send_alert(self, event_type):
        """檢查是否應該發送警報（防止重複）"""
        current_time = time.time()
        last_time = self.last_alert_time.get(event_type, 0)
        
        if current_time - last_time >= self.ALERT_COOLDOWN:
            self.last_alert_time[event_type] = current_time
            return True
        return False
    
    def queue_alert_email(self, event_type, zip_bytes):
        """將警報郵件加入佇列"""
        if not self.should_send_alert(event_type):
            logger.info(f"跳過重複警報: {event_type}")
            return
            
        try:
            email_data = {
                'event_type': event_type,
                'zip_bytes': zip_bytes.getvalue(),
                'timestamp': datetime.now().isoformat()
            }
            self.email_queue.put_nowait(email_data)
            logger.info(f"警報郵件已加入佇列: {event_type}")
        except queue.Full:
            logger.warning("郵件佇列已滿，跳過此次警報")
    
    def _send_email_sync(self, email_data):
        """同步發送郵件"""
        try:
            if not all(self.smtp_config.values()):
                logger.warning("SMTP 設定不完整，跳過郵件發送")
                return
                
            event_type = email_data['event_type']
            zip_bytes = email_data['zip_bytes']
            timestamp = email_data['timestamp']
            
            msg = self.modules['MIMEMultipart']()
            msg["Subject"] = f"[NCCU 機房警報] {event_type} - {timestamp}"
            msg["From"] = self.smtp_config['USER']
            msg["To"] = self.smtp_config['ALERT_TO']
            
            body = f"NCCU 機房監控系統於 {timestamp} 偵測到 {event_type}，請立即檢查！\n\n附件包含事件發生時的影像記錄。"
            msg.attach(self.modules['MIMEText'](body, "plain"))
            
            # 附加 ZIP 檔案
            part = self.modules['MIMEBase']("application", "zip")
            part.set_payload(zip_bytes)
            self.modules['encoders'].encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{event_type}_alert.zip"')
            msg.attach(part)
            
            # 發送郵件
            with self.modules['smtplib'].SMTP(self.smtp_config['HOST'], self.smtp_config['PORT']) as server:
                server.starttls()
                server.login(self.smtp_config['USER'], self.smtp_config['PASS'])
                server.send_message(msg)
                
            logger.info(f"警報郵件發送成功: {event_type}")
            
        except Exception as e:
            logger.error(f"郵件發送失敗: {e}")
    
    def save_event_optimized(self, event_type, entries):
        """優化的事件保存"""
        try:
            timestamp = entries[-1]['ts'].replace(' ', 'T')
            zip_path = os.path.join(self.OUT_DIR, f"{event_type}_{timestamp}.zip")
            
            # 建立記憶體 ZIP
            with self.modules['io'].BytesIO() as buf:
                with self.modules['zipfile'].ZipFile(buf, "w", compression=self.modules['zipfile'].ZIP_DEFLATED) as zf:
                    for i, e in enumerate(entries):
                        fn = f"{event_type}_{i+1}_{e['ts'].replace(' ', 'T')}.jpg"
                        
                        # 直接從 numpy array 壓縮為 JPEG
                        im = self.modules['Image'].fromarray(e["img"])
                        with self.modules['io'].BytesIO() as img_buf:
                            im.save(img_buf, format="JPEG", quality=self.IMAGE_QUALITY, optimize=True)
                            zf.writestr(fn, img_buf.getvalue())
                        im.close()
                        del im
                
                # 同時保存到磁碟（使用相同的 ZIP 資料）
                with open(zip_path, 'wb') as f:
                    f.write(buf.getvalue())
                
                # 非同步發送警報
                buf.seek(0)
                self.queue_alert_email(event_type, buf)
                
            logger.info(f"事件已優化保存: {event_type} - {len(entries)} 張影像")
            
        except Exception as e:
            logger.error(f"事件保存失敗: {e}")
    
    def monitor_loop(self):
        """優化的主要監控迴圈"""
        global running
        
        logger.info("開始優化監控...")
        
        while running:
            try:
                # 取得時間戳記
                ts = datetime.now().isoformat(sep=" ", timespec="seconds")
                
                # 擷取影像
                roi = self.capture_roi_optimized()
                if roi is None:
                    time.sleep(1)
                    continue
                
                # 更新效能計數
                self.performance_monitor.update_frame_count()
                
                # 讀取感測器
                smoke = not self.mq2.value
                fire = not self.flame.value
                
                # 建立記錄
                entry = {"ts": ts, "img": roi, "smoke": smoke, "fire": fire}
                self.buffer.append(entry)
                
                # 檢查警報條件
                if smoke or fire:
                    event_type = "SMOKE" if smoke else "FIRE"
                    logger.warning(f"偵測到 {event_type}！正在保存記錄...")
                    self.save_event_optimized(event_type, list(self.buffer))
                
                # 定期清理儲存空間（每小時）
                current_time = time.time()
                if current_time - self.last_cleanup_time > 3600:
                    threading.Thread(target=self.storage_manager.perform_cleanup, daemon=True).start()
                    self.last_cleanup_time = current_time
                
                # 效能報告（每分鐘）
                fps = self.performance_monitor.get_fps()
                if fps is not None:
                    uptime = self.performance_monitor.get_uptime()
                    logger.info(f"效能報告 - FPS: {fps:.1f}, 運行時間: {uptime/3600:.1f}h, 總幀數: {self.performance_monitor.frame_count}")
                
                # 記憶體清理
                if self.performance_monitor.frame_count % 100 == 0:
                    gc.collect()
                
                time.sleep(self.CAP_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("收到中斷信號")
                break
            except Exception as e:
                logger.error(f"監控迴圈錯誤: {e}")
                logger.error(traceback.format_exc())
                time.sleep(5)  # 錯誤後稍等再繼續
    
    def cleanup(self):
        """清理資源"""
        try:
            # 停止郵件執行緒
            if self.email_thread and self.email_thread.is_alive():
                self.email_queue.put(None)  # 結束信號
                self.email_thread.join(timeout=5)
            
            if self.camera:
                self.camera.close()
                logger.info("攝影機已關閉")
                
            # 最後清理
            gc.collect()
            
        except Exception as e:
            logger.error(f"清理失敗: {e}")

def main():
    """主程式"""
    global running, restart_count
    
    # 註冊信號處理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("NCCU 機房監控系統啟動 (優化版)")
    logger.info(f"PID: {os.getpid()}")
    
    while running and restart_count < max_restarts:
        try:
            # 建立監控系統
            monitor = OptimizedMonitorSystem()
            
            # 初始化
            if not monitor.initialize():
                logger.error("系統初始化失敗")
                restart_count += 1
                time.sleep(10)
                continue
            
            # 開始監控
            monitor.monitor_loop()
            
            # 清理資源
            monitor.cleanup()
            
            if running:
                restart_count += 1
                logger.info(f"系統重啟 ({restart_count}/{max_restarts})")
                time.sleep(5)
            
        except Exception as e:
            logger.error(f"嚴重錯誤: {e}")
            logger.error(traceback.format_exc())
            restart_count += 1
            time.sleep(10)
    
    logger.info("NCCU 機房監控系統關閉")

if __name__ == "__main__":
    main()