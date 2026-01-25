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

# Install requests and its dependencies FIRST
RUN pip install --no-cache-dir requests==2.31.0 urllib3==2.1.0 charset-normalizer==3.3.2 idna==3.6 certifi==2023.7.22

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
