import boto3
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

# IMPORTANT: Ensure your .env file is correctly formatted:
# Example:
# GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE_NO_SPACES
# AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID_NO_SPACES
# AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY_NO_SPACES
# AWS_REGION=ap-south-1

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

Ensure the output is valid JSON. DO NOT wrap the JSON in markdown backticks (```json). Just provide the raw JSON object. Example format:
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
        parsed_data = json.loads(json_string)
        
        # --- Post-processing to ensure numbers are floats ---
        if 'items' in parsed_data and isinstance(parsed_data['items'], list):
            for item in parsed_data['items']:
                if 'price' in item:
                    try:
                        item['price'] = float(item['price'])
                    except (ValueError, TypeError):
                        item['price'] = 0.0

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
        # --- END Post-processing for floats ---

        # --- NEW STEP: Apply post-processing for duplicates ---
        if 'items' in parsed_data and isinstance(parsed_data['items'], list):
            parsed_data['items'] = post_process_items(parsed_data['items'])
        # --- END NEW STEP ---

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

def post_process_items(items):
    """
    Removes likely duplicate items by prioritizing longer, more descriptive names.
    For example, it keeps "Classic Margherita Pizza" and discards a redundant "Pizza" entry.
    """
    # Create a dictionary to store items, using a simple name as the key
    processed_items = {}
    
    # Sort items by name length (longest first) to ensure we process the most descriptive names first
    sorted_items = sorted(items, key=lambda x: len(x.get('name', '')), reverse=True)
    
    for item in sorted_items:
        name = item.get('name', '').strip().lower()
        if not name:
            continue

        # Check if the simplified name is already a substring of a more descriptive name we've already stored
        is_redundant = False
        for key in processed_items.keys():
            if name in key:
                is_redundant = True
                break
        
        # If it's not a redundant entry, add it to our processed list
        if not is_redundant:
            processed_items[name] = item

    # Return the values from the dictionary, which are the unique, most descriptive items
    return list(processed_items.values())


if __name__ == "__main__":
    image_path = "data/receipts/bill1.jpg"
    output = extract_text_from_bill(image_path)
    print(json.dumps(output, indent=4))