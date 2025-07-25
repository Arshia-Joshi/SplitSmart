import boto3
import os
import re
from dotenv import load_dotenv

load_dotenv()

rekognition = boto3.client(
    'rekognition',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

def extract_items_with_prices(lines):
    items = []
    blacklist = ['total', 'gst', 'tax', 'invoice', 'date', 'amount', 'qty', 'rate', 'sub total', 'fssai', 'thank']

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        line_lower = line.lower()

        if any(bad in line_lower for bad in blacklist):
            i += 1
            continue

        
        if re.search(r'[a-zA-Z]{3,}', line):
            prices = []
            for j in range(1, 4):
                if i + j < len(lines):
                    possible_price = lines[i + j].strip()
                    match = re.match(r'^(\d+(?:\.\d{1,2})?)$', possible_price)
                    if match:
                        price = float(match.group(1))
                        if 5 <= price <= 2000:
                            prices.append(price)
            if prices:
                items.append((line, max(prices)))
                i += j  
            else:
                i += 1
        else:
            i += 1
    return items

def extract_text_from_bill(image_path):
    with open(image_path, 'rb') as img_file:
        img_bytes = img_file.read()

    response = rekognition.detect_text(Image={'Bytes': img_bytes})

    lines = []
    print(f"\nFile: {image_path}")
    print("\nRaw OCR Text Lines:")
    for item in response['TextDetections']:
        if item['Type'] == 'LINE':
            print(f"- {item['DetectedText']}")
            lines.append(item['DetectedText'])

    extracted = extract_items_with_prices(lines)

    print("\nExtracted Items with Prices:")
    if extracted:
        for item, price in extracted:
            print(f"- {item}: ₹{price}")
    else:
        print("❌ No items detected.")

if __name__ == "__main__":
    image_path = "data/receipts/bill2.jpg"  
    extract_text_from_bill(image_path)
