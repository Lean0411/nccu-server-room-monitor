# NCCU Server Room Environmental Monitoring System

## System Overview

The NCCU Server Room Monitor is an enterprise-grade environmental monitoring system designed for 24/7 operation in the National Chengchi University (NCCU) server room facility. The system provides real-time monitoring of critical environmental parameters to ensure optimal operating conditions for server infrastructure.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Monitoring System                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Sensors    │  │    Camera    │  │    Alerts    │ │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤ │
│  │ • Smoke      │  │ • Pi Camera  │  │ • Email      │ │
│  │ • Flame      │  │ • ROI        │  │ • Cooldown   │ │
│  │ • Temp/Hum   │  │ • Buffer     │  │ • Threshold  │ │
│  │ • Water      │  │              │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Core Monitor Engine                  │  │
│  │         (Multi-threaded, Event-driven)           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Platform**: Raspberry Pi 4B
- **Language**: Python 3.9+
- **Framework**: Asyncio for concurrent operations
- **Sensors**: GPIO-based environmental sensors
- **Camera**: Pi Camera v2 with OpenCV processing
- **Alerts**: SMTP-based email notifications
- **Service**: systemd daemon for 24/7 operation

## Requirements

### Hardware Requirements

| Component | Specification | GPIO Pin |
|-----------|--------------|----------|
| Raspberry Pi | Model 4B, 2GB+ RAM | - |
| MQ-2 Smoke Sensor | 5V operation | GPIO 17 |
| Flame Sensor | Digital output | GPIO 27 |
| DHT22 Sensor | Temperature & Humidity | GPIO 4 |
| Water Level Sensor | Digital output | GPIO 22 |
| Pi Camera | v2, 8MP | CSI Port |
| Power Supply | 5V 3A | - |

### Software Requirements

- Raspbian OS (Bullseye or later)
- Python 3.9+
- systemd for service management
- Network connectivity for alerts

## Installation

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/nccu/server-room-monitor.git
cd server-room-monitor
```

2. **Run installation script**
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

3. **Configure environment**
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

4. **Start the service**
```bash
sudo systemctl start nccu-monitor
sudo systemctl enable nccu-monitor
```

### Manual Installation

```bash
# System dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev

# Python environment
python3 -m venv venv
source venv/bin/activate

# Install package
pip install -e .

# Configure
cp config/config.yaml.example config/config.yaml
nano config/config.yaml
```

## Project Structure

```
nccu-server-room-monitor/
├── src/                    # Source code
│   ├── core/              # Core monitoring modules
│   │   ├── sensors.py     # Sensor abstractions
│   │   ├── monitor.py     # Main monitoring engine
│   │   └── camera.py      # Camera management
│   ├── alerts/            # Alert system
│   │   └── alert_manager.py
│   ├── daemon/            # Service management
│   │   └── service.py
│   └── utils/             # Utilities
│       ├── config.py      # Configuration management
│       └── logger.py      # Logging system
├── tests/                 # Test suites
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── hardware/         # Hardware tests
├── config/               # Configuration files
│   └── config.yaml
├── scripts/              # Deployment scripts
│   ├── install.sh
│   └── deploy.sh
├── requirements/         # Dependencies
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── setup.py             # Package configuration
```

## Configuration

### Environment Variables

Create `.env` file with the following variables:

```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=monitor@nccu.edu.tw
SMTP_PASS=<app_password>

# Alert Recipients
ALERT_TO=admin@nccu.edu.tw,it-team@nccu.edu.tw

# System Configuration
LOG_LEVEL=INFO
MAX_MEMORY_MB=512
```

### Configuration File

Edit `config/config.yaml` for detailed settings:

```yaml
monitor:
  interval: 5.0           # Monitoring interval (seconds)
  max_memory_mb: 512.0    # Memory limit
  
sensors:
  smoke_threshold: 2      # Consecutive detections
  flame_threshold: 3      # Consecutive detections
  temp_threshold_high: 35.0  # Celsius
  
camera:
  resolution: 640x480
  buffer_size: 20
  capture_interval: 5.0
  
alerts:
  cooldown_minutes: 5
  max_retries: 3
```

## API Reference

### Sensor Interface

```python
from src.core.sensors import SensorManager

# Initialize sensor manager
manager = SensorManager(config)

# Read all sensors
readings = manager.read_all()

# Get specific sensor
smoke_sensor = manager.get_sensor('smoke')
reading = smoke_sensor.read()
```

### Alert System

```python
from src.alerts.alert_manager import AlertManager

# Send alert
alert_manager = AlertManager(config)
await alert_manager.send_alert(
    alert_type='fire',
    message='Fire detected in server room',
    level='critical',
    images=camera_images
)
```

## Operations

### Service Management

```bash
# Start service
sudo systemctl start nccu-monitor

# Stop service
sudo systemctl stop nccu-monitor

# Restart service
sudo systemctl restart nccu-monitor

# Check status
sudo systemctl status nccu-monitor

# View logs
sudo journalctl -u nccu-monitor -f
```

### Monitoring

```bash
# System status
python3 -m src.utils.system_status

# Performance metrics
python3 -m src.utils.performance_analysis

# Test sensors
python3 tests/hardware/check_all_sensors.py
```

### Maintenance

#### Log Rotation
- Maximum file size: 10MB
- Backup count: 5 files
- Auto-compression of old logs

#### Storage Management
- Auto-cleanup of files older than 7 days
- Image buffer limited to 20 frames
- Maximum storage usage: 10GB

## Performance Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Sensor Read Cycle | < 5s | 4.8s |
| Alert Delivery | < 30s | 15s |
| Memory Usage | < 512MB | 380MB |
| CPU Usage | < 50% | 35% |
| Image Processing | < 2s | 1.5s |
| Service Uptime | > 99.9% | 99.95% |

## Troubleshooting

### Common Issues

**Camera not detected**
```bash
sudo raspi-config  # Enable camera interface
sudo modprobe bcm2835-v4l2  # Load camera module
```

**GPIO permission denied**
```bash
sudo usermod -a -G gpio $USER
# Logout and login again
```

**Email sending fails**
- Verify SMTP credentials in `.env`
- Check network connectivity
- Ensure app-specific password is used for Gmail

**High memory usage**
```bash
# Check memory status
free -h

# Restart service to clear memory
sudo systemctl restart nccu-monitor
```

### Debug Mode

Enable debug logging:
```bash
# In .env file
LOG_LEVEL=DEBUG

# Or in config.yaml
logging:
  level: DEBUG
```

## Development

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Code formatting
black src/
flake8 src/
```

### Contributing Guidelines

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for all modules and classes
- Maintain test coverage above 80%

## Security Considerations

- Run service as non-root user
- Use environment variables for sensitive data
- Regular security updates
- Network isolation for critical systems
- Encrypted SMTP connections
- No logging of sensitive information

## License

Copyright (c) 2025 National Chengchi University. All rights reserved.

This software is proprietary and confidential. Unauthorized copying or distribution is prohibited.

## Support

**Technical Support**: NCCU IT Department  
**Email**: it-support@nccu.edu.tw  
**Phone**: (02) 2939-3091  
**Emergency**: 0958-242-580

---

*Version: 2.0.0*  
*Last Updated: 2025-09-02*  
*Status: Production*