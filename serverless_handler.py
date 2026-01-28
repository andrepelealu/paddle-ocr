import os
import sys
import logging
import traceback
from io import BytesIO

os.environ['DISPLAY'] = ''
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Paddle GPU optimization
os.environ['FLAGS_allocator_strategy'] = 'auto_growth'
os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0.85'  # More headroom to prevent OOM
os.environ['FLAGS_cudnn_exhaustive_search'] = '1'
os.environ['FLAGS_cudnn_deterministic'] = '0'

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

ocr = None


# -----------------------
# Lazy OCR init (GPU)
# -----------------------
def get_ocr():
    global ocr
    if ocr is None:
        try:
            import paddle
            from paddleocr import PaddleOCR

            if not paddle.is_compiled_with_cuda():
                raise RuntimeError("Paddle is NOT compiled with CUDA")

            ocr = PaddleOCR(
                use_gpu=True,
                lang="en",
                use_angle_cls=False,
                gpu_mem=22000,          # use almost all 24GB
                use_tensorrt=True,      # BIG speedup
                precision="fp16",
                enable_mkldnn=False,
                show_log=False,
                use_dilation=False,
                rec_batch_num=16,       # Process 16 text regions at once
                det_db_thresh=0.3,      # Detection threshold
                det_db_box_thresh=0.6,  # Box filtering threshold
                max_batch_size=16,      # TensorRT max batch size
            )

            print("✓ PaddleOCR initialized (GPU, FP16, TensorRT)")
        except Exception as e:
            logger.error(f"OCR init failed: {e}")
            raise
    return ocr


# -----------------------
# Image preprocessing
# -----------------------
def preprocess_image(img, max_dim=2560):
    import numpy as np
    import cv2
    from PIL import Image

    if isinstance(img, Image.Image):
        # Resize while still in PIL (faster)
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        # Convert directly to BGR for OpenCV
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    return img


# -----------------------
# PDF → Images (FAST, GPU friendly)
# -----------------------
def pdf_to_images(pdf_bytes):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_bytes)
    images = []

    for page in pdf:
        # Render page to bitmap then convert to PIL
        bitmap = page.render(scale=2.0)
        pil = bitmap.to_pil()
        images.append(pil)

    return images


# -----------------------
# Core OCR logic (OPTIMIZED)
# -----------------------
def ocr_images(images, ocr_engine):
    from concurrent.futures import ThreadPoolExecutor

    # Parallel CPU preprocessing for better performance
    if len(images) > 1:
        with ThreadPoolExecutor(max_workers=4) as executor:
            batch = list(executor.map(preprocess_image, images))
    else:
        batch = [preprocess_image(images[0])]

    # Process each image individually with TensorRT optimization
    # Note: PaddleOCR with TensorRT has issues with batch processing via the API
    # but still benefits from internal TensorRT optimizations per image
    pages = []
    for i, img in enumerate(batch):
        try:
            # Process single image
            result = ocr_engine.ocr(img, cls=False)

            text = []
            if result and result[0]:
                for line in result[0]:
                    text.append(line[1][0])

            pages.append({
                "page_number": i + 1,
                "raw_text": "\n".join(text)
            })

        except Exception as e:
            logger.error(f"OCR failed for page {i + 1}: {e}")
            pages.append({
                "page_number": i + 1,
                "raw_text": "",
                "error": str(e)
            })

    return pages


# -----------------------
# RunPod handler
# -----------------------
def handler(job):
    try:
        import requests
        from PIL import Image

        job_input = job.get("input", {})
        url = job_input.get("pdf_url")

        if not url:
            return {"error": "Missing pdf_url"}

        filename = job_input.get("filename", "document.pdf")

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        ocr_engine = get_ocr()

        # Image
        if url.lower().endswith((".jpg", ".jpeg", ".png")):
            img = Image.open(BytesIO(resp.content))
            pages = ocr_images([img], ocr_engine)
            return {
                "filename": filename,
                "total_pages": 1,
                "pages": pages
            }

        # PDF
        images = pdf_to_images(resp.content)
        pages = ocr_images(images, ocr_engine)

        return {
            "filename": filename,
            "total_pages": len(pages),
            "pages": pages
        }

    except Exception as e:
        logger.error(traceback.format_exc())
        return {"error": str(e)}


# -----------------------
# Start RunPod
# -----------------------
if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": handler})
