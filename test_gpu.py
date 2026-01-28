#!/usr/bin/env python3
"""
Test script to verify GPU availability for PaddleOCR
Run this in your RunPod environment to check GPU setup
"""

print("="*60)
print("GPU Availability Test for PaddleOCR")
print("="*60)

# Test 1: Check CUDA availability
print("\n1. Checking CUDA...")
try:
    import paddle
    print(f"   ✓ PaddlePaddle version: {paddle.__version__}")
    print(f"   ✓ CUDA available: {paddle.is_compiled_with_cuda()}")

    if paddle.is_compiled_with_cuda():
        print(f"   ✓ CUDA version: {paddle.version.cuda()}")
        print(f"   ✓ cuDNN version: {paddle.version.cudnn()}")

        # Check GPU devices
        gpu_count = paddle.device.cuda.device_count()
        print(f"   ✓ GPU devices available: {gpu_count}")

        if gpu_count > 0:
            for i in range(gpu_count):
                props = paddle.device.cuda.get_device_properties(i)
                print(f"   ✓ GPU {i}: {props.name}")
                print(f"      - Total memory: {props.total_memory / 1024**3:.2f} GB")
        else:
            print("   ✗ No GPU devices detected!")
    else:
        print("   ✗ PaddlePaddle compiled WITHOUT CUDA support!")
        print("   → You need to install: paddlepaddle-gpu")

except ImportError:
    print("   ✗ PaddlePaddle not installed!")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Test PaddleOCR with GPU
print("\n2. Testing PaddleOCR GPU initialization...")
try:
    from paddleocr import PaddleOCR

    # Try to initialize with GPU
    ocr = PaddleOCR(use_gpu=True, lang="en", show_log=False)
    print("   ✓ PaddleOCR initialized with GPU successfully!")

    # Check if actually using GPU
    import paddle
    if paddle.device.is_compiled_with_cuda():
        print("   ✓ GPU is being used for inference")
    else:
        print("   ✗ Falling back to CPU (GPU not available)")

except Exception as e:
    print(f"   ✗ Failed to initialize PaddleOCR with GPU: {e}")

# Test 3: System info
print("\n3. System Information...")
try:
    import os
    import subprocess

    # Check nvidia-smi
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    if result.returncode == 0:
        print("   ✓ nvidia-smi output:")
        print(result.stdout)
    else:
        print("   ✗ nvidia-smi not available")

except Exception as e:
    print(f"   ✗ Could not get system info: {e}")

print("\n" + "="*60)
print("Test Complete")
print("="*60)
