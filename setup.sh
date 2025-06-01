#!/bin/bash

# NAS Backup Sync Setup Script
# This script sets up the backup sync system with systemd timer

set -e

INSTALL_DIR="/opt/nas-backup-sync"
SERVICE_USER="backup-sync"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up NAS Backup Sync System${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
apt-get update
apt-get install -y python3 python3-pip rsync openssh-client

# Create system user
echo -e "${YELLOW}Creating system user: ${SERVICE_USER}${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --home-dir "$INSTALL_DIR" --shell /bin/bash "$SERVICE_USER"
else
    echo "User $SERVICE_USER already exists"
fi

# Create installation directory
echo -e "${YELLOW}Creating installation directory: ${INSTALL_DIR}${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"/logs

# Copy files to installation directory
echo -e "${YELLOW}Copying application files...${NC}"
cp sync.py "$INSTALL_DIR/"
cp web_server.py "$INSTALL_DIR/"
cp config.json "$INSTALL_DIR/"

# Make scripts executable
chmod +x "$INSTALL_DIR"/sync.py
chmod +x "$INSTALL_DIR"/web_server.py

# Set ownership
chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"

# Generate SSH key for backup user if it doesn't exist
SSH_KEY_PATH="$INSTALL_DIR/.ssh/backup_key"
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${YELLOW}Generating SSH key for backup authentication...${NC}"
    sudo -u "$SERVICE_USER" mkdir -p "$INSTALL_DIR/.ssh"
    sudo -u "$SERVICE_USER" ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N "" -C "nas-backup-sync"
    chmod 600 "$SSH_KEY_PATH"
    chmod 644 "$SSH_KEY_PATH.pub"
    
    echo -e "${GREEN}SSH public key generated at: ${SSH_KEY_PATH}.pub${NC}"
    echo -e "${YELLOW}You need to copy this public key to your backup server:${NC}"
    echo "ssh-copy-id -i $SSH_KEY_PATH.pub backup-user@your-backup-server"
    echo "Or manually add the key to ~/.ssh/authorized_keys on the backup server"
    echo ""
    cat "$SSH_KEY_PATH.pub"
    echo ""
fi

# Create systemd service file
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > /etc/systemd/system/nas-backup-sync.service << EOF
[Unit]
Description=NAS Backup Sync
After=network.target

[Service]
Type=oneshot
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/sync.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer file
echo -e "${YELLOW}Creating systemd timer...${NC}"
cat > /etc/systemd/system/nas-backup-sync.timer << EOF
[Unit]
Description=Run NAS Backup Sync every hour
Requires=nas-backup-sync.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Create web server service file
echo -e "${YELLOW}Creating web server service...${NC}"
cat > /etc/systemd/system/nas-backup-web.service << EOF
[Unit]
Description=NAS Backup Web Interface
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/web_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
echo -e "${YELLOW}Enabling systemd services...${NC}"
systemctl daemon-reload
systemctl enable nas-backup-sync.timer
systemctl enable nas-backup-web.service

# Start web server
systemctl start nas-backup-web.service

echo -e "${GREEN}Setup completed successfully!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit the configuration file: $INSTALL_DIR/config.json"
echo "2. Copy the SSH public key to your backup server:"
echo "   ssh-copy-id -i $SSH_KEY_PATH.pub backup-user@your-backup-server"
echo "3. Test the sync manually:"
echo "   sudo systemctl start nas-backup-sync.service"
echo "4. Start the timer:"
echo "   sudo systemctl start nas-backup-sync.timer"
echo "5. View the web interface at: http://localhost:8080"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "View sync status:    systemctl status nas-backup-sync.service"
echo "View timer status:   systemctl status nas-backup-sync.timer"
echo "View web status:     systemctl status nas-backup-web.service"
echo "View logs:           journalctl -u nas-backup-sync.service -f"
echo "Manual sync:         sudo systemctl start nas-backup-sync.service"
echo "Stop timer:          sudo systemctl stop nas-backup-sync.timer"
echo "Start timer:         sudo systemctl start nas-backup-sync.timer"