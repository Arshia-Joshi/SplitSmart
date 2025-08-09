import boto3
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
import re

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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

Extract the following:
1. "restaurant_name" (string). If not found, use "Unknown Restaurant".
2. "items" (array), where each object has:
    * "name" (string)
    * "price" (float, final price of that item)
    * "eaten_by" (array of strings, names of people who ate the item; if unknown, use [])
3. "taxes" (array), where each object has:
    * "type" (string)
    * "amount" (float)
    * "percentage" (float or null)
4. "subtotal" (float or null)
5. "total" (float or null)

If a category is not found, use an empty array for lists or null for single values.
Ensure output is valid JSON, without markdown code fences. Example:
{{
    "restaurant_name": "Example Cafe",
    "items": [
        {{ "name": "Burger", "price": 12.50, "eaten_by": ["Alice", "Bob"] }},
        {{ "name": "Fries", "price": 4.00, "eaten_by": [] }}
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
    raw_response_text = llm_response.text.strip()

    # Use a regex to find the first JSON object in the string
    match = re.search(r'\{.*\}', raw_response_text, re.DOTALL)
    
    if match:
        json_string = match.group(0)
    else:
        print("Error: No JSON object found in Gemini's response.")
        print(f"Gemini raw response: {raw_response_text}")
        return {
            'restaurant_name': 'Extraction Error',
            'items': [],
            'taxes': [],
            'subtotal': None,
            'total': None
        }

    try:
        parsed_data = json.loads(json_string)

        # Type conversion and validation (your original code already did this well)
        if 'items' in parsed_data and isinstance(parsed_data['items'], list):
            for item in parsed_data['items']:
                if 'price' in item:
                    try:
                        item['price'] = float(item['price'])
                    except (ValueError, TypeError):
                        item['price'] = 0.0
                if 'eaten_by' not in item or not isinstance(item['eaten_by'], list):
                    item['eaten_by'] = []

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

        return parsed_data

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini: {e}")
        print(f"Gemini raw response: {raw_response_text}")
        return {
            'restaurant_name': 'Extraction Error',
            'items': [],
            'taxes': [],
            'subtotal': None,
            'total': None
        }
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            'restaurant_name': 'Extraction Error',
            'items': [],
            'taxes': [],
            'subtotal': None,
            'total': None
        }

if __name__ == "__main__":
    test_image = "data/receipts/bill1.jpg"
    output = extract_text_from_bill(test_image)
    print(json.dumps(output, indent=4))