# Dockerfile
# Backend API service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY services/ ./services/
COPY config.py .
COPY models.py .
COPY constants.py .
COPY exceptions.py .
COPY utils/ ./utils/

# Create data directories
RUN mkdir -p /data/images

# Expose port
EXPOSE 8000

# Run the application with auto-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]