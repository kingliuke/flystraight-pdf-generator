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
    
    Expected JSON body:
    {
        "markdown_content": "...",
        "client_name": "Javier"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        markdown_content = data.get('markdown_content')
        client_name = data.get('client_name', 'Client')
        
        if not markdown_content:
            return jsonify({"error": "markdown_content is required"}), 400
        
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
