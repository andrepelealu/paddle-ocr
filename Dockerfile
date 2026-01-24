FROM runpod/base:0.4.0-cuda11.8.0

WORKDIR /app

# Install system dependencies ONLY
RUN apt-get update && apt-get install -y \
    poppler-utils \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install pip packages individually to control versions
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir \
    numpy==1.23.5 \
    opencv-python==4.6.0.66 \
    pdf2image==1.16.3 \
    paddlepaddle==2.6.2 \
    paddleocr==2.7.0.3 \
    runpod==0.4.2 \
    requests==2.31.0

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
