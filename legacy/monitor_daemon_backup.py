#!/usr/bin/env python3
"""
NCCU 機房監控系統 - 守護程序版本
專為長期背景運作設計，具備自動重啟和錯誤恢復機制
"""

import os
import sys
import time
import signal
import logging
import traceback
from datetime import datetime
from pathlib import Path

# 確保在正確的目錄下運行
SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

# 設定日誌系統
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "monitor.log"),
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
    """動態導入監控模組"""
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

class MonitorSystem:
    """監控系統核心類別"""
    
    def __init__(self):
        self.modules = None
        self.camera = None
        self.mq2 = None
        self.flame = None
        self.buffer = None
        self.smtp_config = {}
        self.fire_count = 0
        self.fire_threshold = 3  # 需要連續 3 次偵測到火焰才觸發警報
        self.last_fire_alert = None
        self.alert_cooldown = 300  # 5 分鐘內不重複發送同類型警報
        
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
            
            # 監控參數
            self.BUFFER_SIZE = 20
            self.CAP_INTERVAL = 5
            self.ROI = (100, 80, 200, 150)
            self.OUT_DIR = "captures"
            
            # 建立輸出目錄
            os.makedirs(self.OUT_DIR, exist_ok=True)
            
            # 初始化感測器
            board = self.modules['board']
            digitalio = self.modules['digitalio']
            
            self.mq2 = digitalio.DigitalInOut(board.D17)
            self.mq2.direction = digitalio.Direction.INPUT
            
            self.flame = digitalio.DigitalInOut(board.D27)
            self.flame.direction = digitalio.Direction.INPUT
            
            # 初始化攝影機
            self.camera = self.modules['PiCamera']()
            self.camera.resolution = (640, 480)
            self.camera.start_preview()
            time.sleep(2)
            
            # 初始化緩衝區
            self.buffer = self.modules['deque'](maxlen=self.BUFFER_SIZE)
            
            logger.info("系統初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"系統初始化失敗: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def capture_roi(self):
        """擷取 ROI 區域影像"""
        try:
            stream = self.modules['io'].BytesIO()
            self.camera.capture(stream, format='jpeg')
            stream.seek(0)
            img = self.modules['Image'].open(stream).convert("RGB")
            np_img = self.modules['np'].array(img)
            x, y, w, h = self.ROI
            roi = np_img[y:y+h, x:x+w].copy()
            return roi
        except Exception as e:
            logger.error(f"影像擷取失敗: {e}")
            return None
    
    def send_alert(self, event_type, zip_bytes, entries):
        """發送警報郵件"""
        try:
            if not all(self.smtp_config.values()):
                logger.warning("SMTP 設定不完整，跳過郵件發送")
                return
                
            msg = self.modules['MIMEMultipart']()
            msg["Subject"] = f"🚨【緊急警報】NCCU 大仁樓 1F 機房偵測到 {event_type} - {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"
            msg["From"] = self.smtp_config['USER']
            msg["To"] = self.smtp_config['ALERT_TO']
            
            body = f"""🚨 NCCU 政治大學機房監控系統 - 緊急警報通知 🚨

偵測位置：NCCU 大仁樓 1F（樓梯旁）機房
事件類型：{event_type} 
偵測時間：{datetime.now().strftime('%Y年%m月%d日 %H時%M分%S秒')}

⚠️  警報詳情：
系統偵測到機房內有異常{event_type}反應，請立即派員前往現場查看！

📍 機房位置：
- 建築物：大仁樓
- 樓層：1樓
- 位置：樓梯旁機房

📞 緊急聯絡人：
李恩甫同學
電話：0958-242-580

📷 監控影像說明：
附件中包含 {len(entries)} 張連續拍攝的監控照片，完整記錄了警報觸發前後的現場狀況：

• 第 1 張照片：警報觸發前 {self.BUFFER_SIZE-1} 秒的正常狀態
• 第 2-{len(entries)-1} 張照片：異常狀況逐步發展的過程
• 第 {len(entries)} 張照片：警報觸發當下的現場畫面

請仔細查看這些連續的監控照片，特別注意以下幾點：
✓ 是否有明顯的煙霧或火光出現
✓ 機房設備是否有異常狀況（如冒煙、火花等）
✓ 環境光線、顏色是否有明顯變化
✓ 是否有人員在現場

這些照片以每秒一張的頻率連續拍攝，可以清楚看出事件的發展過程。

📋 緊急處理步驟：
1. 立即前往現場查看機房狀況
2. 確認是否有實際火災或煙霧
3. 如有緊急情況，請立即撥打119
4. 檢查所有機房設備是否正常運作
5. 處理完畢後請回報系統管理員處理結果

📎 附件說明：
本郵件附件為 ZIP 壓縮檔，包含警報觸發時的完整監控影像記錄。
• 檔案名稱：{event_type}_alert.zip
• 檔案內容：{len(entries)} 張 JPG 格式的高清監控照片
• 照片解析度：根據攝影機設定
• 拍攝時間：每張照片檔名包含精確時間戳記

⚠️ 重要提醒：
此為自動發送的警報郵件，系統將持續監控機房狀況。
若您無法查看附件或需要更多協助，請立即聯繫系統管理員。

NCCU 機房監控系統
政治大學資訊科學系"""
            msg.attach(self.modules['MIMEText'](body, "plain"))
            
            # 附加 ZIP 檔案
            part = self.modules['MIMEBase']("application", "zip")
            part.set_payload(zip_bytes.getvalue())
            self.modules['encoders'].encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{event_type}_alert.zip"')
            msg.attach(part)
            
            # 發送郵件
            with self.modules['smtplib'].SMTP(self.smtp_config['HOST'], self.smtp_config['PORT']) as server:
                server.starttls()
                server.login(self.smtp_config['USER'], self.smtp_config['PASS'])
                server.send_message(msg)
                
            logger.info(f"警報郵件已發送: {event_type}")
            
        except Exception as e:
            logger.error(f"郵件發送失敗: {e}")
    
    def save_event(self, event_type, entries):
        """保存事件記錄"""
        try:
            timestamp = entries[-1]['ts'].replace(' ', 'T')
            zip_path = os.path.join(self.OUT_DIR, f"{event_type}_{timestamp}.zip")
            
            # 保存到磁碟
            with self.modules['zipfile'].ZipFile(zip_path, "w") as zf:
                for i, e in enumerate(entries):
                    fn = f"{event_type}_{i+1}_{e['ts'].replace(' ', 'T')}.jpg"
                    img_path = os.path.join(self.OUT_DIR, fn)
                    self.modules['Image'].fromarray(e["img"]).save(img_path)
                    zf.write(img_path, arcname=fn)
            
            # 建立記憶體 ZIP 用於郵件
            with self.modules['io'].BytesIO() as buf:
                with self.modules['zipfile'].ZipFile(buf, "w") as zf:
                    for i, e in enumerate(entries):
                        fn = f"{event_type}_{i+1}_{e['ts'].replace(' ', 'T')}.jpg"
                        im = self.modules['Image'].fromarray(e["img"])
                        with self.modules['io'].BytesIO() as img_buf:
                            im.save(img_buf, format="JPEG")
                            zf.writestr(fn, img_buf.getvalue())
                
                # 發送警報
                self.send_alert(event_type, buf, entries)
                
            logger.info(f"事件已保存: {event_type} - {len(entries)} 張影像")
            
        except Exception as e:
            logger.error(f"事件保存失敗: {e}")
    
    def monitor_loop(self):
        """主要監控迴圈"""
        global running
        
        logger.info("開始監控...")
        
        while running:
            try:
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
                
                # 處理火焰偵測（需要連續多次偵測才觸發）
                if fire:
                    self.fire_count += 1
                    logger.info(f"偵測到火焰信號 ({self.fire_count}/{self.fire_threshold})")
                else:
                    self.fire_count = 0  # 重置計數器
                
                # 檢查是否需要發送警報
                current_time = time.time()
                should_alert_fire = (self.fire_count >= self.fire_threshold and 
                                   (self.last_fire_alert is None or 
                                    current_time - self.last_fire_alert > self.alert_cooldown))
                
                # 檢查警報條件
                if smoke or should_alert_fire:
                    if should_alert_fire:
                        event_type = "FIRE"
                        self.last_fire_alert = current_time
                        self.fire_count = 0  # 重置計數器
                    else:
                        event_type = "SMOKE"
                    
                    logger.warning(f"偵測到 {event_type}！正在保存記錄...")
                    self.save_event(event_type, list(self.buffer))
                
                # 記錄狀態（每 10 次記錄一次以免日誌過多）
                if len(self.buffer) % 10 == 0:
                    logger.info(f"系統正常運作 - 緩衝區: {len(self.buffer)}/{self.BUFFER_SIZE}")
                
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
            if self.camera:
                self.camera.close()
                logger.info("攝影機已關閉")
        except Exception as e:
            logger.error(f"清理失敗: {e}")

def main():
    """主程式"""
    global running, restart_count
    
    # 註冊信號處理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("NCCU 機房監控系統啟動")
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