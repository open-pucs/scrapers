# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Install Playwright browsers
RUN playwright install chromium
