#!/usr/bin/env python3
"""
Test module for AHT Temperature and Humidity sensor.

This module provides both manual testing capabilities and pytest-compatible
test functions for the AHT sensor implementation.
"""

import time
import sys
import board
import pytest
from typing import Optional
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, '/home/lean/nccu-server-room-monitor')
from src.core.sensors import AHTSensor, SensorStatus, SensorType


class TestAHTSensor:
    """Test suite for AHT sensor."""
    
    @pytest.fixture
    def mock_i2c(self):
        """Mock I2C interface."""
        with patch('board.I2C') as mock:
            yield mock
    
    @pytest.fixture
    def mock_aht(self):
        """Mock AHTx0 sensor."""
        with patch('src.core.sensors.AHTx0') as mock:
            # Setup mock sensor with temperature and humidity properties
            mock_sensor = Mock()
            mock_sensor.temperature = 25.5
            mock_sensor.relative_humidity = 65.0
            mock.return_value = mock_sensor
            yield mock
    
    def test_sensor_initialization(self, mock_i2c, mock_aht):
        """Test sensor initializes correctly."""
        sensor = AHTSensor()
        
        assert sensor.sensor_id == "AHT"
        assert sensor.name == "AHT Sensor"
        assert sensor.sensor_type == SensorType.TEMPERATURE
        assert sensor.status == SensorStatus.OK
        mock_i2c.assert_called_once()
    
    def test_sensor_initialization_with_custom_params(self, mock_aht):
        """Test sensor initialization with custom parameters."""
        mock_i2c_custom = Mock()
        sensor = AHTSensor(
            sensor_id="custom_aht",
            name="Custom AHT Sensor",
            pin=mock_i2c_custom
        )
        
        assert sensor.sensor_id == "custom_aht"
        assert sensor.name == "Custom AHT Sensor"
        assert sensor.i2c == mock_i2c_custom
    
    def test_temperature_reading(self, mock_i2c, mock_aht):
        """Test temperature reading."""
        sensor = AHTSensor()
        temp = sensor.read_temperature()
        
        assert temp == 25.5
        assert sensor.status == SensorStatus.OK
    
    def test_humidity_reading(self, mock_i2c, mock_aht):
        """Test humidity reading."""
        sensor = AHTSensor()
        humidity = sensor.read_humidity()
        
        assert humidity == 65.0
        assert sensor.status == SensorStatus.OK
    
    def test_combined_reading(self, mock_i2c, mock_aht):
        """Test combined temperature and humidity reading."""
        sensor = AHTSensor()
        reading = sensor.read()
        
        assert reading.sensor_id == "AHT"
        assert reading.sensor_type == SensorType.TEMPERATURE
        assert reading.value["temperature"] == 25.5
        assert reading.value["humidity"] == 65.0
        assert reading.unit == "°C/%"
    
    def test_i2c_error_handling_temperature(self, mock_i2c, mock_aht):
        """Test I2C error handling for temperature reading."""
        sensor = AHTSensor()
        
        # Simulate I2C error
        sensor.aht.temperature = Mock(side_effect=OSError("I2C bus error"))
        temp = sensor.read_temperature()
        
        assert temp is None
        assert sensor.status == SensorStatus.ERROR
        assert sensor.error_count > 0
    
    def test_i2c_error_handling_humidity(self, mock_i2c, mock_aht):
        """Test I2C error handling for humidity reading."""
        sensor = AHTSensor()
        
        # Simulate I2C error
        sensor.aht.relative_humidity = Mock(side_effect=RuntimeError("I2C communication failed"))
        humidity = sensor.read_humidity()
        
        assert humidity is None
        assert sensor.status == SensorStatus.ERROR
        assert sensor.error_count > 0
    
    def test_validation_valid_reading(self, mock_i2c, mock_aht):
        """Test validation of valid sensor reading."""
        sensor = AHTSensor()
        reading = sensor.read()
        
        assert sensor.validate_reading(reading) is True
    
    def test_validation_invalid_temperature_low(self, mock_i2c, mock_aht):
        """Test validation rejects temperature below range."""
        sensor = AHTSensor()
        sensor.aht.temperature = -50.0  # Below -40°C minimum
        reading = sensor.read()
        
        assert sensor.validate_reading(reading) is False
    
    def test_validation_invalid_temperature_high(self, mock_i2c, mock_aht):
        """Test validation rejects temperature above range."""
        sensor = AHTSensor()
        sensor.aht.temperature = 90.0  # Above 85°C maximum
        reading = sensor.read()
        
        assert sensor.validate_reading(reading) is False
    
    def test_validation_invalid_humidity(self, mock_i2c, mock_aht):
        """Test validation rejects invalid humidity."""
        sensor = AHTSensor()
        sensor.aht.relative_humidity = 105.0  # Above 100% maximum
        reading = sensor.read()
        
        assert sensor.validate_reading(reading) is False
    
    def test_resource_cleanup(self, mock_i2c, mock_aht):
        """Test I2C resource cleanup."""
        sensor = AHTSensor()
        mock_i2c_instance = sensor.i2c
        
        sensor.close()
        
        # Verify deinit was called on I2C
        mock_i2c_instance.deinit.assert_called_once()
        assert sensor.i2c is None
    
    def test_destructor_cleanup(self, mock_i2c, mock_aht):
        """Test automatic cleanup in destructor."""
        sensor = AHTSensor()
        mock_i2c_instance = sensor.i2c
        
        # Simulate deletion
        sensor.__del__()
        
        # Verify cleanup was attempted
        mock_i2c_instance.deinit.assert_called_once()


def manual_sensor_test():
    """
    Manual test function for real hardware testing.
    Run this when connected to actual AHT sensor hardware.
    """
    print("開始測試：AHT 溫濕度感測器（Ctrl+C 結束）")
    print("=" * 40)
    
    try:
        # Initialize sensor with real I2C
        sensor = AHTSensor()
        print(f"感測器初始化成功")
        print(f"  ID: {sensor.sensor_id}")
        print(f"  名稱: {sensor.name}")
        print(f"  狀態: {sensor.status.value}")
        print()
        
        # Continuous monitoring
        print("開始監測...")
        while True:
            try:
                temperature = sensor.read_temperature()
                humidity = sensor.read_humidity()
                
                if temperature is not None and humidity is not None:
                    print(f"\r溫度: {temperature:0.1f}°C | 濕度: {humidity:0.1f}% | 狀態: {sensor.status.value}", end="")
                else:
                    print(f"\r讀取錯誤 | 狀態: {sensor.status.value}", end="")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"\n讀取錯誤: {e}")
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("\n\n測試結束")
    except Exception as e:
        print(f"初始化錯誤: {e}")
    finally:
        # Cleanup
        if 'sensor' in locals():
            sensor.close()
            print("資源已清理")


if __name__ == "__main__":
    # Check if running in pytest or manual mode
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        # Run manual hardware test
        manual_sensor_test()
    else:
        # Run pytest
        print("Running pytest tests...")
        print("Use '--manual' flag to run manual hardware test")
        pytest.main([__file__, "-v"])