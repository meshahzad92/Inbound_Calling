# 🐳 Docker Deployment Guide

This guide will help you deploy the Faith Agency AI Calling System using Docker with a single command.

## 🚀 Quick Start

### Option 1: One-Command Deployment
```bash
sudo docker-compose up -d
```

### Option 2: Automated Deployment Script
```bash
./deploy.sh
```

## 📋 Prerequisites

1. **Docker & Docker Compose** installed on your system
2. **Environment Variables** properly configured in `.env` file
3. **Google API Credentials** (optional for basic functionality)

## 🔧 What the Docker Setup Does

The Docker configuration automatically:

1. ✅ Creates Python 3.12 virtual environment
2. ✅ Installs all dependencies from `requirements.txt`
3. ✅ Sets up the complete application structure
4. ✅ Exposes the service on port 8000
5. ✅ Provides health checks and auto-restart
6. ✅ Maintains persistent data (CSV files, credentials)

## 📁 Docker Files Structure

```
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
├── .dockerignore           # Build optimization
└── deploy.sh              # Automated deployment script
```

## 🐳 Docker Commands

### Basic Operations
```bash
# Start the service
sudo docker-compose up -d

# Stop the service
sudo docker-compose down

# Restart the service
sudo docker-compose restart

# View logs
sudo docker-compose logs -f

# Check status
sudo docker-compose ps
```

### Development Commands
```bash
# Rebuild and start
sudo docker-compose up -d --build

# Access container shell
sudo docker-compose exec faith-agency-ai bash

# View real-time logs
sudo docker-compose logs -f faith-agency-ai
```

## 📊 Service Information

- **Container Name**: `faith-agency-calling-system`
- **Port**: `8000`
- **Health Check**: `http://localhost:8000/health`
- **API Endpoint**: `http://localhost:8000/api/incoming`
- **Auto-restart**: Enabled unless manually stopped

## 🔐 Credentials Setup

After deployment, add your credentials:

### Google Sheets API
```bash
# Place credentials in the main directory
cp your-credentials.json credentials.json

# For sheets automation
cp your-credentials.json sheets_automation/credentials.json
```

### Gmail API
```bash
# For email automation
cp your-gmail-credentials.json email_automation/credentials.json
```

## 🌐 Production Deployment

### With Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### With SSL (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## 🔍 Monitoring & Logs

### Container Health
```bash
# Check container health
docker inspect faith-agency-calling-system | grep Health -A 10

# View health check logs
docker-compose logs | grep health
```

### Application Logs
```bash
# Real-time logs
sudo docker-compose logs -f

# Last 100 lines
sudo docker-compose logs --tail=100

# Specific service logs
sudo docker-compose logs faith-agency-ai
```

## 🛠️ Troubleshooting

### Container Won't Start
```bash
# Check build logs
sudo docker-compose up --build

# View detailed logs
sudo docker-compose logs faith-agency-ai
```

### Port Already in Use
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x deploy.sh
```

### Environment Variables
```bash
# Verify .env file
cat .env

# Check container environment
docker-compose exec faith-agency-ai env
```

## 🔄 Updates & Maintenance

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
sudo docker-compose up -d --build
```

### Backup Data
```bash
# Backup Progress.csv
cp Progress.csv Progress_backup_$(date +%Y%m%d).csv

# Backup credentials
tar -czf credentials_backup_$(date +%Y%m%d).tar.gz \
    credentials.json \
    email_automation/ \
    sheets_automation/
```

## ⚡ Performance Optimization

### Resource Limits
Add to `docker-compose.yml`:
```yaml
services:
  faith-agency-ai:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### Log Rotation
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 🔒 Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Regularly update** Docker images and dependencies
4. **Monitor logs** for suspicious activity
5. **Use HTTPS** in production
6. **Implement firewall rules** to restrict access

## 📞 Support

If you encounter issues:

1. Check the logs: `sudo docker-compose logs -f`
2. Verify environment variables in `.env`
3. Ensure all required credentials are in place
4. Check Docker and system resources

---

**🎯 Ready to Deploy?**

Simply run: `sudo docker-compose up -d`

Your Faith Agency AI Calling System will be running on `http://localhost:8000`!