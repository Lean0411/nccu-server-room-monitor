#!/usr/bin/env python3
"""
NCCU 機房監控系統 - 看門狗程式
定期檢查監控系統健康狀態，必要時自動重啟
"""

import os
import time
import logging
import subprocess
import psutil
from datetime import datetime, timedelta
from pathlib import Path

# 設定
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日誌設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [WATCHDOG] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "watchdog.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MonitorWatchdog:
    def __init__(self):
        self.service_name = "nccu-monitor"
        self.log_file = LOG_DIR / "monitor.log"
        self.max_memory_mb = 512  # 最大記憶體使用量 (MB)
        self.max_cpu_percent = 90  # 最大 CPU 使用率
        self.log_check_minutes = 10  # 檢查日誌活動的時間間隔
        self.restart_count = 0
        self.max_daily_restarts = 5
        self.last_restart_date = None
        
    def is_service_running(self):
        """檢查服務是否運行"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                capture_output=True, text=True
            )
            return result.returncode == 0 and result.stdout.strip() == "active"
        except Exception as e:
            logger.error(f"檢查服務狀態失敗: {e}")
            return False
    
    def get_service_pid(self):
        """取得服務的 PID"""
        try:
            result = subprocess.run(
                ["systemctl", "show", self.service_name, "--property=MainPID", "--value"],
                capture_output=True, text=True
            )
            pid = int(result.stdout.strip())
            return pid if pid > 0 else None
        except Exception:
            return None
    
    def check_resource_usage(self):
        """檢查資源使用情況"""
        pid = self.get_service_pid()
        if not pid:
            return True, "服務未運行"
        
        try:
            process = psutil.Process(pid)
            
            # 檢查記憶體使用量
            memory_mb = process.memory_info().rss / 1024 / 1024
            if memory_mb > self.max_memory_mb:
                return False, f"記憶體使用過高: {memory_mb:.1f}MB > {self.max_memory_mb}MB"
            
            # 檢查 CPU 使用率
            cpu_percent = process.cpu_percent(interval=1)
            if cpu_percent > self.max_cpu_percent:
                return False, f"CPU 使用率過高: {cpu_percent:.1f}% > {self.max_cpu_percent}%"
            
            return True, f"資源使用正常 (記憶體: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%)"
            
        except psutil.NoSuchProcess:
            return False, "程序不存在"
        except Exception as e:
            return False, f"資源檢查失敗: {e}"
    
    def check_log_activity(self):
        """檢查日誌活動"""
        if not self.log_file.exists():
            return False, "日誌檔案不存在"
        
        try:
            # 檢查檔案最後修改時間
            mtime = datetime.fromtimestamp(self.log_file.stat().st_mtime)
            time_diff = datetime.now() - mtime
            
            if time_diff > timedelta(minutes=self.log_check_minutes):
                return False, f"日誌超過 {self.log_check_minutes} 分鐘無更新"
            
            return True, f"日誌活動正常 (最後更新: {time_diff.seconds//60} 分鐘前)"
            
        except Exception as e:
            return False, f"日誌檢查失敗: {e}"
    
    def restart_service(self):
        """重啟服務"""
        today = datetime.now().date()
        
        # 重置每日重啟計數
        if self.last_restart_date != today:
            self.restart_count = 0
            self.last_restart_date = today
        
        # 檢查重啟次數限制
        if self.restart_count >= self.max_daily_restarts:
            logger.error(f"今日重啟次數已達上限 ({self.max_daily_restarts} 次)")
            return False
        
        try:
            logger.warning("正在重啟監控服務...")
            
            # 重啟服務
            result = subprocess.run(
                ["sudo", "systemctl", "restart", self.service_name],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self.restart_count += 1
                logger.info(f"服務重啟成功 (今日第 {self.restart_count} 次)")
                
                # 等待服務啟動
                time.sleep(10)
                
                if self.is_service_running():
                    logger.info("服務重啟後運行正常")
                    return True
                else:
                    logger.error("服務重啟後仍未正常運行")
                    return False
            else:
                logger.error(f"服務重啟失敗: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"重啟服務時發生錯誤: {e}")
            return False
    
    def perform_health_check(self):
        """執行健康檢查"""
        logger.info("開始健康檢查...")
        
        issues = []
        
        # 檢查服務狀態
        if not self.is_service_running():
            issues.append("服務未運行")
        else:
            logger.info("✓ 服務運行正常")
            
            # 檢查資源使用
            resource_ok, resource_msg = self.check_resource_usage()
            if resource_ok:
                logger.info(f"✓ {resource_msg}")
            else:
                issues.append(resource_msg)
            
            # 檢查日誌活動
            log_ok, log_msg = self.check_log_activity()
            if log_ok:
                logger.info(f"✓ {log_msg}")
            else:
                issues.append(log_msg)
        
        # 如果有問題，嘗試重啟
        if issues:
            logger.warning(f"發現問題: {'; '.join(issues)}")
            
            if self.restart_service():
                logger.info("問題已通過重啟解決")
            else:
                logger.error("重啟失敗，需要人工介入")
        else:
            logger.info("健康檢查通過")
    
    def run(self, check_interval=300):
        """運行看門狗 (預設每5分鐘檢查一次)"""
        logger.info("監控看門狗啟動")
        logger.info(f"檢查間隔: {check_interval} 秒")
        
        try:
            while True:
                self.perform_health_check()
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("看門狗程式結束")
        except Exception as e:
            logger.error(f"看門狗程式錯誤: {e}")

def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NCCU 監控系統看門狗")
    parser.add_argument("--interval", type=int, default=300,
                        help="檢查間隔 (秒，預設 300)")
    parser.add_argument("--check-once", action="store_true",
                        help="只執行一次檢查")
    
    args = parser.parse_args()
    
    watchdog = MonitorWatchdog()
    
    if args.check_once:
        watchdog.perform_health_check()
    else:
        watchdog.run(args.interval)

if __name__ == "__main__":
    main()