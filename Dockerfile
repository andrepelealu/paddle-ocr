FROM runpod/base:0.4.0-cuda11.8.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    swig \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only serverless requirements and install
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir -r requirements-serverless.txt

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
