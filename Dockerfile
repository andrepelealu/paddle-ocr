FROM runpod/base:0.4.0-cuda11.8.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest
RUN pip install --upgrade pip setuptools wheel

# Install dependencies using only pre-built wheels (no compilation)
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir --only-binary :all: -r requirements-serverless.txt || \
    pip install --no-cache-dir -r requirements-serverless.txt

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
