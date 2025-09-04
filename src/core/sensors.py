"""
感測器模組 - 管理所有環境感測器

提供煙霧、火焰、溫濕度和水位感測器的統一介面。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import logging
import time
from collections import deque

import board
import digitalio
# import adafruit_dht
from adafruit_ahtx0 import AHTx0

class SensorType(Enum):
    """感測器類型列舉"""
    
    SMOKE = "smoke"          # 煙霧感測器
    FLAME = "flame"          # 火焰感測器
    TEMPERATURE = "temperature"  # 溫度感測器
    HUMIDITY = "humidity"    # 濕度感測器
    WATER = "water"          # 水位感測器


class SensorStatus(Enum):
    """感測器運作狀態"""
    
    OK = "ok"                # 正常
    WARNING = "warning"      # 警告
    ERROR = "error"          # 錯誤
    OFFLINE = "offline"      # 離線


@dataclass
class SensorReading:
    """感測器讀數資料結構
    
    Attributes:
        timestamp: 讀取時間戳
        value: 感測器數值
        sensor_type: 感測器類型
        sensor_id: 感測器識別碼
        unit: 測量單位
        raw_value: 原始讀數
        metadata: 其他元資料
    """
    
    timestamp: float
    value: Any
    sensor_type: SensorType
    sensor_id: str
    unit: Optional[str] = None
    raw_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reading to dictionary format."""
        return {
            "timestamp": self.timestamp,
            "datetime": self.datetime.isoformat(),
            "value": self.value,
            "sensor_type": self.sensor_type.value,
            "sensor_id": self.sensor_id,
            "unit": self.unit,
            "raw_value": self.raw_value,
            "metadata": self.metadata
        }


class BaseSensor(ABC):
    """感測器基礎類別
    
    定義所有感測器必須實作的介面，
    提供歷史記錄、狀態追蹤等共同功能。
    """
    
    def __init__(
        self,
        sensor_id: str,
        sensor_type: SensorType,
        name: str,
        history_size: int = 100
    ) -> None:
        """Initialize base sensor.
        
        Args:
            sensor_id: Unique identifier for the sensor
            sensor_type: Type of sensor
            name: Human-readable name
            history_size: Number of readings to keep in history
        """
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.name = name
        self.history_size = history_size
        self.history: deque = deque(maxlen=history_size)
        self.status = SensorStatus.OFFLINE
        self.last_reading: Optional[SensorReading] = None
        self.error_count = 0
        self.logger = logging.getLogger(f"{__name__}.{self.sensor_id}")
        
    @abstractmethod
    def read(self) -> SensorReading:
        """Read current sensor value.
        
        Returns:
            SensorReading object with current value
            
        Raises:
            SensorException: If sensor read fails
        """
        pass
    
    @abstractmethod
    def calibrate(self) -> None:
        """Calibrate the sensor.
        
        This method should implement sensor-specific calibration logic.
        """
        pass
    
    @abstractmethod
    def validate_reading(self, reading: SensorReading) -> bool:
        """Validate a sensor reading.
        
        Args:
            reading: The reading to validate
            
        Returns:
            True if reading is valid, False otherwise
        """
        pass
    
    def read_with_retry(self, max_retries: int = 3, delay: float = 0.5) -> Optional[SensorReading]:
        """Read sensor value with retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            SensorReading if successful, None otherwise
        """
        for attempt in range(max_retries):
            try:
                reading = self.read()
                if self.validate_reading(reading):
                    self.last_reading = reading
                    self.history.append(reading)
                    self.status = SensorStatus.OK
                    self.error_count = 0
                    return reading
                else:
                    self.logger.warning(
                        f"Invalid reading from {self.name}: {reading.value}"
                    )
            except Exception as e:
                self.error_count += 1
                self.logger.error(
                    f"Error reading {self.name} (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)
        
        self.status = SensorStatus.ERROR
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current sensor status.
        
        Returns:
            Dictionary containing sensor status information
        """
        return {
            "sensor_id": self.sensor_id,
            "name": self.name,
            "type": self.sensor_type.value,
            "status": self.status.value,
            "error_count": self.error_count,
            "last_reading": self.last_reading.to_dict() if self.last_reading else None,
            "history_size": len(self.history)
        }
    
    def get_average(self, window_size: int = 10) -> Optional[float]:
        """Calculate average of recent readings.
        
        Args:
            window_size: Number of recent readings to average
            
        Returns:
            Average value or None if insufficient data
        """
        if not self.history:
            return None
        
        recent_readings = list(self.history)[-window_size:]
        
        try:
            values = [r.value for r in recent_readings if isinstance(r.value, (int, float))]
            return sum(values) / len(values) if values else None
        except (TypeError, ValueError):
            return None


class DigitalSensor(BaseSensor):
    """Base class for digital GPIO sensors."""
    
    def __init__(
        self,
        sensor_id: str,
        sensor_type: SensorType,
        name: str,
        pin: Any,
        pull_up: bool = False,
        inverted: bool = False,
        history_size: int = 100
    ) -> None:
        """Initialize digital sensor.
        
        Args:
            sensor_id: Unique identifier
            sensor_type: Type of sensor
            name: Human-readable name
            pin: GPIO pin object
            pull_up: Whether to enable pull-up resistor
            inverted: Whether to invert the logic (LOW = triggered)
            history_size: Number of readings to keep
        """
        super().__init__(sensor_id, sensor_type, name, history_size)
        self.pin = pin
        self.pull_up = pull_up
        self.inverted = inverted
        self._setup_pin()
        
    def _setup_pin(self) -> None:
        """Configure GPIO pin."""
        try:
            self.gpio = digitalio.DigitalInOut(self.pin)
            self.gpio.direction = digitalio.Direction.INPUT
            
            if self.pull_up:
                self.gpio.pull = digitalio.Pull.UP
            else:
                self.gpio.pull = digitalio.Pull.DOWN
                
            self.status = SensorStatus.OK
        except Exception as e:
            self.logger.error(f"Failed to setup GPIO pin: {e}")
            self.status = SensorStatus.ERROR
            raise
    
    def read(self) -> SensorReading:
        """Read digital sensor value."""
        raw_value = self.gpio.value
        value = not raw_value if self.inverted else raw_value
        
        return SensorReading(
            timestamp=time.time(),
            value=value,
            sensor_type=self.sensor_type,
            sensor_id=self.sensor_id,
            raw_value=raw_value,
            metadata={"inverted": self.inverted}
        )
    
    def validate_reading(self, reading: SensorReading) -> bool:
        """Validate digital reading."""
        return isinstance(reading.value, bool)
    
    def calibrate(self) -> None:
        """Digital sensors typically don't need calibration."""
        self.logger.info(f"Calibration not required for {self.name}")


class SmokeSensor(DigitalSensor):
    """MQ-2 Smoke sensor implementation."""
    
    def __init__(
        self,
        sensor_id: str = "smoke_1",
        name: str = "MQ-2 Smoke Sensor",
        pin: Any = board.D17,
        threshold_count: int = 2
    ) -> None:
        """Initialize smoke sensor.
        
        Args:
            sensor_id: Unique identifier
            name: Human-readable name
            pin: GPIO pin (default: GPIO 17)
            threshold_count: Consecutive detections required for alert
        """
        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.SMOKE,
            name=name,
            pin=pin,
            pull_up=False,
            inverted=True  # MQ-2 goes LOW when smoke detected
        )
        self.threshold_count = threshold_count
        self.consecutive_detections = 0
        
    def is_triggered(self) -> bool:
        """Check if smoke threshold is met.
        
        Returns:
            True if consecutive detections meet threshold
        """
        reading = self.read_with_retry()
        if reading and reading.value:
            self.consecutive_detections += 1
        else:
            self.consecutive_detections = 0
            
        return self.consecutive_detections >= self.threshold_count


