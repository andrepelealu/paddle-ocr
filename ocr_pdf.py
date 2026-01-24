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

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/ocr', methods=['POST'])
def ocr_pdf():
    """
    API endpoint to extract text from PDF using PaddleOCR
    
    Request:
        - multipart/form-data with 'file' field containing PDF
        
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
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        logger.info(f"Processing file: {temp_path}")
        
        try:
            # Convert PDF to images
            pages = convert_from_path(temp_path, dpi=300)
            logger.info(f"Converted PDF to {len(pages)} pages")
            
            results = {
                'filename': filename,
                'total_pages': len(pages),
                'pages': []
            }
            
            # Process each page
            for page_num, page in enumerate(pages):
                try:
                    logger.info(f"Processing page {page_num + 1}")
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
                    return jsonify({'error': f'Error processing page {page_num + 1}: {str(e)}'}), 500
            
            return jsonify(results), 200
        
        except Exception as e:
            logger.error(f"Error converting PDF: {e}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'PDF conversion error: {str(e)}'}), 500
        
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
                pages = convert_from_path(temp_path, dpi=300)
                
                file_result = {
                    'filename': filename,
                    'total_pages': len(pages),
                    'pages': []
                }
                
                for page_num, page in enumerate(pages):
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
                    
                    file_result['pages'].append(page_data)
                
                batch_results.append(file_result)
            
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
