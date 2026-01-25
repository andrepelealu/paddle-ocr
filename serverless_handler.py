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
            error_msg = 'Missing required field: pdf_url'
            logger.error(error_msg)
            return {'error': error_msg}
        
        pdf_url = job_input['pdf_url']
        filename = job_input.get('filename', 'document.pdf')
        
        try:
            # Download PDF
            logger.info(f"Downloading PDF from: {pdf_url}")
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            logger.info(f"PDF downloaded: {len(response.content)} bytes")
            
            # Save to temporary file (convert_from_path needs a file path, not BytesIO)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            logger.info(f"PDF saved to temp file: {tmp_path}")
            
            try:
                # Convert PDF to images
                logger.info("Converting PDF to images...")
                pages = convert_from_path(tmp_path, dpi=300)
                logger.info(f"Converted to {len(pages)} pages")
                
                results = {
                    'filename': filename,
                    'total_pages': len(pages),
                    'pages': []
                }
                
                # Get OCR engine
                ocr_engine = get_ocr()
                
                # Process each page
                for page_num, page in enumerate(pages):
                    try:
                        logger.info(f"Processing page {page_num + 1}/{len(pages)}")
                        img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                        ocr_result = ocr_engine.ocr(img, cls=True)
                        
                        # Extract text
                        all_text = []
                        if ocr_result and ocr_result[0]:
                            for line in ocr_result[0]:
                                text = line[1][0]
                                all_text.append(text)
                        
                        page_data = {
                            'page_number': page_num + 1,
                            'raw_text': '\n'.join(all_text)
                        }
                        
                        results['pages'].append(page_data)
                        logger.info(f"Page {page_num + 1} completed")
                    
                    except Exception as e:
                        logger.error(f"Error processing page {page_num + 1}: {e}")
                        logger.error(traceback.format_exc())
                        raise
                
                logger.info(f"Successfully processed {filename}")
                return results
            
            finally:
                # Clean up temp file
                import os as os_module
                if os_module.path.exists(tmp_path):
                    os_module.remove(tmp_path)
                    logger.info(f"Cleaned up temp file: {tmp_path}")
        
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
