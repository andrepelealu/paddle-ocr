"""
RunPod Serverless Handler for PDF OCR
Accepts PDF URLs and returns extracted text as JSON
"""

import sys
import os

# Force headless mode for OpenCV before importing cv2
os.environ['DISPLAY'] = ''
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import logging
import traceback

# Configure logging FIRST
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

logger.info("=== Starting PaddleOCR Serverless Handler ===")

# Global OCR instance (lazy-loaded)
ocr = None

def get_ocr():
    """Lazy-load OCR engine on first use"""
    global ocr
    if ocr is None:
        try:
            logger.info("Initializing PaddleOCR (first use)...")
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False
            )
            logger.info("PaddleOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            logger.error(traceback.format_exc())
            raise
    return ocr

def is_image_url(url):
    """Check if URL points to an image based on extension"""
    url_lower = url.lower()
    return any(url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png'])

def process_image(img, ocr_engine):
    """
    Process a single image with OCR

    Args:
        img: PIL Image or numpy array
        ocr_engine: PaddleOCR instance

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

    # Convert RGB to BGR for OpenCV
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_array

    # Run OCR
    ocr_result = ocr_engine.ocr(img_bgr, cls=True)

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
            pages = convert_from_path(tmp_path, dpi=300)

            results = {
                'filename': filename,
                'total_pages': len(pages),
                'pages': []
            }

            for page_num, page in enumerate(pages):
                raw_text = process_image(page, ocr_engine)
                results['pages'].append({
                    'page_number': page_num + 1,
                    'raw_text': raw_text
                })

            return results
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

def handler(job):
    """RunPod handler function"""
    try:
        logger.info("=== Job received ===")
        
        # Import here to avoid startup failures
        from pdf2image import convert_from_path
        import cv2
        import numpy as np
        import requests
        from io import BytesIO
        import tempfile
        
        job_input = job.get('input', {})
        logger.info(f"Job input: {job_input}")
        
        # Validate input
        if 'pdf_url' not in job_input:
            error_msg = 'Missing required field: pdf_url (can be PDF or image URL)'
            logger.error(error_msg)
            return {'error': error_msg}

        pdf_url = job_input['pdf_url']
        default_filename = 'receipt.jpg' if is_image_url(pdf_url) else 'document.pdf'
        filename = job_input.get('filename', default_filename)
        
        try:
            # Download file
            logger.info(f"Downloading file from: {pdf_url}")
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            logger.info(f"File downloaded: {len(response.content)} bytes")

            # Get OCR engine
            ocr_engine = get_ocr()

            # Process file (PDF or image)
            logger.info(f"Processing {filename}")
            results = process_file_from_bytes(response.content, filename, ocr_engine)
            logger.info(f"Successfully processed {filename}")

            return results
        
        except Exception as e:
            logger.error(f"Processing error: {e}")
            logger.error(traceback.format_exc())
            return {'error': str(e)}
    
    except Exception as e:
        logger.error(f"Handler error: {e}")
        logger.error(traceback.format_exc())
        return {'error': str(e)}

# Test mode - verify handler can start
if __name__ == "__main__":
    logger.info("Handler script loaded successfully")
    try:
        import runpod
        logger.info("RunPod imported successfully")
        runpod.serverless.start({"handler": handler})
    except Exception as e:
        logger.error(f"Failed to start RunPod handler: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
