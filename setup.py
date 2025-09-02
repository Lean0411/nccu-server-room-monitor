"""
Setup script for NCCU Server Room Monitor.

This script provides installation and packaging configuration
for the monitoring system.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    with open(readme_file, "r", encoding="utf-8") as f:
        long_description = f.read()

# Read requirements
def read_requirements(filename):
    """Read requirements from file."""
    req_file = Path(__file__).parent / "requirements" / filename
    if req_file.exists():
        with open(req_file, "r") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#") and not line.startswith("-r")
            ]
    return []

# Base requirements
install_requires = read_requirements("base.txt")

# Development requirements
extras_require = {
    "dev": read_requirements("dev.txt"),
    "prod": read_requirements("prod.txt"),
}

setup(
    name="nccu-server-room-monitor",
    version="2.0.0",
    author="NCCU IT Department",
    author_email="it@nccu.edu.tw",
    description="Professional server room environmental monitoring system for NCCU",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nccu/server-room-monitor",
    
    # Package configuration
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    package_dir={"": "."},
    include_package_data=True,
    
    # Dependencies
    install_requires=install_requires,
    extras_require=extras_require,
    
    # Python version requirement
    python_requires=">=3.9",
    
    # Entry points for command-line scripts
    entry_points={
        "console_scripts": [
            "nccu-monitor=src.core.monitor:main",
            "nccu-monitor-test=tests.system_test:main",
        ],
    },
    
    # Package data files
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md"],
        "config": ["*.yaml"],
    },
    
    # Data files to include
    data_files=[
        ("config", ["config/config.yaml"]),
        ("systemd", ["nccu-monitor.service"]),
        ("scripts", [
            "scripts/install.sh",
            "scripts/deploy.sh",
            "scripts/health_check.sh"
        ]),
    ],
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Framework :: AsyncIO",
    ],
    
    # Keywords for searchability
    keywords="monitoring raspberry-pi sensors server-room environmental nccu",
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/nccu/server-room-monitor/issues",
        "Source": "https://github.com/nccu/server-room-monitor",
        "Documentation": "https://github.com/nccu/server-room-monitor/wiki",
    },
    
    # Test configuration
    test_suite="tests",
    tests_require=[
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-asyncio>=0.21.0",
    ],
    
    # Zip safe flag
    zip_safe=False,
)