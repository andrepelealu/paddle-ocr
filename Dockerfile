FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install all requirements with dependencies
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir -r requirements-serverless.txt

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
