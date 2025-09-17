# Use Python 3.12 slim image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy requirements and application code
COPY requirements.txt .
COPY . .

# Create virtual environment
RUN python3.12 -m venv venv

# Activate venv and install requirements
RUN . venv/bin/activate && pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Run the application
CMD ["/bin/bash", "-c", "source venv/bin/activate && python main.py"]