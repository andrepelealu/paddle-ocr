FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies INCLUDING swig for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    swig \
    poppler-utils \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install all requirements with dependencies
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir -r requirements-serverless.txt

# Clean up build artifacts to reduce image size
RUN apt-get remove -y build-essential swig && apt-get autoremove -y

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