class FlameSensor(DigitalSensor):
    """Flame sensor implementation."""
    
    def __init__(
        self,
        sensor_id: str = "flame_1",
        name: str = "Flame Sensor",
        pin: Any = board.D27,
        threshold_count: int = 3
    ) -> None:
        """Initialize flame sensor.
        
        Args:
            sensor_id: Unique identifier
            name: Human-readable name
            pin: GPIO pin (default: GPIO 27)
            threshold_count: Consecutive detections required for alert
        """
        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.FLAME,
            name=name,
            pin=pin,
            pull_up=False,
            inverted=True  # Flame sensor goes LOW when fire detected
        )
        self.threshold_count = threshold_count
        self.consecutive_detections = 0
        
    def is_triggered(self) -> bool:
        """Check if flame threshold is met.
        
        Returns:
            True if consecutive detections meet threshold
        """
        reading = self.read_with_retry()
        if reading and reading.value:
            self.consecutive_detections += 1
        else:
            self.consecutive_detections = 0
            
        return self.consecutive_detections >= self.threshold_count


class WaterSensor(DigitalSensor):
    """Water level sensor implementation."""
    
    def __init__(
        self,
        sensor_id: str = "water_1",
        name: str = "Water Sensor",
        pin: Any = board.D22
    ) -> None:
        """Initialize water sensor.
        
        Args:
            sensor_id: Unique identifier
            name: Human-readable name
            pin: GPIO pin (default: GPIO 22)
        """
        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.WATER,
            name=name,
            pin=pin,
            pull_up=True,  # Use pull-up for water sensor
            inverted=True  # Water detected when pin goes LOW
        )


