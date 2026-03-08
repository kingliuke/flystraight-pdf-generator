"""
Fly Straight PDF Generator - Flask API
Receives markdown content, generates branded PDF
"""

from flask import Flask, request, jsonify, send_file
import os
import io
from pdf_generator import generate_fuel_protocol_pdf

app = Flask(__name__)

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "service": "Fly Straight PDF Generator",
        "version": "1.0"
    })

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Generate branded PDF from markdown content
    
    Accepts two formats:
    
    1. JSON:
    {
        "markdown_content": "...",
        "client_name": "Javier"
    }
    
    2. Raw text with client name in header:
    Headers: X-Client-Name: Javier
    Content-Type: text/plain
    Body: Raw markdown text
    """
    try:
        # Check content type
        content_type = request.headers.get('Content-Type', '')
        
        # Handle text/plain
        if 'text/plain' in content_type:
            markdown_content = request.get_data(as_text=True)
            client_name = request.headers.get('X-Client-Name', 'Client')
        # Handle JSON
        elif request.is_json or 'application/json' in content_type:
            data = request.get_json()
            markdown_content = data.get('markdown_content')
            client_name = data.get('client_name', 'Client')
        else:
            return jsonify({"error": "Unsupported Content-Type. Use 'text/plain' or 'application/json'"}), 415
        
        if not markdown_content:
            return jsonify({"error": "No content provided"}), 400
        
        # Generate PDF
        print(f"Generating PDF for {client_name}...")
        pdf_buffer = generate_fuel_protocol_pdf(markdown_content, client_name)
        
        # Return PDF as file
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{client_name}_Precision_Fuel_Protocol.pdf'
        )
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # For local testing
    app.run(debug=True, host='0.0.0.0', port=5000)
