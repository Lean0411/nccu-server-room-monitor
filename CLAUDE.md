# NCCU Server Room Monitor - Development Guide

## Project Overview

The NCCU Server Room Monitor is a Raspberry Pi-based environmental monitoring system designed for 24/7 operation in the NCCU (National Chengchi University) server room. The system monitors critical environmental conditions including smoke, fire, temperature, humidity, and water leaks, providing real-time alerts via email.

## Architecture

### Core Components

```
src/
├── core/           # Core monitoring logic
├── alerts/         # Alert and notification system
├── utils/          # Utility functions and helpers
└── daemon/         # Background service management
```

### Technology Stack

- **Hardware**: Raspberry Pi 4B
- **Language**: Python 3.9+
- **Sensors**: MQ-2 (smoke), Flame sensor, DHT22 (temp/humidity), Water sensor
- **Camera**: Pi Camera v2
- **Communication**: SMTP for email alerts
- **Service**: systemd for daemon management

## Development Standards

### Code Style

1. **PEP 8 Compliance**: All Python code must follow PEP 8 standards
2. **Type Hints**: Use type hints for all function signatures
3. **Docstrings**: Google-style docstrings for all classes and functions
4. **Line Length**: Maximum 88 characters (Black formatter standard)
5. **Imports**: Group imports (standard library, third-party, local)

### Example Code Style

```python
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

from picamera import PiCamera
import board

from src.core.exceptions import SensorException


@dataclass
class SensorReading:
    """Represents a single sensor reading.
    
    Attributes:
        timestamp: Unix timestamp of the reading
        value: The sensor value
        sensor_type: Type of sensor (smoke, flame, etc.)
        unit: Optional unit of measurement
    """
    timestamp: float
    value: Any
    sensor_type: str
    unit: Optional[str] = None
    

class BaseSensor:
    """Abstract base class for all sensors.
    
    Args:
        pin: GPIO pin number or board pin object
        name: Human-readable sensor name
    """
    
    def __init__(self, pin: Any, name: str) -> None:
        self.pin = pin
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    def read(self) -> SensorReading:
        """Read current sensor value.
        
        Returns:
            SensorReading object with current value
            
        Raises:
            SensorException: If sensor read fails
        """
        raise NotImplementedError
```

## Testing Strategy

### Test Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for system components
└── hardware/       # Hardware-specific tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/

# Run with verbose output
pytest -v
```

### Test Requirements

1. Minimum 80% code coverage
2. All critical paths must have tests
3. Mock hardware dependencies in unit tests
4. Use fixtures for common test data

## Configuration Management

### Environment Variables

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

### Configuration Hierarchy

1. Environment variables (highest priority)
2. Configuration files (`config/config.yaml`)
3. Default values in code (lowest priority)

### Sensitive Data

- Never commit `.env` files
- Use environment variables for secrets
- Store credentials securely
- Rotate API keys regularly

## Error Handling

### Exception Hierarchy

```python
MonitorException          # Base exception
├── SensorException       # Sensor-related errors
├── AlertException        # Alert system errors
├── ConfigException       # Configuration errors
└── CameraException       # Camera-related errors
```

### Error Recovery

1. Implement exponential backoff for retries
2. Log all errors with context
3. Graceful degradation when possible
4. Alert on critical failures

## Performance Optimization

### Memory Management

1. Use generators for large datasets
2. Implement circular buffers for image storage
3. Regular garbage collection
4. Monitor memory usage

### CPU Optimization

1. Use threading for I/O operations
2. Implement queue-based processing
3. Optimize image processing
4. Profile performance bottlenecks

## Deployment

### System Requirements

- Raspberry Pi 4B (2GB+ RAM)
- Raspbian OS (latest)
- Python 3.9+
- systemd for service management

### Installation Steps

```bash
# Clone repository
git clone https://github.com/nccu/server-room-monitor.git
cd server-room-monitor

# Install dependencies
pip install -r requirements/prod.txt

# Configure environment
cp .env.example .env
nano .env  # Edit configuration

# Install service
sudo ./scripts/install.sh

# Start monitoring
sudo systemctl start nccu-monitor
```

### Service Management

```bash
# Check status
sudo systemctl status nccu-monitor

# View logs
sudo journalctl -u nccu-monitor -f

# Restart service
sudo systemctl restart nccu-monitor

# Stop service
sudo systemctl stop nccu-monitor
```

## Monitoring & Logging

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures requiring immediate attention

### Log Rotation

- Maximum file size: 10MB
- Keep 5 backup files
- Automatic compression of old logs
- Daily rotation for active logs

### Metrics

Key metrics to monitor:
- Sensor reading frequency
- Alert response time
- Memory usage
- CPU utilization
- Network latency
- Email delivery success rate

## Security Considerations

### Access Control

1. Run service as non-root user
2. Restrict file permissions
3. Use principle of least privilege
4. Regular security updates

### Network Security

1. Use TLS for SMTP connections
2. Validate all external inputs
3. Implement rate limiting
4. Monitor for suspicious activity

## Troubleshooting

### Common Issues

1. **Camera not detected**
   ```bash
   sudo raspi-config  # Enable camera interface
   ```

2. **GPIO permission denied**
   ```bash
   sudo usermod -a -G gpio $USER
   ```

3. **Email sending fails**
   - Check SMTP credentials
   - Verify network connectivity
   - Check firewall settings

4. **High memory usage**
   - Check image buffer size
   - Review log file sizes
   - Monitor for memory leaks

### Debug Mode

Enable debug logging:

```python
# In config/config.yaml
logging:
  level: DEBUG
  verbose: true
```

## Development Workflow

### Branch Strategy

- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Emergency fixes

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types: feat, fix, docs, style, refactor, test, chore

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass and coverage adequate
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling implemented
- [ ] Logging appropriate

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements/dev.txt
      - name: Run tests
        run: pytest --cov=src
      - name: Lint code
        run: |
          black --check src/
          flake8 src/
          mypy src/
```

## Performance Benchmarks

### Target Metrics

- Sensor read cycle: < 5 seconds
- Alert delivery: < 30 seconds
- Memory usage: < 500MB
- CPU usage: < 50% average
- Image processing: < 2 seconds
- Startup time: < 10 seconds

## API Documentation

### Sensor Interface

```python
class ISensor(Protocol):
    def read(self) -> SensorReading: ...
    def calibrate(self) -> None: ...
    def get_status(self) -> Dict[str, Any]: ...
```

### Alert Interface

```python
class IAlert(Protocol):
    def send(self, message: str, attachments: List[str]) -> bool: ...
    def check_cooldown(self, alert_type: str) -> bool: ...
```

## Resources

### Documentation

- [Raspberry Pi GPIO](https://www.raspberrypi.org/documentation/usage/gpio/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [systemd Services](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

### Tools

- **Black**: Code formatter
- **Flake8**: Linter
- **Mypy**: Type checker
- **Pytest**: Testing framework
- **Coverage**: Code coverage
- **Pre-commit**: Git hooks

## Contact & Support

- **Project Lead**: NCCU IT Department
- **Repository**: [GitHub](https://github.com/nccu/server-room-monitor)
- **Issues**: [Issue Tracker](https://github.com/nccu/server-room-monitor/issues)

## License

Copyright (c) 2025 National Chengchi University. All rights reserved.

---

*Last Updated: 2025-09-02*
*Version: 2.0.0*