# Newsletter Analyst - Deployment Guide

This guide provides complete instructions for deploying the Newsletter Analyst application in different environments.

## Table of Contents

1. [Local Deployment (Recommended for Personal Use)](#local-deployment)
2. [Docker Deployment](#docker-deployment)
3. [Cloud VM Deployment (AWS, GCP, DigitalOcean)](#cloud-vm-deployment)
4. [Streamlit Cloud Deployment (Dashboard Only)](#streamlit-cloud-deployment)
5. [Security Best Practices](#security-best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Local Deployment

**Best for:** Personal use on your own computer

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git
- Google Cloud account with Gmail API enabled
- Anthropic API key

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/newsletteranalyst.git
cd newsletteranalyst
```

### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Gmail API Credentials

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable the Gmail API

2. **Create OAuth 2.0 Credentials:**
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Download the JSON file

3. **Configure credentials:**
   ```bash
   # Create config directory
   mkdir -p config

   # Copy your downloaded credentials
   cp ~/Downloads/client_secret_*.json config/credentials.json
   ```

### Step 5: Set Up Anthropic API Key

1. Get your API key from [Anthropic Console](https://console.anthropic.com/)

2. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your keys:
   ```bash
   GMAIL_CREDENTIALS_PATH=config/credentials.json
   ANTHROPIC_API_KEY=your_actual_api_key_here
   ```

### Step 6: Create Data Directory

```bash
mkdir -p data
```

### Step 7: First-Time Gmail Authentication

```bash
# Test Gmail connection (this will open browser for OAuth)
python -m src.gmail_client
```

Follow the browser prompts to authorize the application. A `token.json` file will be created in the `config/` directory.

### Step 8: Verify Installation

```bash
# Check CLI is working
python src/main.py --help

# Check database stats (should show empty database)
python src/main.py stats
```

### Step 9: Fetch Your First Emails

```bash
# Fetch emails from a specific label
python src/main.py fetch-emails --label "Newsletter" --max-results 50

# Or search by query
python src/main.py fetch-emails --query "from:newsletter@example.com" --max-results 50
```

### Step 10: Analyze Emails

```bash
# Analyze all unanalyzed emails
python src/main.py analyze-emails

# Or analyze specific batch size with custom delay
python src/main.py analyze-emails --batch-size 10 --delay 2.0
```

### Step 11: Launch Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open automatically at `http://localhost:8501`

---

## Docker Deployment

**Best for:** Consistent environment, easy deployment across machines

### Step 1: Create Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data config output

# Expose Streamlit port
EXPOSE 8501

# Default command (can be overridden)
CMD ["streamlit", "run", "dashboard.py", "--server.address", "0.0.0.0"]
```

### Step 2: Create docker-compose.yml

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  newsletter-analyst:
    build: .
    container_name: newsletter_analyst
    ports:
      - "8501:8501"
    volumes:
      # Mount data directory for persistence
      - ./data:/app/data
      # Mount config for credentials
      - ./config:/app/config
      # Mount output directory
      - ./output:/app/output
    env_file:
      - .env
    restart: unless-stopped
    command: streamlit run dashboard.py --server.address 0.0.0.0
```

### Step 3: Create .dockerignore

Create `.dockerignore`:

```
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.git/
.gitignore
.env
data/*.db
config/token.json
config/credentials.json
*.md
```

### Step 4: Build and Run

```bash
# Build the image
docker-compose build

# Set up credentials (one-time)
# Run container interactively first to authenticate Gmail
docker-compose run --rm newsletter-analyst python -m src.gmail_client

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Step 5: Run CLI Commands in Docker

```bash
# Fetch emails
docker-compose exec newsletter-analyst python src/main.py fetch-emails --label "Newsletter" --max-results 50

# Analyze emails
docker-compose exec newsletter-analyst python src/main.py analyze-emails

# Generate report
docker-compose exec newsletter-analyst python src/main.py generate-report
```

---

## Cloud VM Deployment

**Best for:** Remote access, always-on service, team access

### Supported Platforms

- AWS EC2
- Google Cloud Compute Engine
- DigitalOcean Droplets
- Azure Virtual Machines
- Linode

### Step 1: Provision VM

**Minimum Requirements:**
- OS: Ubuntu 22.04 LTS
- RAM: 2GB
- Storage: 20GB
- vCPU: 1 core

**AWS EC2 Example:**
```bash
# Launch t3.small instance with Ubuntu 22.04
# Configure security group:
# - Allow port 22 (SSH)
# - Allow port 8501 (Streamlit) from your IP only
```

**DigitalOcean Example:**
```bash
# Create $12/month droplet with Ubuntu 22.04
# Add your SSH key during creation
```

### Step 2: Connect to VM

```bash
# SSH into your server
ssh ubuntu@YOUR_VM_IP

# Or with key file
ssh -i ~/.ssh/your_key.pem ubuntu@YOUR_VM_IP
```

### Step 3: Install Dependencies on VM

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and essentials
sudo apt-get install -y python3.10 python3.10-venv python3-pip git

# Install nginx (for reverse proxy, optional)
sudo apt-get install -y nginx
```

### Step 4: Clone and Set Up Application

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/newsletteranalyst.git
sudo chown -R ubuntu:ubuntu newsletteranalyst
cd newsletteranalyst

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data config output
```

### Step 5: Configure Environment

```bash
# Create .env file
nano .env
```

Add your configuration:
```
GMAIL_CREDENTIALS_PATH=config/credentials.json
ANTHROPIC_API_KEY=your_api_key_here
```

### Step 6: Upload Credentials

From your local machine:
```bash
# Upload Gmail credentials
scp config/credentials.json ubuntu@YOUR_VM_IP:/opt/newsletteranalyst/config/

# If you already have token.json
scp config/token.json ubuntu@YOUR_VM_IP:/opt/newsletteranalyst/config/
```

### Step 7: Set Up Systemd Service

Create `/etc/systemd/system/newsletter-dashboard.service`:

```bash
sudo nano /etc/systemd/system/newsletter-dashboard.service
```

Add:
```ini
[Unit]
Description=Newsletter Analyst Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/newsletteranalyst
Environment="PATH=/opt/newsletteranalyst/venv/bin"
ExecStart=/opt/newsletteranalyst/venv/bin/streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8501
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable newsletter-dashboard
sudo systemctl start newsletter-dashboard
sudo systemctl status newsletter-dashboard
```

### Step 8: Set Up Nginx Reverse Proxy (Optional but Recommended)

```bash
sudo nano /etc/nginx/sites-available/newsletter-analyst
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # or use IP address

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/newsletter-analyst /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 9: Set Up SSL with Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

### Step 10: Set Up Cron Jobs for Automation

```bash
# Edit crontab
crontab -e
```

Add automated tasks:
```cron
# Fetch new emails daily at 2 AM
0 2 * * * cd /opt/newsletteranalyst && /opt/newsletteranalyst/venv/bin/python src/main.py fetch-emails --label "Newsletter" --max-results 100 >> /opt/newsletteranalyst/logs/fetch.log 2>&1

# Analyze unanalyzed emails daily at 3 AM
0 3 * * * cd /opt/newsletteranalyst && /opt/newsletteranalyst/venv/bin/python src/main.py analyze-emails >> /opt/newsletteranalyst/logs/analyze.log 2>&1

# Generate weekly report every Monday at 9 AM
0 9 * * 1 cd /opt/newsletteranalyst && /opt/newsletteranalyst/venv/bin/python src/main.py generate-report --output /opt/newsletteranalyst/output/weekly_report.txt
```

Create logs directory:
```bash
mkdir -p /opt/newsletteranalyst/logs
```

---

## Streamlit Cloud Deployment

**Best for:** Quick dashboard-only deployment (note: limited functionality)

⚠️ **Important:** Streamlit Cloud is suitable only for the dashboard. Email fetching and analysis should be run separately.

### Step 1: Prepare Repository

1. Push your code to GitHub
2. Ensure `.streamlit/config.toml` exists:

Create `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[server]
headless = true
port = 8501
```

### Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select repository: `YOUR_USERNAME/newsletteranalyst`
5. Main file path: `dashboard.py`
6. Click "Deploy"

### Step 3: Configure Secrets

In Streamlit Cloud dashboard:
1. Go to app settings
2. Click "Secrets"
3. Add your `.env` contents

**Note:** You cannot run email fetching or analysis on Streamlit Cloud. Use it only for viewing data from a pre-populated database.

### Alternative: Use Streamlit Cloud + Cloud VM

1. Run fetching/analysis on Cloud VM
2. Sync database to cloud storage (S3, GCS)
3. Configure Streamlit Cloud app to read from cloud storage

---

## Security Best Practices

### 1. Protect Credentials

```bash
# Set proper permissions
chmod 600 config/credentials.json
chmod 600 config/token.json
chmod 600 .env

# Never commit these files
echo "config/credentials.json" >> .gitignore
echo "config/token.json" >> .gitignore
echo ".env" >> .gitignore
```

### 2. Firewall Configuration (Cloud VM)

```bash
# Ubuntu UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 3. Regular Backups

```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backup/newsletter-analyst-$DATE.tar.gz \
    /opt/newsletteranalyst/data/ \
    /opt/newsletteranalyst/config/ \
    /opt/newsletteranalyst/output/

# Keep only last 30 days
find /backup -name "newsletter-analyst-*.tar.gz" -mtime +30 -delete
```

Add to crontab:
```cron
# Daily backup at midnight
0 0 * * * /opt/newsletteranalyst/backup.sh
```

### 4. Environment-Specific Settings

Create separate env files:
- `.env.development`
- `.env.production`

### 5. API Rate Limiting

Monitor API usage:
```bash
# Check Anthropic usage
python -c "from src.llm_analyzer import EmailAnalyzer; a = EmailAnalyzer(); print(a.get_usage_stats())"
```

### 6. Database Access Control

```bash
# Set database file permissions
chmod 640 data/newsletter_emails.db
```

---

## Troubleshooting

### Issue: Gmail Authentication Fails

**Solution:**
```bash
# Remove old token
rm config/token.json

# Re-authenticate
python -m src.gmail_client
```

### Issue: Streamlit Port Already in Use

**Solution:**
```bash
# Find process using port 8501
sudo lsof -i :8501

# Kill process
kill -9 PID

# Or use different port
streamlit run dashboard.py --server.port 8502
```

### Issue: Database Locked Error

**Solution:**
```bash
# Check for orphaned connections
ps aux | grep python

# Kill orphaned processes
kill -9 PID

# Restart application
```

### Issue: Out of Memory on Small VM

**Solution:**
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Issue: Anthropic API Rate Limits

**Solution:**
```bash
# Increase delay between requests
python src/main.py analyze-emails --delay 3.0

# Process smaller batches
python src/main.py analyze-emails --batch-size 5
```

### Issue: Database Migration Needed

**Solution:**
```bash
# Backup current database
cp data/newsletter_emails.db data/newsletter_emails.db.backup

# Run migration script (if provided)
python scripts/migrate_db.py
```

---

## Monitoring and Maintenance

### Log Monitoring

```bash
# View application logs
tail -f /opt/newsletteranalyst/logs/*.log

# View systemd service logs
sudo journalctl -u newsletter-dashboard -f
```

### Health Check Script

Create `healthcheck.sh`:
```bash
#!/bin/bash

# Check if dashboard is responding
if curl -s http://localhost:8501 > /dev/null; then
    echo "✓ Dashboard is running"
else
    echo "✗ Dashboard is down"
    sudo systemctl restart newsletter-dashboard
fi

# Check database size
DB_SIZE=$(du -h data/newsletter_emails.db | cut -f1)
echo "Database size: $DB_SIZE"

# Check disk space
df -h /opt/newsletteranalyst
```

### Updating the Application

```bash
# Pull latest changes
cd /opt/newsletteranalyst
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart newsletter-dashboard
```

---

## Quick Reference

### Common Commands

```bash
# Fetch emails
python src/main.py fetch-emails --label "Newsletter" --max-results 100

# Analyze emails
python src/main.py analyze-emails

# Generate report
python src/main.py generate-report

# Export analysis to CSV
python src/main.py export-analysis --output output/analysis.csv

# Launch dashboard
streamlit run dashboard.py

# View database stats
python src/main.py stats

# Search emails
python src/main.py search --keyword "welcome" --limit 10
```

### Service Management (Cloud VM)

```bash
# Start service
sudo systemctl start newsletter-dashboard

# Stop service
sudo systemctl stop newsletter-dashboard

# Restart service
sudo systemctl restart newsletter-dashboard

# View status
sudo systemctl status newsletter-dashboard

# View logs
sudo journalctl -u newsletter-dashboard -n 100 --no-pager
```

---

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review application logs
3. Check GitHub issues
4. Create new issue with:
   - Deployment method
   - Error messages
   - Steps to reproduce

---

## Next Steps

After deployment:
1. ✅ Set up automated email fetching (cron jobs)
2. ✅ Configure regular backups
3. ✅ Set up monitoring/alerts
4. ✅ Review security settings
5. ✅ Test disaster recovery
6. ✅ Document custom configurations

Happy analyzing! 🎉
