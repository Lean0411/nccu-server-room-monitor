"""
Exception hierarchy for NCCU Server Room Monitor.

This module defines custom exceptions used throughout the monitoring system
to provide clear error handling and debugging information.
"""

from typing import Any, Dict, Optional


class MonitorException(Exception):
    """Base exception for all monitoring system errors.
    
    This is the root exception class that all custom exceptions inherit from.
    It provides enhanced error information and logging capabilities.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize monitor exception.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
            details: Additional error details as dictionary
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "MONITOR_ERROR"
        self.details = details or {}
        self.cause = cause
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization.
        
        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }
        
    def __str__(self) -> str:
        """String representation of the exception."""
        if self.cause:
            return f"{self.error_code}: {self.message} (caused by: {self.cause})"
        return f"{self.error_code}: {self.message}"


class SensorException(MonitorException):
    """Exception related to sensor operations.
    
    Raised when sensor initialization, reading, or calibration fails.
    """
    
    def __init__(
        self,
        message: str,
        sensor_id: Optional[str] = None,
        sensor_type: Optional[str] = None,
        **kwargs
    ):
        """Initialize sensor exception.
        
        Args:
            message: Error message
            sensor_id: ID of the affected sensor
            sensor_type: Type of the affected sensor
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details.update({
            "sensor_id": sensor_id,
            "sensor_type": sensor_type
        })
        
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "SENSOR_ERROR"),
            details=details,
            **kwargs
        )


class SensorReadException(SensorException):
    """Exception when sensor reading fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SENSOR_READ_ERROR",
            **kwargs
        )


class SensorInitException(SensorException):
    """Exception when sensor initialization fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SENSOR_INIT_ERROR",
            **kwargs
        )


class SensorCalibrationException(SensorException):
    """Exception when sensor calibration fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SENSOR_CALIBRATION_ERROR",
            **kwargs
        )


class CameraException(MonitorException):
    """Exception related to camera operations.
    
    Raised when camera initialization, capture, or processing fails.
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Initialize camera exception.
        
        Args:
            message: Error message
            operation: Camera operation that failed
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CAMERA_ERROR"),
            details=details,
            **kwargs
        )


class CameraInitException(CameraException):
    """Exception when camera initialization fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CAMERA_INIT_ERROR",
            operation="initialization",
            **kwargs
        )


class CameraCaptureException(CameraException):
    """Exception when camera capture fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CAMERA_CAPTURE_ERROR",
            operation="capture",
            **kwargs
        )


class AlertException(MonitorException):
    """Exception related to alert system.
    
    Raised when alert creation, sending, or management fails.
    """
    
    def __init__(
        self,
        message: str,
        alert_type: Optional[str] = None,
        recipient: Optional[str] = None,
        **kwargs
    ):
        """Initialize alert exception.
        
        Args:
            message: Error message
            alert_type: Type of alert that failed
            recipient: Alert recipient
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details.update({
            "alert_type": alert_type,
            "recipient": recipient
        })
        
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "ALERT_ERROR"),
            details=details,
            **kwargs
        )


class EmailException(AlertException):
    """Exception when email sending fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="EMAIL_ERROR",
            **kwargs
        )


class AlertCooldownException(AlertException):
    """Exception when alert is blocked by cooldown."""
    
    def __init__(
        self,
        message: str,
        cooldown_remaining: Optional[float] = None,
        **kwargs
    ):
        """Initialize cooldown exception.
        
        Args:
            message: Error message
            cooldown_remaining: Seconds remaining in cooldown
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details["cooldown_remaining"] = cooldown_remaining
        
        super().__init__(
            message=message,
            error_code="ALERT_COOLDOWN",
            details=details,
            **kwargs
        )


class ConfigException(MonitorException):
    """Exception related to configuration.
    
    Raised when configuration loading, parsing, or validation fails.
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        """Initialize configuration exception.
        
        Args:
            message: Error message
            config_key: Configuration key that caused error
            config_file: Configuration file path
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details.update({
            "config_key": config_key,
            "config_file": config_file
        })
        
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "CONFIG_ERROR"),
            details=details,
            **kwargs
        )


class ConfigValidationException(ConfigException):
    """Exception when configuration validation fails."""
    
    def __init__(self, message: str, validation_errors: Optional[Dict] = None, **kwargs):
        details = kwargs.pop("details", {})
        details["validation_errors"] = validation_errors
        
        super().__init__(
            message=message,
            error_code="CONFIG_VALIDATION_ERROR",
            details=details,
            **kwargs
        )


class ConfigLoadException(ConfigException):
    """Exception when configuration loading fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIG_LOAD_ERROR",
            **kwargs
        )


class StorageException(MonitorException):
    """Exception related to storage operations.
    
    Raised when file operations, disk space, or data persistence fails.
    """
    
    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Initialize storage exception.
        
        Args:
            message: Error message
            path: File or directory path
            operation: Storage operation that failed
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details.update({
            "path": path,
            "operation": operation
        })
        
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "STORAGE_ERROR"),
            details=details,
            **kwargs
        )


class DiskSpaceException(StorageException):
    """Exception when disk space is insufficient."""
    
    def __init__(
        self,
        message: str,
        available_space: Optional[int] = None,
        required_space: Optional[int] = None,
        **kwargs
    ):
        """Initialize disk space exception.
        
        Args:
            message: Error message
            available_space: Available disk space in bytes
            required_space: Required disk space in bytes
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details.update({
            "available_space": available_space,
            "required_space": required_space
        })
        
        super().__init__(
            message=message,
            error_code="DISK_SPACE_ERROR",
            details=details,
            **kwargs
        )


class NetworkException(MonitorException):
    """Exception related to network operations.
    
    Raised when network connectivity or communication fails.
    """
    
    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ):
        """Initialize network exception.
        
        Args:
            message: Error message
            host: Remote host
            port: Remote port
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details.update({
            "host": host,
            "port": port
        })
        
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "NETWORK_ERROR"),
            details=details,
            **kwargs
        )


class ConnectionException(NetworkException):
    """Exception when network connection fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CONNECTION_ERROR",
            **kwargs
        )


class TimeoutException(NetworkException):
    """Exception when network operation times out."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        """Initialize timeout exception.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details=details,
            **kwargs
        )


class SystemException(MonitorException):
    """Exception related to system operations.
    
    Raised when system-level operations or resources fail.
    """
    
    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        **kwargs
    ):
        """Initialize system exception.
        
        Args:
            message: Error message
            resource: System resource that failed
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details["resource"] = resource
        
        super().__init__(
            message=message,
            error_code=kwargs.pop("error_code", "SYSTEM_ERROR"),
            details=details,
            **kwargs
        )


class ResourceException(SystemException):
    """Exception when system resource is unavailable."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="RESOURCE_ERROR",
            **kwargs
        )


class PermissionException(SystemException):
    """Exception when permission is denied."""
    
    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        **kwargs
    ):
        """Initialize permission exception.
        
        Args:
            message: Error message
            required_permission: Permission that was required
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.pop("details", {})
        details["required_permission"] = required_permission
        
        super().__init__(
            message=message,
            error_code="PERMISSION_ERROR",
            details=details,
            **kwargs
        )