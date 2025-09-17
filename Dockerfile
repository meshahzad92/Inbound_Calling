# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python3.12 -m venv venv && \
    . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Create necessary directories for credentials and data
RUN mkdir -p /app/email_automation /app/sheets_automation /app/data

# Set permissions for the venv
RUN chmod +x venv/bin/activate

# Expose the port the app runs on
EXPOSE 8000

# Health check to ensure the app is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application with virtual environment activated
CMD ["/bin/bash", "-c", "source venv/bin/activate && python main.py"]