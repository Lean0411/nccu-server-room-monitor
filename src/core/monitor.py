"""
Main monitoring module for NCCU Server Room Monitor.

This module coordinates all monitoring activities, manages sensors,
handles alerts, and maintains the main monitoring loop.
"""

import asyncio
import gc
import logging
import signal
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.core.sensors import (
    SensorManager,
    SmokeSensor,
    FlameSensor,
    WaterSensor,
    DHT22Sensor,
    SensorReading
)
from src.core.camera import CameraManager
from src.alerts.alert_manager import AlertManager
from src.utils.config import Config
from src.utils.logger import setup_logging


class MonitorStatus:
    """Monitor system status tracking."""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_readings = 0
        self.total_alerts = 0
        self.last_alert_time: Optional[float] = None
        self.errors = 0
        self.memory_usage_mb = 0
        self.cpu_percent = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary."""
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "uptime_formatted": str(timedelta(seconds=int(uptime))),
            "total_readings": self.total_readings,
            "total_alerts": self.total_alerts,
            "last_alert_time": self.last_alert_time,
            "errors": self.errors,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_percent": self.cpu_percent
        }


class MonitorSystem:
    """Main monitoring system coordinator.
    
    This class manages the entire monitoring system, including sensor readings,
    camera capture, alert management, and system health monitoring.
    """
    
    def __init__(self, config: Config):
        """Initialize monitoring system.
        
        Args:
            config: System configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.status = MonitorStatus()
        
        # Initialize components
        self.sensor_manager = SensorManager()
        self.camera_manager = CameraManager(config)
        self.alert_manager = AlertManager(config)
        
        # Alert tracking
        self.alert_cooldowns: Dict[str, float] = {}
        self.alert_history: deque = deque(maxlen=100)
        
        # Performance monitoring
        self.performance_metrics: deque = deque(maxlen=60)
        self.last_gc_time = time.time()
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.alert_queue: asyncio.Queue = asyncio.Queue()
        
        self._setup_signal_handlers()
        self._initialize_sensors()
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()
        
    def _initialize_sensors(self):
        """Initialize and register all sensors."""
        try:
            # Initialize sensors based on configuration
            if self.config.sensors.smoke_enabled:
                smoke_sensor = SmokeSensor(
                    pin=self.config.sensors.smoke_pin,
                    threshold_count=self.config.sensors.smoke_threshold
                )
                self.sensor_manager.register_sensor(smoke_sensor)
                
            if self.config.sensors.flame_enabled:
                flame_sensor = FlameSensor(
                    pin=self.config.sensors.flame_pin,
                    threshold_count=self.config.sensors.flame_threshold
                )
                self.sensor_manager.register_sensor(flame_sensor)
                
            if self.config.sensors.water_enabled:
                water_sensor = WaterSensor(
                    pin=self.config.sensors.water_pin
                )
                self.sensor_manager.register_sensor(water_sensor)
                
            if self.config.sensors.dht22_enabled:
                dht_sensor = DHT22Sensor(
                    pin=self.config.sensors.dht22_pin
                )
                self.sensor_manager.register_sensor(dht_sensor)
                
            self.logger.info(f"Initialized {len(self.sensor_manager.sensors)} sensors")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize sensors: {e}")
            raise
    
    def start(self):
        """Start the monitoring system."""
        if self.running:
            self.logger.warning("Monitor system already running")
            return
            
        self.running = True
        self.logger.info("Starting NCCU Server Room Monitor System")
        
        # Start camera manager
        self.camera_manager.start()
        
        # Start monitoring loop
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start alert processor
        asyncio.create_task(self._process_alerts())
        
        self.logger.info("Monitor system started successfully")
        
    def stop(self):
        """Stop the monitoring system."""
        if not self.running:
            return
            
        self.logger.info("Stopping monitor system...")
        self.running = False
        
        # Stop camera
        self.camera_manager.stop()
        
        # Wait for threads to finish
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            
        self.logger.info("Monitor system stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            loop_start = time.time()
            
            try:
                # Read all sensors
                readings = self.sensor_manager.read_all()
                self.status.total_readings += len(readings)
                
                # Check for alerts
                alerts = self.sensor_manager.check_alerts()
                if alerts:
                    self._handle_alerts(alerts)
                
                # Capture camera frame
                self.camera_manager.capture_frame()
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Garbage collection if needed
                self._manage_memory()
                
                # Log status periodically
                if self.status.total_readings % 100 == 0:
                    self._log_status()
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                self.status.errors += 1
                
            # Maintain consistent loop timing
            elapsed = time.time() - loop_start
            sleep_time = max(0, self.config.monitor.interval - elapsed)
            time.sleep(sleep_time)
    
    def _handle_alerts(self, alert_sensors: List[str]):
        """Handle sensor alerts.
        
        Args:
            alert_sensors: List of sensor IDs in alert state
        """
        current_time = time.time()
        
        for sensor_id in alert_sensors:
            # Check cooldown
            if not self._check_alert_cooldown(sensor_id, current_time):
                continue
                
            sensor = self.sensor_manager.get_sensor(sensor_id)
            if not sensor:
                continue
                
            # Create alert
            alert_data = {
                "sensor_id": sensor_id,
                "sensor_name": sensor.name,
                "sensor_type": sensor.sensor_type.value,
                "timestamp": current_time,
                "reading": sensor.last_reading.to_dict() if sensor.last_reading else None
            }
            
            # Queue alert for processing
            asyncio.create_task(self.alert_queue.put(alert_data))
            
            # Update cooldown
            self.alert_cooldowns[sensor_id] = current_time
            self.status.total_alerts += 1
            self.status.last_alert_time = current_time
            
            # Log alert
            self.logger.warning(f"ALERT: {sensor.name} triggered!")
    
    def _check_alert_cooldown(self, sensor_id: str, current_time: float) -> bool:
        """Check if sensor is in cooldown period.
        
        Args:
            sensor_id: Sensor ID to check
            current_time: Current timestamp
            
        Returns:
            True if alert can be sent, False if in cooldown
        """
        last_alert = self.alert_cooldowns.get(sensor_id, 0)
        cooldown_period = self.config.alerts.cooldown_minutes * 60
        
        return (current_time - last_alert) >= cooldown_period
    
    async def _process_alerts(self):
        """Process queued alerts asynchronously."""
        while self.running:
            try:
                # Get alert from queue with timeout
                alert_data = await asyncio.wait_for(
                    self.alert_queue.get(),
                    timeout=1.0
                )
                
                # Get camera images for alert
                images = self.camera_manager.get_buffer_images()
                
                # Send alert
                success = await self.alert_manager.send_alert(
                    alert_type=alert_data["sensor_type"],
                    message=self._format_alert_message(alert_data),
                    images=images,
                    metadata=alert_data
                )
                
                if success:
                    self.alert_history.append(alert_data)
                    self.logger.info(f"Alert sent successfully for {alert_data['sensor_name']}")
                else:
                    self.logger.error(f"Failed to send alert for {alert_data['sensor_name']}")
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing alert: {e}")
    
    def _format_alert_message(self, alert_data: Dict[str, Any]) -> str:
        """Format alert message for notification.
        
        Args:
            alert_data: Alert information
            
        Returns:
            Formatted alert message
        """
        timestamp = datetime.fromtimestamp(alert_data["timestamp"])
        
        message = f"""
🚨 NCCU Server Room Alert
━━━━━━━━━━━━━━━━━━━━━

Alert Type: {alert_data['sensor_type'].upper()}
Sensor: {alert_data['sensor_name']}
Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Location: NCCU Building 1F Server Room

System Status:
• Total Alerts Today: {self.status.total_alerts}
• System Uptime: {self.status.to_dict()['uptime_formatted']}
• Active Sensors: {len(self.sensor_manager.sensors)}

Action Required: Please investigate immediately.

━━━━━━━━━━━━━━━━━━━━━
NCCU Monitoring System
        """
        return message.strip()
    
    def _update_performance_metrics(self):
        """Update system performance metrics."""
        try:
            import psutil
            
            process = psutil.Process()
            
            metrics = {
                "timestamp": time.time(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "open_files": len(process.open_files())
            }
            
            self.performance_metrics.append(metrics)
            self.status.memory_usage_mb = metrics["memory_mb"]
            self.status.cpu_percent = metrics["cpu_percent"]
            
        except Exception as e:
            self.logger.debug(f"Failed to update performance metrics: {e}")
    
    def _manage_memory(self):
        """Manage memory usage and trigger garbage collection if needed."""
        current_time = time.time()
        
        # Run GC every 5 minutes or if memory usage is high
        if (current_time - self.last_gc_time > 300 or 
            self.status.memory_usage_mb > self.config.monitor.max_memory_mb):
            
            gc.collect()
            self.last_gc_time = current_time
            self.logger.debug("Garbage collection completed")
            
            # Clear old performance metrics if memory is still high
            if self.status.memory_usage_mb > self.config.monitor.max_memory_mb * 0.9:
                self.performance_metrics.clear()
                self.alert_history.clear()
                self.logger.info("Cleared historical data to free memory")
    
    def _log_status(self):
        """Log system status."""
        status = self.status.to_dict()
        sensor_status = self.sensor_manager.get_all_status()
        
        self.logger.info(
            f"System Status - Uptime: {status['uptime_formatted']}, "
            f"Readings: {status['total_readings']}, "
            f"Alerts: {status['total_alerts']}, "
            f"Memory: {status['memory_usage_mb']:.1f}MB, "
            f"CPU: {status['cpu_percent']:.1f}%"
        )
        
        # Log sensor status
        for sensor_id, sensor_info in sensor_status.items():
            if sensor_info["status"] != "ok":
                self.logger.warning(
                    f"Sensor {sensor_info['name']} status: {sensor_info['status']}"
                )
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status.
        
        Returns:
            Dictionary containing full system status
        """
        return {
            "system": self.status.to_dict(),
            "sensors": self.sensor_manager.get_all_status(),
            "camera": self.camera_manager.get_status(),
            "alerts": {
                "total": len(self.alert_history),
                "recent": list(self.alert_history)[-10:],
                "cooldowns": self.alert_cooldowns
            },
            "performance": {
                "current": self.performance_metrics[-1] if self.performance_metrics else None,
                "average": self._calculate_average_metrics()
            }
        }
    
    def _calculate_average_metrics(self) -> Dict[str, float]:
        """Calculate average performance metrics.
        
        Returns:
            Dictionary of average metrics
        """
        if not self.performance_metrics:
            return {}
            
        metrics = list(self.performance_metrics)
        
        return {
            "avg_memory_mb": sum(m["memory_mb"] for m in metrics) / len(metrics),
            "avg_cpu_percent": sum(m["cpu_percent"] for m in metrics) / len(metrics),
            "avg_threads": sum(m["threads"] for m in metrics) / len(metrics)
        }
    
    def run(self):
        """Run the monitoring system (blocking)."""
        try:
            self.start()
            
            # Keep running until interrupted
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.stop()


def main():
    """Main entry point for the monitoring system."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = Config.load()
        
        # Create and run monitor system
        monitor = MonitorSystem(config)
        monitor.run()
        
    except Exception as e:
        logger.error(f"Failed to start monitoring system: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()