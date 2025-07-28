import boto3
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json # <--- Make sure this is imported

load_dotenv()

# IMPORTANT: Ensure your .env file is correctly formatted:
# Example:
# GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE_NO_SPACES
# AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID_NO_SPACES
# AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY_NO_SPACES
# AWS_REGION=ap-south-1
# No spaces around '=', no comments on the same line as key-value pairs.

genai.configure(api_key=os.getenv("GEMINI_API_KEY")) # Use GEMINI_API_KEY for consistency
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")

rekognition = boto3.client(
    'rekognition',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

def extract_text_from_bill(image_path):
    with open(image_path, 'rb') as img_file:
        img_bytes = img_file.read()

    response = rekognition.detect_text(Image={'Bytes': img_bytes})

    lines = []
    for item in response['TextDetections']:
        if item['Type'] == 'LINE':
            lines.append(item['DetectedText'])

    prompt = f"""
You are given raw OCR text from a restaurant bill. Your task is to extract structured billing information in JSON format.

OCR Text:
{" ".join(lines)}

Extract the following from this bill:
1.  A "restaurant_name" (string, e.g., "The Grand Cafe"). If not found, use "Unknown Restaurant".
2.  An "items" array, where each object has:
    * "name" (string, the food item's description)
    * "price" (float, the final price of the item). Ignore rate/qty/unit prices.
3.  A "taxes" array, where each object has:
    * "type" (string, e.g., "SGST", "Service Charge", "VAT")
    * "amount" (float, the total amount for that tax)
    * "percentage" (float, optional, the percentage if available, e.g., 5.0 for 5%). If not available, use null.
4.  A "subtotal" (float, the subtotal or gross total as labeled in the bill). If not found, use null.
5.  A "total" (float, the final bill total (as labeled: Net Amount / Total / Bill Amount) after all taxes and charges). If not found, use null.

Do not calculate any totals yourself; extract only the values explicitly given in the bill.
If a category is not found, use an empty array for lists or null for single values.

Ensure the output is valid JSON. **DO NOT wrap the JSON in markdown backticks (```json). Just provide the raw JSON object.** Example format:
{{
    "restaurant_name": "Example Restaurant",
    "items": [
        {{ "name": "Burger", "price": 12.50 }},
        {{ "name": "Fries", "price": 4.00 }}
    ],
    "taxes": [
        {{ "type": "SGST", "amount": 1.20, "percentage": 6.0 }},
        {{ "type": "Service Charge", "amount": 3.00, "percentage": null }}
    ],
    "subtotal": 20.00,
    "total": 24.20
}}
"""

    llm_response = model.generate_content(prompt)
    raw_response_text = llm_response.text

    # --- Strip markdown code block wrappers ---
    if raw_response_text.startswith("```json") and raw_response_text.endswith("```"):
        json_string = raw_response_text[len("```json"):-len("```")].strip()
    else:
        json_string = raw_response_text.strip()
    
    try:
        parsed_data = json.loads(json_string) # Use json_string here
        
        # --- Post-processing to ensure numbers are floats ---
        if 'items' in parsed_data and isinstance(parsed_data['items'], list):
            for item in parsed_data['items']:
                if 'price' in item:
                    try:
                        item['price'] = float(item['price'])
                    except (ValueError, TypeError):
                        item['price'] = 0.0 # Default to 0 if conversion fails

        if 'taxes' in parsed_data and isinstance(parsed_data['taxes'], list):
            for tax in parsed_data['taxes']:
                if 'amount' in tax:
                    try:
                        tax['amount'] = float(tax['amount'])
                    except (ValueError, TypeError):
                        tax['amount'] = 0.0
                if 'percentage' in tax and tax['percentage'] is not None:
                    try:
                        tax['percentage'] = float(tax['percentage'])
                    except (ValueError, TypeError):
                        tax['percentage'] = None

        for key in ['subtotal', 'total']:
            if key in parsed_data and parsed_data[key] is not None:
                try:
                    parsed_data[key] = float(parsed_data[key])
                except (ValueError, TypeError):
                    parsed_data[key] = None
        # --- END Post-processing ---
        
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini: {e}")
        print(f"Gemini raw response: {raw_response_text}") # Print raw text for debugging
        return {
            'restaurant_name': 'Extraction Error',
            'items': [],
            'taxes': [],
            'subtotal': None,
            'total': None
        }


if __name__ == "__main__":
    image_path = "data/receipts/bill1.jpg" # Ensure this path is correct for testing
    output = extract_text_from_bill(image_path)
    print(json.dumps(output, indent=4)) # Print as pretty JSON for testing