#!/bin/bash
# Quick setup script for WebDL
# Installs dependencies and makes the script executable

echo "Setting up WebDL..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Make webdl.py executable
chmod +x webdl.py

echo ""
echo "Setup complete!"
echo ""
echo "Usage:"
echo "  python3 webdl.py example.com"
echo "  python3 webdl.py https://example.com --max-pages 200"
echo ""
echo "Downloaded sites are saved to: sites/domain/"
