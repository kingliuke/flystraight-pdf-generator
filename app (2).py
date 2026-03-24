"""
Fly Straight PDF Generator - Flask API
Receives markup/markdown content, generates branded PDFs

Routes:
  POST /generate-pdf      → Precision Fuel Protocol (existing)
  POST /generate-checkin  → Weekly Check-In document (new)
"""

from flask import Flask, request, jsonify, send_file
import os
import io
from pdf_generator import generate_fuel_protocol_pdf
from checkin_pdf_generator import generate_checkin_pdf

app = Flask(__name__)


@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "service": "Fly Straight PDF Generator",
        "version": "2.0",
        "endpoints": {
            "fuel_protocol": "POST /generate-pdf",
            "weekly_checkin": "POST /generate-checkin"
        }
    })


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Generate branded Precision Fuel Protocol PDF from markdown content.

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
        content_type = request.headers.get('Content-Type', '')

        if 'text/plain' in content_type:
            markdown_content = request.get_data(as_text=True)
            client_name = request.headers.get('X-Client-Name', 'Client')
        elif request.is_json or 'application/json' in content_type:
            data = request.get_json()
            markdown_content = data.get('markdown_content')
            client_name = data.get('client_name', 'Client')
        else:
            return jsonify({
                "error": "Unsupported Content-Type. Use 'text/plain' or 'application/json'"
            }), 415

        if not markdown_content:
            return jsonify({"error": "No content provided"}), 400

        print(f"Generating Fuel Protocol PDF for {client_name}...")
        pdf_buffer = generate_fuel_protocol_pdf(markdown_content, client_name)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{client_name}_Precision_Fuel_Protocol.pdf'
        )

    except Exception as e:
        print(f"Error generating Fuel Protocol PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/generate-checkin', methods=['POST'])
def generate_checkin():
    """
    Generate branded weekly check-in PDF from custom markup content.

    Accepts two formats:

    1. Raw text (recommended — matches Make.com HTTP module setup):
    Headers:
      Content-Type: text/plain
      X-Client-Name: Javier
    Body: Raw markup content (output of Modules 3 + 4 + 5 concatenated)

    2. JSON:
    {
        "markup_content": "...",
        "client_name": "Javier"
    }
    """
    try:
        content_type = request.headers.get('Content-Type', '')

        if 'text/plain' in content_type:
            markup_content = request.get_data(as_text=True)
            client_name = request.headers.get('X-Client-Name', 'Client')
        elif request.is_json or 'application/json' in content_type:
            data = request.get_json()
            markup_content = data.get('markup_content')
            client_name = data.get('client_name', 'Client')
        else:
            return jsonify({
                "error": "Unsupported Content-Type. Use 'text/plain' or 'application/json'"
            }), 415

        if not markup_content:
            return jsonify({"error": "No content provided"}), 400

        print(f"Generating Check-In PDF for {client_name}...")
        pdf_buffer = generate_checkin_pdf(markup_content, client_name)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{client_name}_CheckIn.pdf'
        )

    except Exception as e:
        print(f"Error generating Check-In PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
