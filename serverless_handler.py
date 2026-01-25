"""
RunPod Serverless Handler for PDF OCR
Accepts PDF URLs and returns extracted text as JSON
"""

import sys
import os
import logging

# Configure logging FIRST
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.info("=== Starting PaddleOCR Serverless Handler ===")

try:
    logger.info("Importing dependencies...")
    import runpod
    from pdf2image import convert_from_path
    from paddleocr import PaddleOCR
    import cv2
    import numpy as np
    import tempfile
    import traceback
    import requests
    from io import BytesIO
    logger.info("All imports successful")
except Exception as e:
    logger.error(f"Import failed: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# Initialize OCR once
ocr = None
try:
    logger.info("Initializing PaddleOCR...")
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang="en",
        use_gpu=False  # Explicit CPU mode
    )
    logger.info("PaddleOCR initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize PaddleOCR: {e}")
    logger.error(traceback.format_exc())

def download_pdf(url):
    """Download PDF from URL and return as bytes"""
    try:
        logger.info(f"Downloading PDF from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logger.info(f"PDF downloaded successfully, size: {len(response.content)} bytes")
        return BytesIO(response.content)
    except Exception as e:
        logger.error(f"Failed to download PDF: {e}")
        raise Exception(f"Failed to download PDF from URL: {str(e)}")

def process_pdf(pdf_file, filename):
    """Process PDF file and extract text"""
    try:
        if not ocr:
            raise Exception("OCR engine not initialized")
        
        logger.info(f"Converting PDF to images: {filename}")
        # Convert PDF to images
        pages = convert_from_path(pdf_file, dpi=300)
        logger.info(f"Converted PDF to {len(pages)} pages")
        
        results = {
            'filename': filename,
            'total_pages': len(pages),
            'pages': []
        }
        
        # Process each page
        for page_num, page in enumerate(pages):
            try:
                logger.info(f"Processing page {page_num + 1}/{len(pages)}")
                img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                ocr_result = ocr.ocr(img, cls=True)
                
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
                logger.info(f"Page {page_num + 1} completed with {len(all_text)} text blocks")
            
            except Exception as e:
                logger.error(f"Error processing page {page_num + 1}: {e}")
                logger.error(traceback.format_exc())
                raise Exception(f"Error processing page {page_num + 1}: {str(e)}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        logger.error(traceback.format_exc())
        raise

def handler(job):
    """
    RunPod handler function
    
    Input format:
    {
        "input": {
            "pdf_url": "https://example.com/document.pdf",
            "filename": "document.pdf"  # optional
        }
    }
    """
    try:
        logger.info(f"=== New job received ===")
        job_input = job['input']
        logger.info(f"Job input: {job_input}")
        
        # Validate input
        if 'pdf_url' not in job_input:
            error_msg = 'Missing required field: pdf_url'
            logger.error(error_msg)
            return {'error': error_msg}
        
        pdf_url = job_input['pdf_url']
        filename = job_input.get('filename', 'document.pdf')
        
        logger.info(f"Processing PDF from URL: {pdf_url}")
        
        # Download PDF
        pdf_file = download_pdf(pdf_url)
        
        # Process PDF
        results = process_pdf(pdf_file, filename)
        
        logger.info(f"Successfully processed {filename}")
        return results
    
    except Exception as e:
        logger.error(f"Handler error: {e}")
        logger.error(traceback.format_exc())
        return {
            'error': str(e)
        }

# RunPod handler entry point
logger.info("Starting RunPod serverless handler...")
try:
    runpod.serverless.start({"handler": handler})
except Exception as e:
    logger.error(f"Failed to start handler: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)