class AHTSensor(BaseSensor):
    """AHT Temperature and Humidity sensor implementation."""
    
    def __init__(
        self,
        sensor_id: str = "AHT",
        name: str = "AHT Sensor",
        pin: Any = board.I2C()
    ) -> None:
        """Initialize AHT sensor.
        
        Args:
            sensor_id: Unique identifier
            name: Human-readable name
            pin: I2C pin (default: (GPIO 2, GPIO 3))
        """
        super().__init__(
            sensor_id=sensor_id,
            sensor_type=SensorType.TEMPERATURE,
            name=name
        )
        self.pin = pin
        self._setup_sensor()
        
    def _setup_sensor(self) -> None:
        """Setup DHT22 sensor."""
        try:
            self.aht = AHTx0(self.pin)
            self.status = SensorStatus.OK
        except Exception as e:
            self.logger.error(f"Failed to setup DHT22: {e}")
            self.status = SensorStatus.ERROR
            raise
    
    def read(self) -> SensorReading:
        """Read temperature and humidity."""
        temperature = self.aht.temperature
        humidity = self.aht.relative_humidity
        
        return SensorReading(
            timestamp=time.time(),
            value={"temperature": temperature, "humidity": humidity},
            sensor_type=self.sensor_type,
            sensor_id=self.sensor_id,
            unit="°C/%",
            metadata={
                "temperature": temperature,
                "humidity": humidity
            }
        )
    
    def read_temperature(self) -> Optional[float]:
        """Read only temperature value."""
        try:
            return self.aht.temperature
        except Exception as e:
            self.logger.error(f"Error reading temperature: {e}")
            return None
    
    def read_humidity(self) -> Optional[float]:
        """Read only humidity value."""
        try:
            return self.aht.relative_humidity
        except Exception as e:
            self.logger.error(f"Error reading humidity: {e}")
            return None
    
    def validate_reading(self, reading: SensorReading) -> bool:
        """Validate DHT22 reading."""
        if not isinstance(reading.value, dict):
            return False
        
        temp = reading.value.get("temperature")
        humidity = reading.value.get("humidity")
        
        # Validate temperature range (-40 to 80°C)
        if temp is None or temp < -40 or temp > 80:
            return False
        
        # Validate humidity range (0 to 100%)
        if humidity is None or humidity < 0 or humidity > 100:
            return False
        
        return True
    
    def calibrate(self) -> None:
        """DHT22 doesn't require calibration."""
        self.logger.info(f"Calibration not required for {self.name}")


class SensorManager:
    """Manages all sensors in the monitoring system."""
    
    def __init__(self) -> None:
        """Initialize sensor manager."""
        self.sensors: Dict[str, BaseSensor] = {}
        self.logger = logging.getLogger(f"{__name__}.SensorManager")
        
    def register_sensor(self, sensor: BaseSensor) -> None:
        """Register a sensor with the manager.
        
        Args:
            sensor: Sensor instance to register
        """
        if sensor.sensor_id in self.sensors:
            self.logger.warning(
                f"Sensor {sensor.sensor_id} already registered, replacing"
            )
        
        self.sensors[sensor.sensor_id] = sensor
        self.logger.info(f"Registered sensor: {sensor.name} ({sensor.sensor_id})")
    
    def unregister_sensor(self, sensor_id: str) -> None:
        """Unregister a sensor.
        
        Args:
            sensor_id: ID of sensor to unregister
        """
        if sensor_id in self.sensors:
            del self.sensors[sensor_id]
            self.logger.info(f"Unregistered sensor: {sensor_id}")
    
    def read_all(self) -> Dict[str, Optional[SensorReading]]:
        """Read all registered sensors.
        
        Returns:
            Dictionary of sensor IDs to readings
        """
        readings = {}
        for sensor_id, sensor in self.sensors.items():
            readings[sensor_id] = sensor.read_with_retry()
        return readings
    
    def get_sensor(self, sensor_id: str) -> Optional[BaseSensor]:
        """Get sensor by ID.
        
        Args:
            sensor_id: Sensor ID to retrieve
            
        Returns:
            Sensor instance or None if not found
        """
        return self.sensors.get(sensor_id)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all sensors.
        
        Returns:
            Dictionary of sensor statuses
        """
        return {
            sensor_id: sensor.get_status()
            for sensor_id, sensor in self.sensors.items()
        }
    
    def check_alerts(self) -> List[str]:
        """Check all sensors for alert conditions.
        
        Returns:
            List of sensor IDs that are in alert state
        """
        alerts = []
        
        for sensor_id, sensor in self.sensors.items():
            if isinstance(sensor, (SmokeSensor, FlameSensor)):
                if sensor.is_triggered():
                    alerts.append(sensor_id)
            elif isinstance(sensor, WaterSensor):
                reading = sensor.read_with_retry()
                if reading and reading.value:
                    alerts.append(sensor_id)
        
        return alerts