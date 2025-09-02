"""
Logging module for NCCU Server Room Monitor.

Provides structured logging with rotation, performance tracking,
and multiple output formats.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json
from datetime import datetime

import structlog
from pythonjsonlogger import jsonlogger


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class ContextFilter(logging.Filter):
    """Add context information to log records."""
    
    def __init__(self, context: Dict[str, Any]):
        """Initialize context filter.
        
        Args:
            context: Context dictionary to add to records
        """
        super().__init__()
        self.context = context
        
    def filter(self, record):
        """Add context to record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self, logger: logging.Logger):
        """Initialize performance logger.
        
        Args:
            logger: Base logger instance
        """
        self.logger = logger
        self.metrics: Dict[str, Any] = {}
        
    def log_metric(self, name: str, value: float, unit: str = ""):
        """Log a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            unit: Optional unit
        """
        self.metrics[name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.debug(f"Performance metric - {name}: {value}{unit}")
        
    def log_timing(self, operation: str, duration: float):
        """Log operation timing.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        self.log_metric(f"{operation}_duration", duration, "s")
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.copy()


def setup_logging(
    config: Optional[Any] = None,
    log_dir: Optional[Path] = None,
    console: bool = True,
    file: bool = True,
    json_format: bool = False
) -> logging.Logger:
    """Setup logging configuration.
    
    Args:
        config: Optional configuration object
        log_dir: Directory for log files
        console: Enable console output
        file: Enable file output
        json_format: Use JSON format for logs
        
    Returns:
        Configured root logger
    """
    # Get configuration
    if config:
        log_level = config.logging.level
        log_format = config.logging.format
        max_size = config.logging.max_file_size_mb * 1024 * 1024
        backup_count = config.logging.backup_count
    else:
        log_level = "INFO"
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        max_size = 10 * 1024 * 1024
        backup_count = 5
    
    # Set log directory
    if not log_dir:
        log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        
        if json_format:
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:
            formatter = ColoredFormatter(log_format)
        
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if file:
        log_file = log_dir / "monitor.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level))
        
        if json_format:
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:
            formatter = logging.Formatter(log_format)
        
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Error file handler (always enabled)
    error_file = log_dir / "error.log"
    error_handler = RotatingFileHandler(
        error_file,
        maxBytes=max_size,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(error_handler)
    
    return root_logger


def setup_structured_logging(
    config: Optional[Any] = None,
    log_dir: Optional[Path] = None
) -> structlog.BoundLogger:
    """Setup structured logging with structlog.
    
    Args:
        config: Optional configuration object
        log_dir: Directory for log files
        
    Returns:
        Configured structlog logger
    """
    # Setup standard logging first
    setup_logging(config, log_dir, json_format=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


class LoggerManager:
    """Centralized logger management."""
    
    _instance = None
    _loggers: Dict[str, logging.Logger] = {}
    _performance_loggers: Dict[str, PerformanceLogger] = {}
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]
    
    def get_performance_logger(self, name: str) -> PerformanceLogger:
        """Get or create a performance logger.
        
        Args:
            name: Logger name
            
        Returns:
            PerformanceLogger instance
        """
        if name not in self._performance_loggers:
            logger = self.get_logger(f"{name}.performance")
            self._performance_loggers[name] = PerformanceLogger(logger)
        return self._performance_loggers[name]
    
    def add_context(self, context: Dict[str, Any]):
        """Add context to all loggers.
        
        Args:
            context: Context dictionary
        """
        context_filter = ContextFilter(context)
        for logger in self._loggers.values():
            logger.addFilter(context_filter)
    
    def set_level(self, level: str):
        """Set level for all loggers.
        
        Args:
            level: Log level
        """
        log_level = getattr(logging, level.upper())
        for logger in self._loggers.values():
            logger.setLevel(log_level)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics from all performance loggers.
        
        Returns:
            Dictionary of all metrics
        """
        return {
            name: logger.get_metrics()
            for name, logger in self._performance_loggers.items()
        }


# Convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return LoggerManager().get_logger(name)


def get_performance_logger(name: str) -> PerformanceLogger:
    """Get a performance logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        PerformanceLogger instance
    """
    return LoggerManager().get_performance_logger(name)


def log_exception(logger: logging.Logger, exception: Exception, context: Optional[Dict] = None):
    """Log an exception with context.
    
    Args:
        logger: Logger instance
        exception: Exception to log
        context: Optional context dictionary
    """
    exc_info = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "context": context or {}
    }
    
    logger.error(
        f"Exception occurred: {exception}",
        exc_info=True,
        extra=exc_info
    )


def create_audit_logger(log_dir: Optional[Path] = None) -> logging.Logger:
    """Create an audit logger for security events.
    
    Args:
        log_dir: Directory for audit logs
        
    Returns:
        Audit logger instance
    """
    if not log_dir:
        log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.handlers.clear()
    
    # Audit file handler with daily rotation
    audit_file = log_dir / "audit.log"
    handler = TimedRotatingFileHandler(
        audit_file,
        when="midnight",
        interval=1,
        backupCount=30
    )
    
    # JSON format for audit logs
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    audit_logger.addHandler(handler)
    
    return audit_logger


def log_audit_event(event_type: str, details: Dict[str, Any], user: Optional[str] = None):
    """Log an audit event.
    
    Args:
        event_type: Type of audit event
        details: Event details
        user: Optional user identifier
    """
    audit_logger = create_audit_logger()
    
    audit_entry = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "user": user or "system",
        "details": details
    }
    
    audit_logger.info(f"Audit event: {event_type}", extra=audit_entry)