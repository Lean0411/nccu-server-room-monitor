#!/usr/bin/env python3
"""
NCCU 機房監控系統 - 優化版本
效能改進、記憶體優化、更好的錯誤處理
"""

import os
import sys
import time
import signal
import logging
import traceback
import threading
import queue
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager

# 確保在正確的目錄下運行
SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

# 設定日誌系統 - 使用 RotatingFileHandler 防止日誌檔案過大
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 檔案處理器 - 最大 10MB，保留 5 個備份
file_handler = RotatingFileHandler(
    LOG_DIR / "monitor.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# 控制台處理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

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
    """動態導入監控模組 - 延遲載入以減少啟動時間"""
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
    except ImportError as e:
        logger.error(f"模組導入失敗: {e}")
        logger.error("請確保已安裝所有必要的套件")
        return None
    except Exception as e:
        logger.error(f"未預期的錯誤: {e}")
        return None

class MonitorSystem:
    """監控系統核心類別 - 優化版"""
    
    def __init__(self):
        self.modules = None
        self.camera = None
        self.mq2 = None
        self.flame = None
        self.buffer = None
        self.smtp_config = {}
        self.fire_count = 0
        self.smoke_count = 0  # 新增煙霧計數器
        self.fire_threshold = 3
        self.smoke_threshold = 2  # 煙霧需要 2 次偵測
        self.last_fire_alert = None
        self.last_smoke_alert = None
        self.alert_cooldown = 300
        
        # 效能優化：使用執行緒池處理郵件發送
        self.alert_queue = None
        self.alert_thread = None
        
        # 記憶體優化：限制同時保存的影像檔案數量
        self.max_saved_images = 100
        self.saved_image_count = 0
        
    @contextmanager
    def camera_capture(self):
        """使用 context manager 確保資源正確釋放"""
        stream = self.modules['io'].BytesIO()
        try:
            yield stream
        finally:
            stream.close()
            
    def initialize(self):
        """初始化系統 - 加入更多錯誤檢查"""
        try:
            # 導入模組
            self.modules = import_monitor_modules()
            if not self.modules:
                return False
                
            # 載入環境變數
            self.modules['load_dotenv']()
            
            # SMTP 設定 - 驗證必要參數
            required_smtp_vars = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_TO"]
            missing_vars = [var for var in required_smtp_vars if not os.getenv(var)]
            
            if missing_vars:
                logger.warning(f"缺少 SMTP 設定: {', '.join(missing_vars)}")
                logger.warning("警報功能將被停用")
            
            self.smtp_config = {
                'HOST': os.getenv("SMTP_HOST", ""),
                'PORT': int(os.getenv("SMTP_PORT", 587)),
                'USER': os.getenv("SMTP_USER", ""),
                'PASS': os.getenv("SMTP_PASS", ""),
                'ALERT_TO': os.getenv("ALERT_TO", "")
            }
            
            # 監控參數 - 可從環境變數設定
            self.BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", 20))
            self.CAP_INTERVAL = int(os.getenv("CAP_INTERVAL", 5))
            self.ROI = tuple(map(int, os.getenv("ROI", "100,80,200,150").split(",")))
            self.OUT_DIR = os.getenv("OUT_DIR", "captures")
            
            # 建立輸出目錄
            os.makedirs(self.OUT_DIR, exist_ok=True)
            
            # 清理舊檔案（保留最近 7 天）
            self._cleanup_old_files()
            
            # 初始化感測器
            board = self.modules['board']
            digitalio = self.modules['digitalio']
            
            self.mq2 = digitalio.DigitalInOut(board.D17)
            self.mq2.direction = digitalio.Direction.INPUT
            
            self.flame = digitalio.DigitalInOut(board.D27)
            self.flame.direction = digitalio.Direction.INPUT
            
            # 初始化攝影機 - 使用較低解析度以節省記憶體
            self.camera = self.modules['PiCamera']()
            self.camera.resolution = (640, 480)
            self.camera.start_preview()
            time.sleep(2)  # 等待攝影機穩定
            
            # 初始化緩衝區
            self.buffer = self.modules['deque'](maxlen=self.BUFFER_SIZE)
            
            # 初始化警報佇列和執行緒
            self.alert_queue = queue.Queue()
            self.alert_thread = threading.Thread(target=self._alert_worker, daemon=True)
            self.alert_thread.start()
            
            logger.info("系統初始化完成")
            logger.info(f"監控參數: BUFFER_SIZE={self.BUFFER_SIZE}, CAP_INTERVAL={self.CAP_INTERVAL}, ROI={self.ROI}")
            return True
            
        except Exception as e:
            logger.error(f"系統初始化失敗: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _cleanup_old_files(self):
        """清理舊的監控檔案"""
        try:
            import glob
            from datetime import timedelta
            
            cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 天前
            
            for pattern in ["*.jpg", "*.zip"]:
                for filepath in glob.glob(os.path.join(self.OUT_DIR, pattern)):
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"已刪除舊檔案: {filepath}")
                        
        except Exception as e:
            logger.warning(f"清理舊檔案時發生錯誤: {e}")
    
    def capture_roi(self):
        """擷取 ROI 區域影像 - 優化記憶體使用"""
        try:
            with self.camera_capture() as stream:
                self.camera.capture(stream, format='jpeg', use_video_port=True)  # 使用 video port 加速
                stream.seek(0)
                
                # 只在需要時載入完整影像
                img = self.modules['Image'].open(stream)
                
                # 直接裁切 ROI 區域，避免載入整張影像到 numpy
                x, y, w, h = self.ROI
                roi_img = img.crop((x, y, x+w, y+h))
                
                # 轉換為 numpy array
                return self.modules['np'].array(roi_img)
                
        except Exception as e:
            logger.error(f"影像擷取失敗: {e}")
            return None
    
    def _alert_worker(self):
        """背景執行緒處理警報發送"""
        while True:
            try:
                alert_data = self.alert_queue.get()
                if alert_data is None:  # 停止信號
                    break
                    
                self._send_alert_internal(alert_data['event_type'], 
                                        alert_data['zip_bytes'], 
                                        alert_data['entries'])
                                        
            except Exception as e:
                logger.error(f"警報處理錯誤: {e}")
    
    def send_alert(self, event_type, zip_bytes, entries):
        """將警報加入佇列（非阻塞）"""
        try:
            self.alert_queue.put({
                'event_type': event_type,
                'zip_bytes': zip_bytes,
                'entries': entries
            })
        except Exception as e:
            logger.error(f"加入警報佇列失敗: {e}")
    
    def _send_alert_internal(self, event_type, zip_bytes, entries):
        """實際發送警報郵件"""
        try:
            if not all(self.smtp_config.values()):
                logger.warning("SMTP 設定不完整，跳過郵件發送")
                return
                
            msg = self.modules['MIMEMultipart']()
            msg["Subject"] = f"🚨【緊急警報】NCCU 大仁樓 1F 機房偵測到 {event_type} - {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"
            msg["From"] = self.smtp_config['USER']
            msg["To"] = self.smtp_config['ALERT_TO']
            
            # 簡化郵件內容以減少記憶體使用
            body = f"""🚨 NCCU 政治大學機房監控系統 - 緊急警報通知 🚨

偵測位置：NCCU 大仁樓 1F（樓梯旁）機房
事件類型：{event_type} 
偵測時間：{datetime.now().strftime('%Y年%m月%d日 %H時%M分%S秒')}
附件影像：{len(entries)} 張

請立即前往現場查看！

緊急聯絡人：李恩甫同學 (0958-242-580)

NCCU 機房監控系統"""
            
            msg.attach(self.modules['MIMEText'](body, "plain"))
            
            # 附加 ZIP 檔案
            part = self.modules['MIMEBase']("application", "zip")
            part.set_payload(zip_bytes.getvalue())
            self.modules['encoders'].encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{event_type}_alert.zip"')
            msg.attach(part)
            
            # 發送郵件 - 加入重試機制
            retry_count = 3
            for i in range(retry_count):
                try:
                    with self.modules['smtplib'].SMTP(self.smtp_config['HOST'], self.smtp_config['PORT']) as server:
                        server.starttls()
                        server.login(self.smtp_config['USER'], self.smtp_config['PASS'])
                        server.send_message(msg)
                    logger.info(f"警報郵件已發送: {event_type}")
                    break
                except Exception as e:
                    if i < retry_count - 1:
                        logger.warning(f"郵件發送失敗，重試 {i+1}/{retry_count}: {e}")
                        time.sleep(5)
                    else:
                        raise
                        
        except Exception as e:
            logger.error(f"郵件發送失敗: {e}")
    
    def save_event(self, event_type, entries):
        """保存事件記錄 - 優化 I/O 操作"""
        try:
            # 檢查磁碟空間
            if not self._check_disk_space():
                logger.warning("磁碟空間不足，跳過保存")
                return
                
            timestamp = entries[-1]['ts'].replace(' ', 'T')
            zip_path = os.path.join(self.OUT_DIR, f"{event_type}_{timestamp}.zip")
            
            # 使用記憶體緩衝區減少 I/O
            with self.modules['io'].BytesIO() as buf:
                with self.modules['zipfile'].ZipFile(buf, "w", compression=self.modules['zipfile'].ZIP_DEFLATED) as zf:
                    for i, e in enumerate(entries):
                        fn = f"{event_type}_{i+1}_{e['ts'].replace(' ', 'T')}.jpg"
                        im = self.modules['Image'].fromarray(e["img"])
                        with self.modules['io'].BytesIO() as img_buf:
                            im.save(img_buf, format="JPEG", quality=85)  # 降低品質以節省空間
                            zf.writestr(fn, img_buf.getvalue())
                
                # 保存到磁碟
                buf.seek(0)
                with open(zip_path, 'wb') as f:
                    f.write(buf.getvalue())
                
                # 發送警報（非阻塞）
                buf.seek(0)
                self.send_alert(event_type, buf, entries)
                
            logger.info(f"事件已保存: {event_type} - {len(entries)} 張影像")
            
            # 更新計數器
            self.saved_image_count += len(entries)
            if self.saved_image_count > self.max_saved_images:
                self._cleanup_old_files()
                self.saved_image_count = 0
                
        except Exception as e:
            logger.error(f"事件保存失敗: {e}")
    
    def _check_disk_space(self):
        """檢查磁碟空間"""
        try:
            stat = os.statvfs(self.OUT_DIR)
            free_mb = (stat.f_bavail * stat.f_frsize) / 1024 / 1024
            return free_mb > 100  # 至少需要 100MB 空間
        except:
            return True  # 如果無法檢查，假設有足夠空間
    
    def monitor_loop(self):
        """主要監控迴圈 - 優化版"""
        global running
        
        logger.info("開始監控...")
        
        # 效能計數器
        loop_count = 0
        last_stats_time = time.time()
        
        while running:
            try:
                loop_start = time.time()
                
                # 取得時間戳記
                ts = datetime.now().isoformat(sep=" ", timespec="seconds")
                
                # 擷取影像
                roi = self.capture_roi()
                if roi is None:
                    time.sleep(1)
                    continue
                
                # 讀取感測器
                smoke = not self.mq2.value
                fire = not self.flame.value
                
                # 建立記錄
                entry = {"ts": ts, "img": roi, "smoke": smoke, "fire": fire}
                self.buffer.append(entry)
                
                # 處理火焰偵測
                if fire:
                    self.fire_count += 1
                    if self.fire_count <= self.fire_threshold:
                        logger.info(f"偵測到火焰信號 ({self.fire_count}/{self.fire_threshold})")
                else:
                    self.fire_count = 0
                
                # 處理煙霧偵測
                if smoke:
                    self.smoke_count += 1
                    if self.smoke_count <= self.smoke_threshold:
                        logger.info(f"偵測到煙霧信號 ({self.smoke_count}/{self.smoke_threshold})")
                else:
                    self.smoke_count = 0
                
                # 檢查是否需要發送警報
                current_time = time.time()
                should_alert_fire = (self.fire_count >= self.fire_threshold and 
                                   (self.last_fire_alert is None or 
                                    current_time - self.last_fire_alert > self.alert_cooldown))
                
                should_alert_smoke = (self.smoke_count >= self.smoke_threshold and 
                                    (self.last_smoke_alert is None or 
                                     current_time - self.last_smoke_alert > self.alert_cooldown))
                
                # 處理警報
                if should_alert_fire or should_alert_smoke:
                    if should_alert_fire:
                        event_type = "FIRE"
                        self.last_fire_alert = current_time
                        self.fire_count = 0
                    else:
                        event_type = "SMOKE"
                        self.last_smoke_alert = current_time
                        self.smoke_count = 0
                    
                    logger.warning(f"偵測到 {event_type}！正在保存記錄...")
                    self.save_event(event_type, list(self.buffer))
                
                # 統計資訊（每分鐘記錄一次）
                loop_count += 1
                if current_time - last_stats_time > 60:
                    fps = loop_count / (current_time - last_stats_time)
                    logger.info(f"系統狀態 - FPS: {fps:.2f}, 緩衝區: {len(self.buffer)}/{self.BUFFER_SIZE}")
                    loop_count = 0
                    last_stats_time = current_time
                
                # 動態調整延遲以維持穩定的擷取間隔
                loop_time = time.time() - loop_start
                sleep_time = max(0, self.CAP_INTERVAL - loop_time)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("收到中斷信號")
                break
            except Exception as e:
                logger.error(f"監控迴圈錯誤: {e}")
                logger.error(traceback.format_exc())
                time.sleep(5)
    
    def cleanup(self):
        """清理資源"""
        try:
            # 停止警報執行緒
            if self.alert_queue:
                self.alert_queue.put(None)
                if self.alert_thread and self.alert_thread.is_alive():
                    self.alert_thread.join(timeout=5)
            
            # 關閉攝影機
            if self.camera:
                self.camera.close()
                logger.info("攝影機已關閉")
                
            # 清理感測器
            if self.mq2:
                self.mq2.deinit()
            if self.flame:
                self.flame.deinit()
                
        except Exception as e:
            logger.error(f"清理失敗: {e}")

def main():
    """主程式"""
    global running, restart_count
    
    # 註冊信號處理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("NCCU 機房監控系統啟動（優化版）")
    logger.info(f"PID: {os.getpid()}")
    
    while running and restart_count < max_restarts:
        try:
            # 建立監控系統
            monitor = MonitorSystem()
            
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