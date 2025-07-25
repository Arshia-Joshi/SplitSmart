import boto3
import os
import re
from dotenv import load_dotenv

# Load AWS credentials
load_dotenv()

# Setup Textract client (instead of Rekognition)
textract = boto3.client(
    'textract',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

def extract_items_from_textract(image_path):
    with open(image_path, 'rb') as img_file:
        img_bytes = img_file.read()

    # Use Textract to detect TABLES
    response = textract.analyze_document(
        Document={'Bytes': img_bytes},
        FeatureTypes=['TABLES']
    )

    blocks = response['Blocks']
    block_map = {block['Id']: block for block in blocks}
    table_data = []

    # Extract text from each table cell
    for block in blocks:
        if block['BlockType'] == 'CELL':
            text = ''
            if 'Relationships' in block:
                for rel in block['Relationships']:
                    if rel['Type'] == 'CHILD':
                        for cid in rel['Ids']:
                            word = block_map[cid]
                            if word['BlockType'] == 'WORD':
                                text += word['Text'] + ' '
            table_data.append((block['RowIndex'], block['ColumnIndex'], text.strip()))

    # Organize table into rows and columns
    table = {}
    for row, col, text in table_data:
        table.setdefault(row, {})[col] = text

    # Detect which column is item and which is amount
    header = table.get(1, {})
    col_map = {v.lower(): k for k, v in header.items()}
    
    item_col = None
    amt_col = None

    for key in col_map:
        if 'item' in key:
            item_col = col_map[key]
        elif 'amount' in key or 'amt' in key:
            amt_col = col_map[key]

    if item_col is None or amt_col is None:
        print("❌ Couldn't detect 'Item' or 'Amount' columns.")
        return

    # Extract item-price pairs
    print(f"\n📄 File: {image_path}")
    print("\n🧾 Extracted Items with Prices:")
    for r in range(2, max(table) + 1):
        row = table.get(r, {})
        item = row.get(item_col, '').strip()
        price = row.get(amt_col, '').strip()
        if item and price:
            try:
                price_val = float(re.sub(r'[^\d.]', '', price))
                print(f"- {item}: ₹{price_val}")
            except:
                continue

# Run on bill image
image_path = "data/receipts/bill11.jpg"
extract_items_from_textract(image_path)
