FROM runpod/base:0.4.0-cuda11.8.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pip packages
RUN pip install --no-cache-dir -U pip setuptools wheel

# Install requirements (allow PyMuPDF to compile since it's a transitive dep)
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir -r requirements-serverless.txt

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
