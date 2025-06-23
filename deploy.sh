#!/bin/bash

# Production deployment script for Masumi Kodosuni Connector
set -e

echo "🚀 Deploying Masumi Kodosuni Connector..."

# Configuration
APP_DIR="/opt/masumi-kodosuni-connector"
SERVICE_NAME="masumi-connector"
USER="masumi"

# Create application user
if ! id "$USER" &>/dev/null; then
    sudo useradd -r -s /bin/false -d "$APP_DIR" "$USER"
fi

# Create application directory
sudo mkdir -p "$APP_DIR"
sudo chown "$USER:$USER" "$APP_DIR"

# Copy files
sudo cp -r src/ "$APP_DIR/"
sudo cp requirements.txt "$APP_DIR/"
sudo cp .env.example "$APP_DIR/.env"
sudo chown -R "$USER:$USER" "$APP_DIR"

# Install Python 3.12 if not present
if ! command -v python3.12 &> /dev/null; then
    echo "Installing Python 3.12..."
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python3.12 python3.12-venv python3.12-dev
fi

# Create virtual environment and install dependencies
sudo -u "$USER" python3.12 -m venv "$APP_DIR/venv"
sudo -u "$USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# Create systemd service
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Masumi Kodosuni Connector
After=network.target

[Service]
Type=exec
User=$USER
WorkingDirectory=$APP_DIR
Environment=PYTHONPATH=$APP_DIR/src
ExecStart=$APP_DIR/venv/bin/python -m uvicorn masumi_kodosuni_connector.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "✅ Deployment complete!"
echo "📊 Service status: sudo systemctl status $SERVICE_NAME"
echo "📋 View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "🌐 Configure reverse proxy to point to http://localhost:8000"