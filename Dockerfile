FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install PyMuPDF binary wheel FIRST (pre-built)
RUN pip install --no-cache-dir --only-binary :all: PyMuPDF==1.23.8 || true

# Install other requirements
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir --no-deps -r requirements-serverless.txt && \
    pip install --no-cache-dir --only-binary :all: numpy opencv-python

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
