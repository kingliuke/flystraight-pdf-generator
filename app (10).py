"""
Fly Straight PDF Generator - Flask API
Receives markup/markdown content, generates branded PDFs

Routes:
  POST /generate-pdf        → Precision Fuel Protocol
  POST /generate-checkin    → Weekly Check-In document
  POST /generate-offer      → Fitness Offer document
  POST /generate-onboarding → Fitness Onboarding document
  POST /generate-training   → Precision Training Protocol (new)
"""

from flask import Flask, request, jsonify, send_file
import os
import io
from pdf_generator import generate_fuel_protocol_pdf
from checkin_pdf_generator import generate_checkin_pdf
from offer_pdf_generator import generate_offer_pdf
from onboarding_pdf_generator import generate_onboarding_pdf
from training_pdf_generator import generate_training_pdf

app = Flask(__name__)


@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "service": "Fly Straight PDF Generator",
        "version": "4.0",
        "endpoints": {
            "fuel_protocol":      "POST /generate-pdf",
            "weekly_checkin":     "POST /generate-checkin",
            "fitness_offer":      "POST /generate-offer",
            "onboarding":         "POST /generate-onboarding",
            "training_protocol":  "POST /generate-training",
        }
    })


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Generate branded Precision Fuel Protocol PDF from markup content.

    Accepts two formats:

    1. Raw text:
    Headers: Content-Type: text/plain, X-Client-Name: Javier
    Body: Raw markup text

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

        print(f"=== FUEL PROTOCOL DEBUG ===")
        print(f"Client: {client_name}")
        print(f"Content length: {len(markdown_content)} chars")
        print(f"Contains COVER_BLOCK: {'[COVER_BLOCK]' in markdown_content}")
        print(f"Contains APPENDIX_START: {'[APPENDIX_START]' in markdown_content}")
        print(f"=== END DEBUG ===")

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


@app.route('/generate-training', methods=['POST'])
def generate_training():
    """
    Generate branded Precision Training Protocol PDF from markup content.

    This route receives the concatenated output of TP1 through TP6 as a single
    markup string. Make.com concatenates the six module outputs before sending.

    Accepts two formats:

    1. Raw text (recommended — matches Make.com HTTP module setup):
    Headers:
      Content-Type: text/plain
      X-Client-Name: Agostino DiRienzo
      X-Header-Label: PRECISION TRAINING PROTOCOL    (optional — defaults to this value)
    Body: Concatenated TP1-TP6 markup

    2. JSON:
    {
        "markup_content": "...",
        "client_name": "Agostino DiRienzo",
        "header_label": "PRECISION TRAINING PROTOCOL"  (optional)
    }
    """
    try:
        content_type = request.headers.get('Content-Type', '')

        if 'text/plain' in content_type:
            markup_content = request.get_data(as_text=True)
            client_name  = request.headers.get('X-Client-Name', 'Client')
            header_label = request.headers.get(
                'X-Header-Label', 'PRECISION TRAINING PROTOCOL')
        elif request.is_json or 'application/json' in content_type:
            data = request.get_json()
            markup_content = data.get('markup_content')
            client_name  = data.get('client_name', 'Client')
            header_label = data.get('header_label', 'PRECISION TRAINING PROTOCOL')
        else:
            return jsonify({
                "error": "Unsupported Content-Type. Use 'text/plain' or 'application/json'"
            }), 415

        if not markup_content:
            return jsonify({"error": "No content provided"}), 400

        print(f"=== TRAINING PROTOCOL DEBUG ===")
        print(f"Client: {client_name}")
        print(f"Content length: {len(markup_content)} chars")
        print(f"Contains COVER_BLOCK: {'[COVER_BLOCK]' in markup_content}")
        print(f"Contains EXERCISE_BLOCK: {'[EXERCISE_BLOCK]' in markup_content}")
        print(f"Contains RECOVERY_VARIANT: {'[RECOVERY_VARIANT]' in markup_content}")
        print(f"=== END DEBUG ===")

        print(f"Generating Training Protocol PDF for {client_name}...")
        pdf_buffer = generate_training_pdf(
            markup_content, client_name, header_label)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{client_name}_Precision_Training_Protocol.pdf'
        )

    except Exception as e:
        print(f"Error generating Training Protocol PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
