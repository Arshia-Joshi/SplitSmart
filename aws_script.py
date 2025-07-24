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

def extract_items_with_prices(text_lines):
    item_price_dict = {}
    i = 0

    while i < len(text_lines):
        line = text_lines[i].strip()

  
        if (
            re.search(r'[a-zA-Z]', line) and
            not any(x in line.lower() for x in ['gst', 'rate', 'qty', 'amount', 'total', 'invoice', 'date', 'bill', 'hsn']) and
            not re.match(r'^\d+(\.\d+)?\s*(kg|no|g|pcs)?$', line.lower())
        ):
            item_name = line
            price = None

           
            for j in range(1, 5):
                if i + j < len(text_lines):
                    next_line = text_lines[i + j].strip()

                    
                    if (
                        re.search(r'[a-zA-Z]', next_line) and
                        not any(x in next_line.lower() for x in ['gst', 'rate', 'qty', 'amount', 'total', 'invoice', 'date', 'bill', 'hsn']) and
                        not re.match(r'^\d+(\.\d+)?\s*(kg|no|g|pcs)?$', next_line.lower())
                    ):
                        break

                    
                    if re.match(r'^\d+(\.\d{1,2})?$', next_line):
                        price_val = float(next_line)
                        if 0 < price_val < 1000:
                            price = price_val  
            if price is not None:
                item_price_dict[item_name] = price

            i += j  
        else:
            i += 1

    return item_price_dict



def extract_text_from_bill(image_path):
    with open(image_path, 'rb') as img_file:
        img_bytes = img_file.read()

    response = rekognition.detect_text(Image={'Bytes': img_bytes})

    lines = []
    print(f"\nFile: {image_path}")
    print("\nRaw OCR Text Lines:")

    for item in response['TextDetections']:
        if item['Type'] == 'LINE':
            line = item['DetectedText']
            print(f"- {line}")
            lines.append(line)

  
    items = extract_items_with_prices(lines)

    print("\nExtracted Items with Prices:")
    for item, price in items.items():
        print(f"- {item}: ₹{price}")


image_path = "data/receipts/bill11.jpg"
extract_text_from_bill(image_path)
