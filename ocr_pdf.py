from flask import Flask, request, jsonify
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import cv2
import numpy as np
import tempfile
import os
from werkzeug.utils import secure_filename
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# init OCR once
try:
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang="en"  # change to "id" or "en+id" if needed
    )
except Exception as e:
    logger.error(f"Failed to initialize PaddleOCR: {e}")
    ocr = None

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image_file(filename):
    """Check if file is an image based on extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in IMAGE_EXTENSIONS

def process_image(img, ocr_engine):
    """
    Process a single image with OCR

    Args:
        img: PIL Image or numpy array
        ocr_engine: PaddleOCR instance

    Returns:
        str: Extracted raw text
    """
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

def process_file(file_path, filename, ocr_engine):
    """
    Process either PDF or image file

    Args:
        file_path: Path to file
        filename: Original filename
        ocr_engine: PaddleOCR instance

    Returns:
        dict: Results in standard format
    """
    if is_image_file(filename):
        # Process as image
        from PIL import Image
        img = Image.open(file_path)
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
        # Process as PDF
        pages = convert_from_path(file_path, dpi=300)
        logger.info(f"Converted PDF to {len(pages)} pages")

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

@app.route('/api/ocr', methods=['POST'])
def ocr_pdf():
    """
    API endpoint to extract text from PDF or images using PaddleOCR

    Request:
        - multipart/form-data with 'file' field containing PDF or image

    Response:
        - JSON with pages array containing text and confidence scores
    """
    try:
        if not ocr:
            return jsonify({'error': 'OCR engine not initialized'}), 500
        
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF and image files (JPG, PNG) are allowed'}), 400
        
        # Save temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)

        try:
            # Process file (PDF or image)
            logger.info(f"Processing file: {temp_path}")
            results = process_file(temp_path, filename, ocr)
            return jsonify(results), 200

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'File processing error: {str(e)}'}), 500
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    ocr_status = 'OK' if ocr else 'NOT_INITIALIZED'
    return jsonify({'status': 'OK', 'ocr_status': ocr_status}), 200

@app.route('/api/ocr/batch', methods=['POST'])
def ocr_multiple_pdfs():
    """
    Batch process multiple PDFs
    
    Request:
        - multipart/form-data with multiple 'files' fields
        
    Response:
        - JSON array with results for each PDF
    """
    try:
        if not ocr:
            return jsonify({'error': 'OCR engine not initialized'}), 500
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files part'}), 400
        
        files = request.files.getlist('files')
        batch_results = []
        
        for file in files:
            if file.filename == '' or not allowed_file(file.filename):
                batch_results.append({
                    'filename': file.filename,
                    'error': 'Invalid file'
                })
                continue
            
            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_path)

            try:
                results = process_file(temp_path, filename, ocr)
                batch_results.append(results)

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                batch_results.append({
                    'filename': filename,
                    'error': str(e)
                })
            
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        return jsonify({'results': batch_results}), 200
    
    except Exception as e:
        logger.error(f"Batch error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Expose public URL via ngrok on RunPod
    try:
        from pyngrok import ngrok
        import os as os_module
        
        # Set your authtoken (get from https://dashboard.ngrok.com/get-started/your-authtoken)
        authtoken = os_module.getenv('NGROK_AUTHTOKEN')
        if authtoken:
            ngrok.set_auth_token(authtoken)
        
        public_url = ngrok.connect(5000)
        print(f"\n{'='*60}")
        print(f"PUBLIC API URL: {public_url}")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"ngrok not available or not authenticated: {e}")
        print("To use ngrok, set NGROK_AUTHTOKEN environment variable")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
