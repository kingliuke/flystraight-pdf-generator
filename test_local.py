"""
Test script for PDF generator
Run this locally to verify everything works before deploying
"""

from pdf_generator import generate_fuel_protocol_pdf

# Sample markdown content
test_markdown = """
# PRECISION FUEL PROTOCOL

**Javier**

You know what works. You have done this before.

## FLY STRAIGHT MEMBER PROFILE

| Field | Value |
|-------|-------|
| Age | 47 years old |
| Current Weight | 283 lbs |
| Goal Weight | 175 lbs |

## YOUR NUMBERS

Your TDEE is 3,200 calories per day.

### Why 2,400 Calories

This is aggressive but sustainable.

**CRITICAL:** Do not skip meals.

- Meal 1: 6:00 AM
- Meal 2: 12:00 PM
- Meal 3: 5:30 PM
- Meal 4: 8:00 PM
"""

if __name__ == "__main__":
    print("Generating test PDF...")
    
    try:
        pdf_buffer = generate_fuel_protocol_pdf(test_markdown, "TestClient")
        
        # Save to file
        with open("test_output.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        
        print("✅ SUCCESS! PDF created: test_output.pdf")
        print("Open it to verify branding looks correct")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
