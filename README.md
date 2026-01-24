# PaddleOCR PDF API

A Flask API and RunPod Serverless function for extracting text from PDF files using PaddleOCR with JSON response format.

## Features

- **Single PDF Processing** - Upload and extract text from a single PDF
- **Batch Processing** - Process multiple PDFs at once
- **Serverless Support** - Deploy on RunPod Serverless for automatic scaling
- **URL-based Input** - Process PDFs directly from URLs (serverless)
- **Health Check** - Check API status
- JSON responses with text content and page numbers

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install poppler (required for pdf2image):
```bash
# macOS (using Homebrew)
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases/
```

## Option 1: Flask API (Development/Production)

### Running the API

```bash
# Set ngrok token (optional, for public URL)
export NGROK_AUTHTOKEN="your_token_here"

# Start the API
python ocr_pdf.py
```

The API will start at `http://localhost:5000`

### API Endpoints

#### Single PDF OCR
**POST** `/api/ocr`

Upload a single PDF file for OCR processing.

```bash
curl -X POST -F "file=@your_file.pdf" http://localhost:5000/api/ocr
```

**Response:**
```json
{
  "filename": "your_file.pdf",
  "total_pages": 2,
  "pages": [
    {
      "page_number": 1,
      "raw_text": "Extracted text from page 1..."
    },
    {
      "page_number": 2,
      "raw_text": "Extracted text from page 2..."
    }
  ]
}
```

#### Batch OCR
**POST** `/api/ocr/batch`

Process multiple PDF files in one request.

```bash
curl -X POST -F "files=@file1.pdf" -F "files=@file2.pdf" http://localhost:5000/api/ocr/batch
```

**Response:**
```json
{
  "results": [
    {
      "filename": "file1.pdf",
      "total_pages": 1,
      "pages": [...]
    },
    {
      "filename": "file2.pdf",
      "total_pages": 2,
      "pages": [...]
    }
  ]
}
```

#### Health Check
**GET** `/api/health`

```bash
curl http://localhost:5000/api/health
```

**Response:**
```json
{
  "status": "OK",
  "ocr_status": "OK"
}
```

## Option 2: RunPod Serverless (Production Scale)

### Setup Instructions

1. **Create a RunPod Serverless Endpoint:**
   - Go to https://www.runpod.io/console/serverless
   - Click "Create Template"
   - Use this Docker image: `runpod/base:0.4.0-cuda11.8.0` or similar
   - Container disk: 50GB (for models)
   - Max timeout: 900 seconds
   - Upload the following files to your repo/template:
     - `serverless_handler.py`
     - `requirements.txt`

2. **Dockerfile** (create in your repo):
```dockerfile
FROM runpod/base:0.4.0-cuda11.8.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    swig \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy handler
COPY serverless_handler.py .

# Set entrypoint
CMD ["python", "serverless_handler.py"]
```

3. **Deploy on RunPod:**
   - Push your repo or use the template builder
   - Set the Handler path: `serverless_handler.py`
   - Deploy and get your Endpoint ID

### Using RunPod Serverless

#### Process PDF from URL

```bash
curl -X POST https://api.runpod.io/v2/[ENDPOINT_ID]/run \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "pdf_url": "https://example.com/document.pdf",
      "filename": "document.pdf"
    }
  }'
```

**Response:**
```json
{
  "id": "async-job-id",
  "status": "QUEUED"
}
```

Check status:
```bash
curl https://api.runpod.io/v2/[ENDPOINT_ID]/status/[JOB_ID]
```

Get results:
```bash
curl https://api.runpod.io/v2/[ENDPOINT_ID]/stream/[JOB_ID]
```

**Output format:**
```json
{
  "output": {
    "filename": "document.pdf",
    "total_pages": 2,
    "pages": [
      {
        "page_number": 1,
        "raw_text": "Extracted text..."
      }
    ]
  }
}
```

### RunPod Serverless Input Format

```json
{
  "input": {
    "pdf_url": "string - URL to the PDF file",
    "filename": "string - optional, custom filename (default: document.pdf)"
  }
}
```

## Configuration

### Flask API (ocr_pdf.py)

Edit to customize:

- **Language**: Change `lang="en"` to:
  - `"id"` for Indonesian
  - `"en+id"` for English + Indonesian
  - Other language codes supported by PaddleOCR

- **DPI**: Change `dpi=300` for different image resolution (higher = better quality but slower)

- **Max file size**: Modify `app.config['MAX_CONTENT_LENGTH']` (50MB default)

- **Port**: Change `port=5000` to use a different port

### Serverless Handler (serverless_handler.py)

- **Language**: Change `lang="en"` in the PaddleOCR initialization
- **DPI**: Change `dpi=300` in the `process_pdf` function
- **Timeout**: RunPod default is 15 minutes, can be customized

## Error Handling

### Flask API
- `200` - Success
- `400` - Bad request (invalid file, missing file)
- `500` - Server error

### Serverless
- `{"error": "..."}` - Error message in response
- Check endpoint logs on RunPod console for detailed errors

## Performance Tips

- First request may take longer as the OCR model is loaded
- Use DPI 150-200 for faster processing, 300+ for better accuracy
- For large PDFs, serverless is recommended (auto-scales)
- RunPod Serverless bills only for execution time

## Dependencies

- Flask: Web framework (Flask API only)
- pdf2image: PDF to image conversion
- PaddleOCR: Text recognition
- OpenCV: Image processing
- Werkzeug: WSGI utilities (Flask API only)
- RunPod: Serverless API client (Serverless only)
- Requests: HTTP library (Serverless only)

## Troubleshooting

### "poppler not found"
Install poppler system package (see Installation section)

### "ngrok authentication failed"
Get free authtoken from https://dashboard.ngrok.com/get-started/your-authtoken

### "could not execute a primitive"
This is a PaddleOCR internal error. Try:
- Reduce DPI to 200
- Update PaddleOCR: `pip install --upgrade paddleocr`
- Check PDF quality/format

### Serverless timeout
Increase timeout in RunPod endpoint settings or reduce DPI for faster processing
