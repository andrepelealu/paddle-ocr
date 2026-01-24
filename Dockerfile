FROM runpod/base:0.4.0-cuda11.8.0

WORKDIR /app

# Install ALL system dependencies needed for compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    poppler-utils \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install requirements
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir -r requirements-serverless.txt

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
