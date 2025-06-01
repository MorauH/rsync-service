#!/usr/bin/env python3

import json
import subprocess
import datetime
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

class BackupSync:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.status_file = 'status.json'
        self.log_dir = 'logs'
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup logging
        log_file = os.path.join(self.log_dir, f"sync_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.load_config()
        self.load_status()
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            logging.info(f"Configuration loaded from {self.config_file}")
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    
    def load_status(self):
        """Load or initialize status file"""
        try:
            with open(self.status_file, 'r') as f:
                self.status = json.load(f)
        except FileNotFoundError:
            self.status = {
                'jobs': {},
                'last_run': None,
                'total_runs': 0
            }
            self.save_status()
        except Exception as e:
            logging.error(f"Failed to load status: {e}")
            self.status = {'jobs': {}, 'last_run': None, 'total_runs': 0}
    
    def save_status(self):
        """Save status to JSON file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Failed to save status: {e}")
    
    def run_rsync(self, job):
        """Execute rsync for a single job"""
        name = job['name']
        source = job['source']
        destination = job['destination']
        
        # Build rsync command
        cmd = ['rsync']
        
        # Add SSH key if specified
        ssh_key = self.config.get('settings', {}).get('ssh_key')
        if ssh_key:
            cmd.extend(['-e', f'ssh -i {ssh_key} -o StrictHostKeyChecking=no'])
        else:
            cmd.extend(['-e', 'ssh -o StrictHostKeyChecking=no'])
        
        # Add rsync options
        rsync_options = self.config.get('settings', {}).get('rsync_options', '-avz --delete --stats')
        cmd.extend(rsync_options.split())
        
        # Add excludes
        for exclude in job.get('exclude', []):
            cmd.extend(['--exclude', exclude])
        
        # Add source and destination
        cmd.extend([source, destination])
        
        logging.info(f"Starting sync for {name}: {' '.join(cmd)}")
        
        start_time = datetime.datetime.now()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Parse rsync stats from output
            stats = self.parse_rsync_stats(result.stdout)
            
            job_status = {
                'name': name,
                'source': source,
                'destination': destination,
                'last_run': start_time.isoformat(),
                'duration': duration,
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stats': stats,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            self.status['jobs'][name] = job_status
            
            if result.returncode == 0:
                logging.info(f"✓ {name} completed successfully in {duration:.1f}s")
            else:
                logging.error(f"✗ {name} failed with return code {result.returncode}")
                logging.error(f"Error output: {result.stderr}")
                
            return job_status
            
        except subprocess.TimeoutExpired:
            logging.error(f"✗ {name} timed out after 1 hour")
            job_status = {
                'name': name,
                'source': source,
                'destination': destination,
                'last_run': start_time.isoformat(),
                'duration': 3600,
                'success': False,
                'return_code': -1,
                'error': 'Timeout after 1 hour',
                'stats': {},
                'stdout': '',
                'stderr': 'Process timed out'
            }
            self.status['jobs'][name] = job_status
            return job_status
            
        except Exception as e:
            logging.error(f"✗ {name} failed with exception: {e}")
            job_status = {
                'name': name,
                'source': source,
                'destination': destination,
                'last_run': start_time.isoformat(),
                'duration': 0,
                'success': False,
                'return_code': -1,
                'error': str(e),
                'stats': {},
                'stdout': '',
                'stderr': str(e)
            }
            self.status['jobs'][name] = job_status
            return job_status
    
    def parse_rsync_stats(self, output):
        """Parse rsync statistics from output"""
        stats = {}
        lines = output.split('\n')
        
        for line in lines:
            if 'Number of files:' in line:
                stats['total_files'] = line.split(':')[1].strip()
            elif 'Number of created files:' in line:
                stats['created_files'] = line.split(':')[1].strip()
            elif 'Number of deleted files:' in line:
                stats['deleted_files'] = line.split(':')[1].strip()
            elif 'Total transferred file size:' in line:
                stats['transferred_size'] = line.split(':')[1].strip()
            elif 'Total file size:' in line:
                stats['total_size'] = line.split(':')[1].strip()
        
        return stats
    
    def send_notification(self, failed_jobs):
        """Send email notification for failed jobs"""
        if not failed_jobs:
            return
            
        try:
            notification_config = self.config.get('settings', {}).get('notification', {})
            if not notification_config.get('email'):
                logging.warning("No email configuration found, skipping notification")
                return
            
            msg = MIMEMultipart()
            msg['From'] = notification_config['smtp_user']
            msg['To'] = notification_config['email']
            msg['Subject'] = f"Backup Sync Failed - {len(failed_jobs)} job(s)"
            
            body = f"The following backup jobs failed:\n\n"
            for job in failed_jobs:
                body += f"• {job['name']}\n"
                body += f"  Source: {job['source']}\n"
                body += f"  Error: {job.get('error', 'Unknown error')}\n\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(notification_config['smtp_server'], notification_config['smtp_port'])
            server.starttls()
            server.login(notification_config['smtp_user'], notification_config['smtp_pass'])
            server.send_message(msg)
            server.quit()
            
            logging.info("Notification email sent successfully")
            
        except Exception as e:
            logging.error(f"Failed to send notification email: {e}")
    
    def run_all_jobs(self):
        """Run all enabled sync jobs"""
        logging.info("Starting backup sync run")
        
        start_time = datetime.datetime.now()
        failed_jobs = []
        successful_jobs = []
        
        for job in self.config['sync_jobs']:
            if not job.get('enabled', True):
                logging.info(f"Skipping disabled job: {job['name']}")
                continue
                
            job_result = self.run_rsync(job)
            
            if job_result['success']:
                successful_jobs.append(job_result)
            else:
                failed_jobs.append(job_result)
        
        # Update overall status
        self.status['last_run'] = start_time.isoformat()
        self.status['total_runs'] = self.status.get('total_runs', 0) + 1
        self.status['last_summary'] = {
            'successful': len(successful_jobs),
            'failed': len(failed_jobs),
            'total': len(successful_jobs) + len(failed_jobs)
        }
        
        self.save_status()
        
        # Send notifications for failures
        if failed_jobs:
            self.send_notification(failed_jobs)
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logging.info(f"Backup sync completed in {duration:.1f}s")
        logging.info(f"Results: {len(successful_jobs)} successful, {len(failed_jobs)} failed")
        
        return len(failed_jobs) == 0

if __name__ == "__main__":
    sync = BackupSync()
    success = sync.run_all_jobs()
    sys.exit(0 if success else 1)