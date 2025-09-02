#!/bin/bash

# NCCU Server Room Monitor - Installation Script
# This script installs and configures the monitoring system

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="nccu-monitor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
VENV_DIR="${PROJECT_DIR}/venv"

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
    fi
}

check_raspberrypi() {
    if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        print_warning "This doesn't appear to be a Raspberry Pi"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    sudo apt-get update
    sudo apt-get install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        build-essential \
        libatlas-base-dev \
        libjpeg-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libopenjp2-7 \
        libtiff5
}

enable_camera() {
    print_status "Enabling camera interface..."
    
    if ! grep -q "start_x=1" /boot/config.txt; then
        echo "start_x=1" | sudo tee -a /boot/config.txt
        echo "gpu_mem=128" | sudo tee -a /boot/config.txt
        print_warning "Camera enabled. Reboot required."
    else
        print_status "Camera already enabled"
    fi
}

create_virtualenv() {
    print_status "Creating Python virtual environment..."
    
    if [[ -d "$VENV_DIR" ]]; then
        print_warning "Virtual environment already exists"
    else
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate virtual environment
    source "${VENV_DIR}/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
}

install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    source "${VENV_DIR}/bin/activate"
    
    # Install production requirements
    pip install -r "${PROJECT_DIR}/requirements/prod.txt"
    
    # Install the package
    pip install -e "${PROJECT_DIR}"
}

create_directories() {
    print_status "Creating required directories..."
    
    mkdir -p "${PROJECT_DIR}/logs"
    mkdir -p "${PROJECT_DIR}/captures"
    mkdir -p "${PROJECT_DIR}/data"
    
    # Set permissions
    chmod 755 "${PROJECT_DIR}/logs"
    chmod 755 "${PROJECT_DIR}/captures"
    chmod 755 "${PROJECT_DIR}/data"
}

setup_environment() {
    print_status "Setting up environment..."
    
    if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
        cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
        print_warning "Please edit ${PROJECT_DIR}/.env with your configuration"
    else
        print_status "Environment file already exists"
    fi
}

install_service() {
    print_status "Installing systemd service..."
    
    # Create service file
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=NCCU Server Room Monitor
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin"
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/src/core/monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable service
    sudo systemctl enable "$SERVICE_NAME"
    
    print_status "Service installed successfully"
}

test_installation() {
    print_status "Testing installation..."
    
    source "${VENV_DIR}/bin/activate"
    
    # Test imports
    python -c "from src.core import sensors, monitor, camera" || print_error "Import test failed"
    
    # Test configuration
    python -c "from src.utils.config import Config; Config.load()" || print_error "Config test failed"
    
    print_status "Installation tests passed"
}

# Main installation flow
main() {
    echo "======================================"
    echo "NCCU Server Room Monitor Installation"
    echo "======================================"
    echo
    
    check_root
    check_raspberrypi
    
    print_status "Starting installation..."
    
    install_system_dependencies
    enable_camera
    create_virtualenv
    install_python_dependencies
    create_directories
    setup_environment
    install_service
    test_installation
    
    echo
    echo "======================================"
    print_status "Installation completed successfully!"
    echo "======================================"
    echo
    echo "Next steps:"
    echo "1. Edit configuration: nano ${PROJECT_DIR}/.env"
    echo "2. Test the system: sudo systemctl start ${SERVICE_NAME}"
    echo "3. Check status: sudo systemctl status ${SERVICE_NAME}"
    echo "4. View logs: sudo journalctl -u ${SERVICE_NAME} -f"
    echo
    
    read -p "Start the service now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start "$SERVICE_NAME"
        sudo systemctl status "$SERVICE_NAME"
    fi
}

# Run main function
main "$@"