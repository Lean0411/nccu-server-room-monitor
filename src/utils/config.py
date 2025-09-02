"""
Configuration management module for NCCU Server Room Monitor.

Handles loading, validation, and management of system configuration
from multiple sources (environment variables, YAML files, defaults).
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

import yaml
from pydantic import BaseSettings, Field, validator
from pydantic.types import SecretStr
from dotenv import load_dotenv

import board


# Load environment variables
load_dotenv()


class SMTPConfig(BaseSettings):
    """SMTP email configuration."""
    
    host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    port: int = Field(default=587, env="SMTP_PORT")
    user: str = Field(..., env="SMTP_USER")
    password: SecretStr = Field(..., env="SMTP_PASS")
    use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    timeout: int = Field(default=30, env="SMTP_TIMEOUT")
    
    class Config:
        env_prefix = "SMTP_"
        case_sensitive = False


class AlertConfig(BaseSettings):
    """Alert system configuration."""
    
    recipients: List[str] = Field(default_factory=list, env="ALERT_TO")
    cooldown_minutes: int = Field(default=5, env="ALERT_COOLDOWN")
    max_retries: int = Field(default=3, env="ALERT_MAX_RETRIES")
    include_images: bool = Field(default=True, env="ALERT_INCLUDE_IMAGES")
    max_image_size_mb: float = Field(default=10.0, env="ALERT_MAX_IMAGE_SIZE")
    
    @validator("recipients", pre=True)
    def parse_recipients(cls, v):
        """Parse recipients from comma-separated string."""
        if isinstance(v, str):
            return [email.strip() for email in v.split(",") if email.strip()]
        return v
    
    class Config:
        env_prefix = "ALERT_"
        case_sensitive = False


class SensorConfig(BaseSettings):
    """Sensor configuration."""
    
    # Smoke sensor
    smoke_enabled: bool = Field(default=True, env="SENSOR_SMOKE_ENABLED")
    smoke_pin: Any = Field(default=board.D17, env="SENSOR_SMOKE_PIN")
    smoke_threshold: int = Field(default=2, env="SENSOR_SMOKE_THRESHOLD")
    
    # Flame sensor
    flame_enabled: bool = Field(default=True, env="SENSOR_FLAME_ENABLED")
    flame_pin: Any = Field(default=board.D27, env="SENSOR_FLAME_PIN")
    flame_threshold: int = Field(default=3, env="SENSOR_FLAME_THRESHOLD")
    
    # Water sensor
    water_enabled: bool = Field(default=True, env="SENSOR_WATER_ENABLED")
    water_pin: Any = Field(default=board.D22, env="SENSOR_WATER_PIN")
    
    # DHT22 sensor
    dht22_enabled: bool = Field(default=True, env="SENSOR_DHT22_ENABLED")
    dht22_pin: Any = Field(default=board.D4, env="SENSOR_DHT22_PIN")
    temp_threshold_high: float = Field(default=35.0, env="SENSOR_TEMP_HIGH")
    temp_threshold_low: float = Field(default=10.0, env="SENSOR_TEMP_LOW")
    humidity_threshold_high: float = Field(default=80.0, env="SENSOR_HUMIDITY_HIGH")
    humidity_threshold_low: float = Field(default=20.0, env="SENSOR_HUMIDITY_LOW")
    
    @validator("smoke_pin", "flame_pin", "water_pin", "dht22_pin", pre=True)
    def parse_gpio_pin(cls, v):
        """Parse GPIO pin from string or int."""
        if isinstance(v, str):
            # Handle string like "D17" or "17"
            pin_str = v.upper().replace("GPIO", "").replace("D", "")
            try:
                pin_num = int(pin_str)
                return getattr(board, f"D{pin_num}")
            except (ValueError, AttributeError):
                raise ValueError(f"Invalid GPIO pin: {v}")
        elif isinstance(v, int):
            return getattr(board, f"D{v}")
        return v
    
    class Config:
        env_prefix = "SENSOR_"
        case_sensitive = False
        arbitrary_types_allowed = True


class CameraConfig(BaseSettings):
    """Camera configuration."""
    
    enabled: bool = Field(default=True, env="CAMERA_ENABLED")
    resolution: tuple = Field(default=(640, 480), env="CAMERA_RESOLUTION")
    framerate: int = Field(default=30, env="CAMERA_FRAMERATE")
    rotation: int = Field(default=0, env="CAMERA_ROTATION")
    capture_interval: float = Field(default=5.0, env="CAMERA_CAPTURE_INTERVAL")
    buffer_size: int = Field(default=20, env="CAMERA_BUFFER_SIZE")
    
    # Region of Interest (ROI)
    use_roi: bool = Field(default=False, env="CAMERA_USE_ROI")
    roi_x: int = Field(default=100, env="CAMERA_ROI_X")
    roi_y: int = Field(default=80, env="CAMERA_ROI_Y")
    roi_width: int = Field(default=200, env="CAMERA_ROI_WIDTH")
    roi_height: int = Field(default=150, env="CAMERA_ROI_HEIGHT")
    
    @validator("resolution", pre=True)
    def parse_resolution(cls, v):
        """Parse resolution from string."""
        if isinstance(v, str):
            parts = v.split("x")
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
        return v
    
    class Config:
        env_prefix = "CAMERA_"
        case_sensitive = False


class MonitorConfig(BaseSettings):
    """Monitor system configuration."""
    
    interval: float = Field(default=5.0, env="MONITOR_INTERVAL")
    max_memory_mb: float = Field(default=512.0, env="MONITOR_MAX_MEMORY")
    max_cpu_percent: float = Field(default=80.0, env="MONITOR_MAX_CPU")
    restart_on_error: bool = Field(default=True, env="MONITOR_RESTART_ON_ERROR")
    max_restarts: int = Field(default=10, env="MONITOR_MAX_RESTARTS")
    
    class Config:
        env_prefix = "MONITOR_"
        case_sensitive = False


class StorageConfig(BaseSettings):
    """Storage configuration."""
    
    data_dir: Path = Field(default=Path("data"), env="STORAGE_DATA_DIR")
    captures_dir: Path = Field(default=Path("captures"), env="STORAGE_CAPTURES_DIR")
    logs_dir: Path = Field(default=Path("logs"), env="STORAGE_LOGS_DIR")
    max_storage_gb: float = Field(default=10.0, env="STORAGE_MAX_SIZE")
    cleanup_days: int = Field(default=7, env="STORAGE_CLEANUP_DAYS")
    
    @validator("data_dir", "captures_dir", "logs_dir", pre=True)
    def parse_path(cls, v):
        """Parse path from string."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    def ensure_directories(self):
        """Create storage directories if they don't exist."""
        for dir_path in [self.data_dir, self.captures_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_prefix = "STORAGE_"
        case_sensitive = False


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    max_file_size_mb: int = Field(default=10, env="LOG_MAX_SIZE")
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    console_output: bool = Field(default=True, env="LOG_CONSOLE")
    file_output: bool = Field(default=True, env="LOG_FILE")
    
    @validator("level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper
    
    class Config:
        env_prefix = "LOG_"
        case_sensitive = False


class Config(BaseSettings):
    """Main configuration class that aggregates all config sections."""
    
    # Sub-configurations
    smtp: SMTPConfig = Field(default_factory=SMTPConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    sensors: SensorConfig = Field(default_factory=SensorConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # General settings
    environment: str = Field(default="production", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "Config":
        """Load configuration from file and environment.
        
        Args:
            config_file: Optional path to YAML config file
            
        Returns:
            Config instance with loaded settings
        """
        # Start with environment variables and defaults
        config_dict = {}
        
        # Load from YAML file if provided
        if config_file and config_file.exists():
            with open(config_file, "r") as f:
                yaml_config = yaml.safe_load(f) or {}
                config_dict.update(yaml_config)
        
        # Create config instance (env vars override file values)
        config = cls(**config_dict)
        
        # Ensure storage directories exist
        config.storage.ensure_directories()
        
        return config
    
    def save(self, config_file: Path):
        """Save configuration to YAML file.
        
        Args:
            config_file: Path to save the configuration
        """
        config_dict = self.dict(exclude_unset=False)
        
        # Convert SecretStr to string for saving
        if "smtp" in config_dict and "password" in config_dict["smtp"]:
            config_dict["smtp"]["password"] = "***REDACTED***"
        
        # Convert Path objects to strings
        def convert_paths(d):
            for key, value in d.items():
                if isinstance(value, Path):
                    d[key] = str(value)
                elif isinstance(value, dict):
                    convert_paths(value)
            return d
        
        config_dict = convert_paths(config_dict)
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    def validate_config(self) -> List[str]:
        """Validate configuration settings.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check SMTP settings if alerts are enabled
        if self.alerts.recipients:
            if not self.smtp.user:
                errors.append("SMTP user is required for email alerts")
            if not self.smtp.password:
                errors.append("SMTP password is required for email alerts")
        
        # Check sensor pins don't conflict
        used_pins = []
        if self.sensors.smoke_enabled:
            used_pins.append(("smoke", self.sensors.smoke_pin))
        if self.sensors.flame_enabled:
            used_pins.append(("flame", self.sensors.flame_pin))
        if self.sensors.water_enabled:
            used_pins.append(("water", self.sensors.water_pin))
        if self.sensors.dht22_enabled:
            used_pins.append(("dht22", self.sensors.dht22_pin))
        
        # Check for duplicate pins
        pin_values = [pin for _, pin in used_pins]
        if len(pin_values) != len(set(pin_values)):
            errors.append("Duplicate GPIO pins detected in sensor configuration")
        
        # Validate thresholds
        if self.sensors.temp_threshold_low >= self.sensors.temp_threshold_high:
            errors.append("Temperature low threshold must be less than high threshold")
        if self.sensors.humidity_threshold_low >= self.sensors.humidity_threshold_high:
            errors.append("Humidity low threshold must be less than high threshold")
        
        # Validate storage limits
        if self.storage.max_storage_gb <= 0:
            errors.append("Maximum storage must be greater than 0")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return self.dict(exclude={"smtp": {"password"}})
    
    def get_summary(self) -> str:
        """Get configuration summary as string.
        
        Returns:
            Human-readable configuration summary
        """
        summary = []
        summary.append(f"Environment: {self.environment}")
        summary.append(f"Debug Mode: {self.debug}")
        summary.append(f"Monitor Interval: {self.monitor.interval}s")
        
        # Sensor summary
        enabled_sensors = []
        if self.sensors.smoke_enabled:
            enabled_sensors.append("Smoke")
        if self.sensors.flame_enabled:
            enabled_sensors.append("Flame")
        if self.sensors.water_enabled:
            enabled_sensors.append("Water")
        if self.sensors.dht22_enabled:
            enabled_sensors.append("DHT22")
        summary.append(f"Enabled Sensors: {', '.join(enabled_sensors)}")
        
        # Camera summary
        if self.camera.enabled:
            summary.append(f"Camera: {self.camera.resolution[0]}x{self.camera.resolution[1]} @ {self.camera.framerate}fps")
        
        # Alert summary
        if self.alerts.recipients:
            summary.append(f"Alert Recipients: {len(self.alerts.recipients)}")
            summary.append(f"Alert Cooldown: {self.alerts.cooldown_minutes} minutes")
        
        return "\n".join(summary)


# Singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance.
    
    Returns:
        Global Config instance
    """
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config(config_file: Optional[Path] = None):
    """Reload configuration from file and environment.
    
    Args:
        config_file: Optional path to YAML config file
    """
    global _config
    _config = Config.load(config_file)
    logging.info("Configuration reloaded")