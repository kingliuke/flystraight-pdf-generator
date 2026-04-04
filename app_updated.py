"""
Fly Straight PDF Generator - Flask API
Receives markup/markdown content, generates branded PDFs

Routes:
  POST /generate-pdf        → Precision Fuel Protocol
  POST /generate-checkin    → Weekly Check-In document
  POST /generate-offer      → Fitness Offer document
  POST /generate-onboarding → Fitness Onboarding document
"""

from flask import Flask, request, jsonify, send_file
import os
import io
from pdf_generator import generate_fuel_protocol_pdf
from checkin_pdf_generator import generate_checkin_pdf
from offer_pdf_generator import generate_offer_pdf
from onboarding_pdf_generator import generate_onboarding_pdf

app = Flask(__name__)


@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "service": "Fly Straight PDF Generator",
        "version": "3.0",
        "endpoints": {
            "fuel_protocol":  "POST /generate-pdf",
            "weekly_checkin": "POST /generate-checkin",
            "fitness_offer":  "POST /generate-offer",
            "onboarding":     "POST /generate-onboarding",
        }
    })


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Generate branded Precision Fuel Protocol PDF from markdown content.

    Accepts two formats:

    1. Raw text:
    Headers: Content-Type: text/plain, X-Client-Name: Javier
    Body: Raw markdown text

    2. JSON:
    { "markdown_content": "...", "client_name": "Javier" }
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

    1. Raw text:
    Headers: Content-Type: text/plain, X-Client-Name: Javier
    Body: Raw markup content

    2. JSON:
    { "markup_content": "...", "client_name": "Javier" }
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


@app.route('/generate-offer', methods=['POST'])
def generate_offer():
    """
    Generate branded fitness offer PDF from custom markup content.

    Accepts two formats:

    1. Raw text:
    Headers: Content-Type: text/plain, X-Client-Name: Antonio Tobar
    Body: Raw markup content

    2. JSON:
    { "markup_content": "...", "client_name": "Antonio Tobar" }
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

        print(f"Generating Fitness Offer PDF for {client_name}...")
        pdf_buffer = generate_offer_pdf(markup_content, client_name)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{client_name}_Fitness_Offer.pdf'
        )

    except Exception as e:
        print(f"Error generating Fitness Offer PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/generate-onboarding', methods=['POST'])
def generate_onboarding():
    """
    Generate branded fitness onboarding PDF from custom markup content.

    Accepts two formats:

    1. Raw text (recommended — matches Make.com HTTP module setup):
    Headers:
      Content-Type: text/plain
      X-Client-Name: Steven Almeida
    Body: Raw markup content (output of Module 2)

    2. JSON:
    {
        "markup_content": "...",
        "client_name": "Steven Almeida"
    }

    Uses onboarding_pdf_generator.py — purpose-built renderer with:
      - Gold rule header on content pages (page 2+)
      - BOX_RED: strong CTA box with white text
      - BOX_PREP: preparation list with thin ruled item separators
      - STEP tag: two-part step renderer (title | body)
      - Larger cover name (18pt vs 16pt in offer generator)
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

        print(f"Generating Onboarding PDF for {client_name}...")
        pdf_buffer = generate_onboarding_pdf(markup_content, client_name)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{client_name}_Onboarding.pdf'
        )

    except Exception as e:
        print(f"Error generating Onboarding PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
