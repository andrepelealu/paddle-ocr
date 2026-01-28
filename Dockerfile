# Use CUDA-enabled base image for GPU support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.11
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-distutils \
    python3-pip \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install system dependencies INCLUDING graphics libraries for OpenCV
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
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
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
