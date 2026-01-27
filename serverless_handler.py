"""
RunPod Serverless Handler - PRODUCTION

This is the production deployment for RunPod Serverless.
Accepts PDF/image URLs and returns extracted text as JSON.

For local development/testing, use ocr_pdf.py instead.
"""

import sys
import os

# Force headless mode for OpenCV before importing cv2
os.environ['DISPLAY'] = ''
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import logging
import traceback

# Configure logging - production ready
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Global OCR instance (lazy-loaded)
ocr = None

def get_ocr():
    """Lazy-load OCR engine on first use"""
    global ocr
    if ocr is None:
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(
                use_angle_cls=False,  # Disabled for receipts (usually upright) - saves 30-50ms/page
                lang="en",
                use_gpu=True,  # Enable GPU if available (falls back to CPU)
                det_db_thresh=0.3,  # Detection threshold
                det_db_box_thresh=0.6,  # Box threshold for filtering noise
            )
            print("✓ PaddleOCR initialized successfully")  # Startup info only
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}\n{traceback.format_exc()}")
            raise
    return ocr

def is_image_url(url):
    """Check if URL points to an image based on extension"""
    url_lower = url.lower()
    return any(url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png'])

def process_image(img, ocr_engine, max_dimension=1920):
    """
    Process a single image with OCR

    Args:
        img: PIL Image or numpy array
        ocr_engine: PaddleOCR instance
        max_dimension: Maximum width/height in pixels (default 1920)

    Returns:
        str: Extracted raw text
    """
    import cv2
    import numpy as np

    # Convert PIL to numpy if needed
    if hasattr(img, 'mode'):  # PIL Image
        img_array = np.array(img)
    else:
        img_array = img

    # OPTIMIZATION: Resize large images to save processing time
    height, width = img_array.shape[:2]
    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img_array = cv2.resize(img_array, (new_width, new_height),
                              interpolation=cv2.INTER_AREA)

    # Convert RGB to BGR for OpenCV
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array

    # Run OCR (cls=False for receipts - they're usually upright)
    ocr_result = ocr_engine.ocr(img_bgr, cls=False)

    # Extract text
    all_text = []
    if ocr_result and ocr_result[0]:
        for line in ocr_result[0]:
            text = line[1][0]
            all_text.append(text)

    return '\n'.join(all_text)

def process_file_from_bytes(file_bytes, filename, ocr_engine):
    """
    Process file from bytes (PDF or image)

    Args:
        file_bytes: File content as bytes
        filename: Original filename
        ocr_engine: PaddleOCR instance

    Returns:
        dict: Results in standard format
    """
    import tempfile
    from PIL import Image
    from io import BytesIO
    from pdf2image import convert_from_path
    import os

    # Determine file type
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    if ext in ['jpg', 'jpeg', 'png']:
        # Process as image
        img = Image.open(BytesIO(file_bytes))
        raw_text = process_image(img, ocr_engine)

        return {
            'filename': filename,
            'total_pages': 1,
            'pages': [{
                'page_number': 1,
                'raw_text': raw_text
            }]
        }
    else:
        # Process as PDF - requires temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        try:
            # Use 150 DPI for faster processing (200-300 for higher quality)
            pages = convert_from_path(tmp_path, dpi=150)

            results = {
                'filename': filename,
                'total_pages': len(pages),
                'pages': [None] * len(pages)  # Pre-allocate list
            }

            # OPTIMIZATION: Use parallel processing for multiple pages
            if len(pages) > 1:
                max_workers = min(4, len(pages))  # Limit to 4 workers
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all pages
                    future_to_page = {
                        executor.submit(process_image, page, ocr_engine): page_num
                        for page_num, page in enumerate(pages)
                    }

                    # Collect results as they complete
                    for future in as_completed(future_to_page):
                        page_num = future_to_page[future]
                        try:
                            raw_text = future.result()
                            results['pages'][page_num] = {
                                'page_number': page_num + 1,
                                'raw_text': raw_text
                            }
                        except Exception as e:
                            logger.error(f"OCR failed for page {page_num + 1}: {e}")
                            results['pages'][page_num] = {
                                'page_number': page_num + 1,
                                'raw_text': '',
                                'error': str(e)
                            }
            else:
                # Single page - no need for parallel processing
                raw_text = process_image(pages[0], ocr_engine)
                results['pages'][0] = {
                    'page_number': 1,
                    'raw_text': raw_text
                }

            return results
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

def handler(job):
    """RunPod handler function"""
    try:
        # Import here to avoid startup failures
        from pdf2image import convert_from_path
        import cv2
        import numpy as np
        import requests
        from io import BytesIO
        import tempfile
        from concurrent.futures import ThreadPoolExecutor, as_completed

        job_input = job.get('input', {})

        # Validate input
        if 'pdf_url' not in job_input:
            error_msg = 'Missing required field: pdf_url (can be PDF or image URL)'
            logger.error(error_msg)
            return {'error': error_msg}

        pdf_url = job_input['pdf_url']
        default_filename = 'receipt.jpg' if is_image_url(pdf_url) else 'document.pdf'
        filename = job_input.get('filename', default_filename)

        try:
            # Download and process file
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()

            ocr_engine = get_ocr()
            results = process_file_from_bytes(response.content, filename, ocr_engine)
            return results

        except Exception as e:
            logger.error(f"Processing failed for {filename}: {e}\n{traceback.format_exc()}")
            return {'error': str(e)}

    except Exception as e:
        logger.error(f"Handler failed: {e}\n{traceback.format_exc()}")
        return {'error': str(e)}

# Start RunPod serverless handler
if __name__ == "__main__":
    try:
        import runpod
        runpod.serverless.start({"handler": handler})
    except Exception as e:
        logger.error(f"Failed to start RunPod handler: {e}\n{traceback.format_exc()}")
        sys.exit(1)
