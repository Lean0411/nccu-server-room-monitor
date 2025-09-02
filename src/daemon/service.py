"""
背景服務管理模組 - 處理系統的 daemon 服務

提供服務生命週期管理、訊號處理和健康檢查。
"""

import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from src.core.monitor import MonitorSystem
from src.utils.config import Config
from src.utils.logger import setup_logging, get_logger


class ServiceStatus:
    """服務狀態追蹤"""
    
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class DaemonService:
    """背景服務管理器"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化服務
        
        Args:
            config_path: 配置檔案路徑
        """
        self.status = ServiceStatus.STOPPED
        self.config = None
        self.monitor_system = None
        self.logger = None
        self.pid_file = Path("/var/run/nccu-monitor.pid")
        self.stop_requested = False
        
        # 載入配置
        self._load_config(config_path)
        
        # 設定日誌
        self._setup_logging()
        
        # 註冊訊號處理
        self._register_signal_handlers()
    
    def _load_config(self, config_path: Optional[Path] = None):
        """載入系統配置"""
        try:
            self.config = Config.load(config_path)
        except Exception as e:
            print(f"Failed to load config: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """設定日誌系統"""
        setup_logging(self.config)
        self.logger = get_logger(__name__)
        self.logger.info("Logging initialized")
    
    def _register_signal_handlers(self):
        """註冊系統訊號處理器"""
        # 處理終止訊號
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGHUP, self._handle_reload)
    
    def _handle_signal(self, signum, frame):
        """
        處理系統訊號
        
        Args:
            signum: 訊號編號
            frame: 當前堆疊框架
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received signal: {signal_name}")
        
        if signum in (signal.SIGTERM, signal.SIGINT):
            self.stop_requested = True
            self.stop()
    
    def _handle_reload(self, signum, frame):
        """
        處理重新載入訊號
        
        Args:
            signum: 訊號編號
            frame: 當前堆疊框架
        """
        self.logger.info("Received SIGHUP - reloading configuration")
        self.reload_config()
    
    def start(self):
        """啟動服務"""
        if self.status != ServiceStatus.STOPPED:
            self.logger.warning(f"Cannot start - service is {self.status}")
            return
        
        self.logger.info("Starting NCCU Monitor Service")
        self.status = ServiceStatus.STARTING
        
        try:
            # 寫入 PID 檔案
            self._write_pid()
            
            # 初始化監控系統
            self.monitor_system = MonitorSystem(self.config)
            
            # 啟動監控
            self.monitor_system.start()
            
            self.status = ServiceStatus.RUNNING
            self.logger.info("Service started successfully")
            
            # 主迴圈
            self._run_loop()
            
        except Exception as e:
            self.logger.error(f"Service start failed: {e}")
            self.status = ServiceStatus.ERROR
            raise
        finally:
            self._cleanup()
    
    def _run_loop(self):
        """主服務迴圈"""
        self.logger.info("Entering main service loop")
        
        while not self.stop_requested:
            try:
                # 檢查系統健康狀態
                if not self._health_check():
                    self.logger.warning("Health check failed")
                
                # 短暫休眠避免 CPU 過載
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error in service loop: {e}")
                
                # 錯誤計數和自動恢復邏輯
                if self._should_restart():
                    self._restart_monitor()
                else:
                    break
    
    def stop(self):
        """停止服務"""
        if self.status != ServiceStatus.RUNNING:
            return
        
        self.logger.info("Stopping service")
        self.status = ServiceStatus.STOPPING
        
        try:
            # 停止監控系統
            if self.monitor_system:
                self.monitor_system.stop()
            
            # 清理資源
            self._cleanup()
            
            self.status = ServiceStatus.STOPPED
            self.logger.info("Service stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping service: {e}")
            self.status = ServiceStatus.ERROR
    
    def reload_config(self):
        """重新載入配置"""
        try:
            # 載入新配置
            new_config = Config.load()
            
            # 驗證配置
            if self._validate_config(new_config):
                self.config = new_config
                
                # 套用新配置到監控系統
                if self.monitor_system:
                    self.monitor_system.reload_config(self.config)
                
                self.logger.info("Configuration reloaded successfully")
            else:
                self.logger.error("New configuration validation failed")
                
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
    
    def _validate_config(self, config: Config) -> bool:
        """
        驗證配置有效性
        
        Args:
            config: 要驗證的配置
            
        Returns:
            配置是否有效
        """
        # 基本驗證邏輯
        required_fields = ['smtp', 'alerts', 'sensors', 'camera']
        
        for field in required_fields:
            if not hasattr(config, field):
                self.logger.error(f"Missing required config field: {field}")
                return False
        
        return True
    
    def _health_check(self) -> bool:
        """
        執行健康檢查
        
        Returns:
            系統是否健康
        """
        if not self.monitor_system:
            return False
        
        try:
            status = self.monitor_system.get_status()
            
            # 檢查記憶體使用
            if status.get('memory_mb', 0) > self.config.monitor.max_memory_mb:
                self.logger.warning("Memory usage exceeds limit")
                return False
            
            # 檢查錯誤率
            error_rate = status.get('error_rate', 0)
            if error_rate > 0.1:  # 錯誤率超過 10%
                self.logger.warning(f"High error rate: {error_rate:.2%}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def _should_restart(self) -> bool:
        """
        判斷是否應該重啟監控系統
        
        Returns:
            是否應該重啟
        """
        # 實作重啟策略
        # 可以基於錯誤次數、時間間隔等因素
        return False
    
    def _restart_monitor(self):
        """重啟監控系統"""
        self.logger.info("Restarting monitor system")
        
        try:
            # 停止現有系統
            if self.monitor_system:
                self.monitor_system.stop()
            
            # 短暫等待
            time.sleep(5)
            
            # 重新初始化
            self.monitor_system = MonitorSystem(self.config)
            self.monitor_system.start()
            
            self.logger.info("Monitor system restarted successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to restart monitor: {e}")
            self.status = ServiceStatus.ERROR
    
    def _write_pid(self):
        """寫入 PID 檔案"""
        try:
            pid = os.getpid()
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.pid_file.write_text(str(pid))
            self.logger.debug(f"PID {pid} written to {self.pid_file}")
        except Exception as e:
            self.logger.error(f"Failed to write PID file: {e}")
    
    def _cleanup(self):
        """清理資源"""
        # 移除 PID 檔案
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except Exception as e:
                self.logger.error(f"Failed to remove PID file: {e}")
        
        # 關閉日誌處理器
        if self.logger:
            for handler in self.logger.handlers:
                handler.close()
    
    def get_status(self) -> dict:
        """
        取得服務狀態
        
        Returns:
            狀態資訊字典
        """
        status = {
            "service_status": self.status,
            "pid": os.getpid(),
            "uptime": None,
            "monitor_status": None
        }
        
        if self.monitor_system:
            try:
                status["monitor_status"] = self.monitor_system.get_status()
            except Exception:
                pass
        
        return status


def main():
    """服務主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NCCU Monitor Daemon Service")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground mode"
    )
    
    args = parser.parse_args()
    
    # 建立並啟動服務
    service = DaemonService(config_path=args.config)
    
    try:
        service.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Service error: {e}")
        sys.exit(1)
    finally:
        service.stop()


if __name__ == "__main__":
    main()