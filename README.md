# NAS Backup Sync System

A comprehensive backup synchronization system with web monitoring interface for Linux NAS servers.

## Features

- **Automated rsync-based backups** to remote servers via SSH
- **Web interface** for monitoring backup status and history
- **Email notifications** on backup failures
- **Configurable sync jobs** with individual settings
- **Detailed logging** and statistics
- **SystemD timer integration** for automated scheduling
- **Docker support** for containerized deployment

## Quick Start

### Option 1: SystemD Installation (Recommended)

1. **Download all files** to a directory on your NAS server
2. **Run the setup script** as root:
```bash
sudo chmod +x setup.sh
sudo ./setup.sh
```

3. **Configure your sync jobs** by editing `/opt/nas-backup-sync/config.json`

4. **Set up SSH key authentication** to your backup server:
```bash
# Copy the generated public key to your backup server
ssh-copy-id -i /opt/nas-backup-sync/.ssh/backup_key.pub backup-user@192.168.1.100
```

5. **Start the services**:
```bash
# Test manual sync first
sudo systemctl start nas-backup-sync.service

# Start the automatic timer
sudo systemctl start nas-backup-sync.timer

# Check status
sudo systemctl status nas-backup-sync.timer
```

6. **Access the web interface** at `http://your-nas-ip:8080`

### Option 2: Docker Installation

1. **Create SSH key directory**:
```bash
mkdir ssh
ssh-keygen -t rsa -b 4096 -f ssh/backup_key -N ""
ssh-copy-id -i ssh/backup_key.pub backup-user@192.168.1.100
```

2. **Edit docker-compose.yml** to mount your NAS shares

3. **Start the containers**:
```bash
docker-compose up -d
```

## Configuration

Edit `config.json` to configure your backup jobs:

```json
{
  "sync_jobs": [
    {
      "name": "Documents Share",
      "source": "/mnt/nas/documents/",
      "destination": "backup-user@192.168.1.100:/backup/documents/",
      "enabled": true,
      "exclude": ["*.tmp", "*.log"]
    }
  ],
  "settings": {
    "rsync_options": "-avz --delete --stats",
    "ssh_key": "/opt/nas-backup-sync/.ssh/backup_key",
    "notification": {
      "email": "your@email.com",
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "your@email.com",
      "smtp_pass": "your-app-password"
    }
  }
}
```

### Configuration Options

#### Sync Jobs
- **name**: Display name for the backup job
- **source**: Source directory path (with trailing slash)  
- **destination**: SSH destination `user@host:/path/`
- **enabled**: Whether this job should run
- **exclude**: Array of patterns to exclude from sync

#### Settings
- **rsync_options**: Command line options for rsync
- **ssh_key**: Path to SSH private key for authentication
- **notification**: Email settings for failure notifications

## SSH Setup for Remote Backup

Since your backup target doesn't have SMB shares, you'll use SSH:

1. **On your backup server**, create a backup user:
```bash
sudo useradd -m backup-user
sudo mkdir /home/backup-user/.ssh
sudo chmod 700 /home/backup-user/.ssh
```

2. **Copy the public key** from your NAS to the backup server:
```bash
# From NAS server
ssh-copy-id -i /opt/nas-backup-sync/.ssh/backup_key.pub backup-user@192.168.1.100
```

3. **Test the connection**:
```bash
ssh -i /opt/nas-backup-sync/.ssh/backup_key backup-user@192.168.1.100
```

## Usage

### SystemD Commands

```bash
# Manual sync
sudo systemctl start nas-backup-sync.service

# View sync status  
sudo systemctl status nas-backup-sync.service

# View logs
sudo journalctl -u nas-backup-sync.service -f

# Timer management
sudo systemctl start nas-backup-sync.timer    # Start automatic syncing
sudo systemctl stop nas-backup-sync.timer     # Stop automatic syncing
sudo systemctl status nas-backup-sync.timer   # Check timer status

# Web interface
sudo systemctl status nas-backup-web.service  # Check web server
```

### Docker Commands

```bash
# View logs
docker-compose logs nas-backup-sync
docker-compose logs nas-backup-web

# Manual sync
docker-compose exec nas-backup-sync python3 /app/sync.py

# Restart services
docker-compose restart
```

## Web Interface

The web interface provides:

- **Dashboard overview** with success rates and last run times
- **Individual job status** with detailed statistics  
- **Real-time logs** and error information
- **Auto-refresh** every 30 seconds
- **Mobile-responsive** design

Access at: `http://your-nas-ip:8080`

## File Structure

```
/opt/nas-backup-sync/
├── sync.py           # Main sync script
├── web_server.py     # Web interface server  
├── config.json       # Configuration file
├── status.json       # Runtime status (auto-generated)
├── logs/            # Log files directory
│   └── sync_YYYYMMDD.log
└── .ssh/            # SSH keys directory
    ├── backup_key
    └── backup_key.pub
```

## Monitoring & Troubleshooting

### Check Sync Status
- Web interface: `http://your-nas-ip:8080`
- Status file: `/opt/nas-backup-sync/status.json`
- Logs: `/opt/nas-backup-sync/logs/`

### Common Issues

**SSH Connection Failed:**
- Verify SSH key is copied to backup server
- Check SSH key permissions (600 for private key)
- Test manual SSH connection

**Permission Denied:**
- Check source directory permissions
- Verify backup user has write access on destination

**Sync Fails Silently:**
- Check logs in `/opt/nas-backup-sync/logs/`
- Run manual sync to see detailed output

## Email Notifications

Configure SMTP settings in `config.json` to receive failure notifications:

```json
"notification": {
  "email": "admin@yourdomain.com",
  "smtp_server": "smtp.gmail.com", 
  "smtp_port": 587,
  "smtp_user": "notifications@yourdomain.com",
  "smtp_pass": "your-app-password"
}
```

For Gmail, use an App Password instead of your regular password.

## Recovery

To restore from backup:

```bash
# Restore specific directory
rsync -avz backup-user@192.168.1.100:/backup/documents/ /mnt/nas/documents/

# Restore everything  
rsync -avz backup-user@192.168.1.100:/backup/ /mnt/nas/
```

The backup is an exact mirror, so standard rsync commands work for recovery.

## Security Notes

- SSH keys are stored with restricted permissions (600)
- Web interface runs on localhost by default
- No authentication on web interface - restrict network access
- Email passwords stored in plain text - use app passwords
- Consider firewall rules for the web interface port
