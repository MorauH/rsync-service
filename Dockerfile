FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    rsync \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy application files
COPY sync.py /app/
COPY web_server.py /app/
COPY config.json /app/

# Make scripts executable
RUN chmod +x /app/sync.py /app/web_server.py

# Create directories for logs and status
RUN mkdir -p /app/logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Default command
CMD ["python3", "/app/web_server.py", "8080"]