FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

WORKDIR /app

# -----------------------
# GPU ENV (IMPORTANT)
# -----------------------
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

# Paddle / CUDA optimization
ENV FLAGS_allocator_strategy=auto_growth
ENV FLAGS_fraction_of_gpu_memory_to_use=0.85
ENV FLAGS_cudnn_exhaustive_search=1
ENV FLAGS_cudnn_deterministic=0
ENV FLAGS_enable_cuda_graph=1
ENV FLAGS_use_cudnn=1
ENV FLAGS_enable_tensor_core=1

# -----------------------
# System dependencies
# -----------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    git \
    curl \
    swig \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libjpeg-dev \
    zlib1g-dev \
    libssl-dev \
    libffi-dev \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && python -m pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# -----------------------
# Install Paddle GPU (CRITICAL)
# -----------------------
RUN pip install --no-cache-dir \
    paddlepaddle-gpu==2.6.2 \
    -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html

# -----------------------
# Install Python deps
# -----------------------
COPY requirements-serverless.txt .
RUN pip install --no-cache-dir -r requirements-serverless.txt

# Extra: faster PDF rendering
RUN pip install --no-cache-dir pypdfium2

# -----------------------
# Copy app
# -----------------------
COPY serverless_handler.py .

CMD ["python", "serverless_handler.py"]
