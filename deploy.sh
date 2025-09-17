#!/bin/bash

# Faith Agency AI Calling System - Docker Deployment Script
# This script handles the complete deployment of the AI calling system

set -e  # Exit on any error

echo "🚀 Faith Agency AI Calling System - Docker Deployment"
echo "=" * 60

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check for required files
echo "🔍 Checking required files..."

if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it with your API keys."
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found."
    exit 1
fi

echo "✅ All required files found."

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p email_automation
mkdir -p sheets_automation

# Check for credentials
echo "🔐 Checking for Google API credentials..."
if [ ! -f "credentials.json" ]; then
    echo "⚠️  credentials.json not found. You'll need to add it for Google Sheets integration."
    echo "   Place it in the root directory after starting the container."
fi

if [ ! -f "email_automation/credentials.json" ]; then
    echo "⚠️  email_automation/credentials.json not found. You'll need to add it for Gmail integration."
fi

if [ ! -f "sheets_automation/credentials.json" ]; then
    echo "⚠️  sheets_automation/credentials.json not found. You'll need to add it for Google Sheets automation."
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start the container
echo "🔧 Building and starting the Faith Agency AI Calling System..."
docker-compose up -d --build

# Wait for the service to be ready
echo "⏳ Waiting for service to be ready..."
sleep 10

# Check if the service is running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Faith Agency AI Calling System is running successfully!"
    echo ""
    echo "📊 Service Information:"
    echo "   - Container: faith-agency-calling-system"
    echo "   - Port: 8000"
    echo "   - Health Check: http://localhost:8000/health"
    echo "   - API Endpoint: http://localhost:8000/api/incoming"
    echo ""
    echo "🔍 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
    echo "🔄 To restart: docker-compose restart"
    echo ""
    echo "⚠️  Don't forget to:"
    echo "   1. Add your Google API credentials to the respective folders"
    echo "   2. Configure your Twilio webhook to point to this server"
    echo "   3. Set up ngrok if testing locally: ngrok http 8000"
else
    echo "❌ Failed to start the service. Check logs with: docker-compose logs"
    exit 1
fi