# Fly Straight PDF Generator - Render.com Deployment

This service converts markdown-formatted Precision Fuel Protocol content into branded PDFs.

## Files

- `app.py` - Flask web application
- `pdf_generator.py` - PDF generation logic with Fly Straight branding
- `requirements.txt` - Python dependencies
- `README.md` - This file

## API Endpoint

### POST /generate-pdf

Generates a branded PDF from markdown content.

**Request Body (JSON):**
```json
{
  "markdown_content": "# PRECISION FUEL PROTOCOL...",
  "client_name": "Javier"
}
```

**Response:**
- Content-Type: `application/pdf`
- Binary PDF file download

**Example cURL:**
```bash
curl -X POST https://your-app.onrender.com/generate-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "markdown_content": "# PRECISION FUEL PROTOCOL\n\n**Javier**...",
    "client_name": "Javier"
  }' \
  --output output.pdf
```

## Health Check

### GET /

Returns service status.

**Response:**
```json
{
  "status": "online",
  "service": "Fly Straight PDF Generator",
  "version": "1.0"
}
```

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Test endpoint
curl -X POST http://localhost:5000/generate-pdf \
  -H "Content-Type: application/json" \
  -d '{"markdown_content": "test", "client_name": "Test"}' \
  --output test.pdf
```

## Deployment to Render.com

1. Push code to GitHub repository
2. Connect repository to Render.com
3. Render will auto-detect Python and use requirements.txt
4. Set start command: `gunicorn app:app`
5. Deploy!

## Integration with Make.com

**Module: HTTP - Make a Request**

- **URL:** `https://your-app.onrender.com/generate-pdf`
- **Method:** POST
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "markdown_content": "{{markdown_from_chatgpt}}",
  "client_name": "{{client_name}}"
}
```

**Response will be PDF binary data - save with Google Drive Upload module**
