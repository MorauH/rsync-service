#!/usr/bin/env python3

import json
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

def load_config():
    """Load configuration from JSON file"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {'sync_jobs': [], 'settings': {}}

class BackupStatusHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.serve_status_page()
        elif self.path == '/api/status':
            self.serve_api_status()
        elif self.path == '/api/logs':
            self.serve_api_logs()
        elif self.path.startswith('/logs/'):
            self.serve_log_file()
        else:
            self.send_error(404)
    
    def serve_status_page(self):
        """Serve the main status HTML page"""
        html = self.generate_status_html()
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_api_status(self):
        """Serve status data as JSON API"""
        try:
            status = self.load_status()
            config = load_config()
            
            response = {
                'status': status,
                'config': {
                    'jobs': config.get('sync_jobs', []),
                    'settings': config.get('settings', {})
                }
            }
            
            json_data = json.dumps(response, indent=2, default=str)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', str(len(json_data.encode())))
            self.end_headers()
            self.wfile.write(json_data.encode())
            
        except Exception as e:
            self.send_error(500, f"Error loading status: {e}")
    
    def serve_api_logs(self):
        """Serve available log files"""
        try:
            log_files = []
            if os.path.exists('logs'):
                for filename in sorted(os.listdir('logs'), reverse=True):
                    if filename.endswith('.log'):
                        filepath = os.path.join('logs', filename)
                        stat = os.stat(filepath)
                        log_files.append({
                            'filename': filename,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
            
            json_data = json.dumps(log_files, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', str(len(json_data.encode())))
            self.end_headers()
            self.wfile.write(json_data.encode())
            
        except Exception as e:
            self.send_error(500, f"Error loading logs: {e}")
    
    def serve_log_file(self):
        """Serve individual log file content"""
        try:
            # Parse filename from path
            filename = self.path.split('/')[-1]
            filepath = os.path.join('logs', filename)
            
            if not os.path.exists(filepath) or not filename.endswith('.log'):
                self.send_error(404)
                return
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Content-Length', str(len(content.encode())))
            self.end_headers()
            self.wfile.write(content.encode())
            
        except Exception as e:
            self.send_error(500, f"Error reading log file: {e}")
    
    def load_status(self):
        """Load status from JSON file"""
        try:
            with open('status.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'jobs': {}, 'last_run': None, 'total_runs': 0}
        except Exception:
            return {'jobs': {}, 'last_run': None, 'total_runs': 0}
    
    def format_datetime(self, iso_string):
        """Format ISO datetime string for display"""
        if not iso_string:
            return 'Never'
        try:
            dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return str(iso_string)
    
    def format_duration(self, seconds):
        """Format duration in seconds to human readable"""
        if not seconds:
            return '0s'
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def generate_status_html(self):
        """Generate the HTML status page"""
        status = self.load_status()
        config = load_config()
        
        title = config.get('settings', {}).get('web_interface', {}).get('title', 'NAS Backup Monitor')
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .summary-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        .jobs-container {{
            padding: 30px;
        }}
        .job-card {{
            border: 1px solid #e1e5e9;
            border-radius: 6px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .job-header {{
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e1e5e9;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .job-name {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }}
        .status-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .status-success {{
            background: #d4edda;
            color: #155724;
        }}
        .status-error {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-never {{
            background: #e2e3e5;
            color: #6c757d;
        }}
        .job-details {{
            padding: 20px;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        .detail-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .detail-label {{
            font-weight: 500;
            color: #666;
        }}
        .detail-value {{
            color: #333;
            font-family: monospace;
            font-size: 0.9em;
        }}
        .path {{
            word-break: break-all;
            max-width: 300px;
        }}
        .stats {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }}
        .stats h4 {{
            margin: 0 0 10px 0;
            color: #666;
        }}
        .refresh-btn {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 50px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-weight: bold;
        }}
        .refresh-btn:hover {{
            background: #5a67d8;
        }}
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                border-radius: 0;
            }}
            .summary {{
                grid-template-columns: 1fr;
                padding: 20px;
            }}
            .detail-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Real-time backup synchronization monitoring</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Last Run</h3>
                <div class="value">{self.format_datetime(status.get('last_run'))}</div>
            </div>
            <div class="summary-card">
                <h3>Total Runs</h3>
                <div class="value">{status.get('total_runs', 0)}</div>
            </div>
            <div class="summary-card">
                <h3>Active Jobs</h3>
                <div class="value">{len([j for j in config.get('sync_jobs', []) if j.get('enabled', True)])}</div>
            </div>
            <div class="summary-card">
                <h3>Success Rate</h3>
                <div class="value">{self.calculate_success_rate(status)}%</div>
            </div>
        </div>
        
        <div class="jobs-container">
            <h2>Sync Jobs</h2>
            {self.generate_jobs_html(config.get('sync_jobs', []), status.get('jobs', {}))}
        </div>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">Refresh</button>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""
        
        return html
    
    def calculate_success_rate(self, status):
        """Calculate overall success rate"""
        jobs = status.get('jobs', {})
        if not jobs:
            return 100
        
        successful = sum(1 for job in jobs.values() if job.get('success', False))
        total = len(jobs)
        
        return round((successful / total) * 100) if total > 0 else 100
    
    def generate_jobs_html(self, config_jobs, status_jobs):
        """Generate HTML for job cards"""
        html = ""
        
        for job in config_jobs:
            name = job['name']
            enabled = job.get('enabled', True)
            status_info = status_jobs.get(name, {})
            
            if not enabled:
                continue
            
            success = status_info.get('success')
            last_run = status_info.get('last_run')
            
            if success is None:
                status_class = "status-never"
                status_text = "Never Run"
            elif success:
                status_class = "status-success"
                status_text = "Success"
            else:
                status_class = "status-error"
                status_text = "Failed"
            
            stats = status_info.get('stats', {})
            
            html += f"""
            <div class="job-card">
                <div class="job-header">
                    <div class="job-name">{name}</div>
                    <div class="status-badge {status_class}">{status_text}</div>
                </div>
                <div class="job-details">
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">Source:</span>
                            <span class="detail-value path">{job['source']}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Destination:</span>
                            <span class="detail-value path">{job['destination']}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Last Run:</span>
                            <span class="detail-value">{self.format_datetime(last_run)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Duration:</span>
                            <span class="detail-value">{self.format_duration(status_info.get('duration'))}</span>
                        </div>
                    </div>
                    
                    {f'''
                    <div class="stats">
                        <h4>Last Sync Statistics</h4>
                        <div class="detail-grid">
                            {f'<div class="detail-item"><span class="detail-label">Total Files:</span><span class="detail-value">{stats.get("total_files", "N/A")}</span></div>' if stats.get("total_files") else ''}
                            {f'<div class="detail-item"><span class="detail-label">Created:</span><span class="detail-value">{stats.get("created_files", "N/A")}</span></div>' if stats.get("created_files") else ''}
                            {f'<div class="detail-item"><span class="detail-label">Deleted:</span><span class="detail-value">{stats.get("deleted_files", "N/A")}</span></div>' if stats.get("deleted_files") else ''}
                            {f'<div class="detail-item"><span class="detail-label">Transferred:</span><span class="detail-value">{stats.get("transferred_size", "N/A")}</span></div>' if stats.get("transferred_size") else ''}
                        </div>
                    </div>
                    ''' if stats else ''}
                </div>
            </div>
            """
        
        return html

def start_server(port=8080):
    """Start the web server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, BackupStatusHandler)
    print(f"Starting backup status server on port {port}")
    print(f"Visit http://localhost:{port} to view the status")
    httpd.serve_forever()

if __name__ == "__main__":
    
    config = load_config()
    port = config.get('settings', {}).get('web_interface', {}).get('port', 8080)

    start_server(port)