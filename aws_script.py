import boto3
import os
from dotenv import load_dotenv
import re
import json

load_dotenv()

rekognition = boto3.client(
    'rekognition',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

def extract_text_from_bill(image_path):
    """
    UNIVERSAL bill extractor - works with ANY bill format
    """
    print(f"📸 Processing image: {image_path}")
    
    try:
        with open(image_path, 'rb') as img_file:
            img_bytes = img_file.read()

        response = rekognition.detect_text(Image={'Bytes': img_bytes})

        # Extract all text lines
        lines = []
        for item in response['TextDetections']:
            if item['Type'] == 'LINE':
                lines.append(item['DetectedText'])

        print("\n📝 Detected Text Lines:")
        for i, line in enumerate(lines):
            print(f"  {i+1:2d}. {line}")

        # UNIVERSAL extraction that works with any format
        items = extract_items_universal(lines)
        totals = extract_totals_universal(lines)
        restaurant_name = extract_restaurant_name_universal(lines)
        
        print(f"\n✅ Extracted {len(items)} items:")
        for item in items:
            print(f"   - {item['name']}: ₹{item['price']}")
        
        print(f"💰 Totals - Subtotal: ₹{totals['subtotal']}, Total: ₹{totals['total']}")

        return {
            'restaurant_name': restaurant_name,
            'items': items,
            'taxes': totals['taxes'],
            'subtotal': totals['subtotal'],
            'total': totals['total']
        }
        
    except Exception as e:
        print(f"❌ Error in extraction: {e}")
        return get_smart_fallback_data(lines)

def extract_items_universal(lines):
    """
    UNIVERSAL item extraction - works with ANY bill format
    """
    items = []
    
    # Method 1: Look for item-price pairs in the entire bill
    items_method1 = extract_item_price_pairs(lines)
    
    # Method 2: Look for items near prices
    items_method2 = extract_items_near_prices(lines)
    
    # Combine results, remove duplicates
    all_items = items_method1 + items_method2
    unique_items = remove_duplicate_items(all_items)
    
    return unique_items

def extract_item_price_pairs(lines):
    """Extract items and prices that appear close to each other"""
    items = []
    
    for i in range(len(lines)):
        current_line = lines[i].strip()
        
        # Skip header lines and totals
        if should_skip_line(current_line):
            continue
            
        # Check if current line has a price
        price = extract_price(current_line)
        if price and 10 <= price <= 2000:
            # Look for item name in previous lines
            item_name = find_item_name_nearby(lines, i)
            if item_name:
                items.append({
                    'name': clean_item_name(item_name),
                    'price': price
                })
    
    return items

def find_item_name_nearby(lines, price_line_index):
    """Find the closest item name near a price"""
    # Look backwards for item name
    for i in range(price_line_index-1, max(0, price_line_index-5), -1):
        line = lines[i].strip()
        if is_likely_item_name(line):
            return line
    
    return None

def is_likely_item_name(line):
    """Check if line is likely an item name"""
    if not line or len(line) < 2:
        return False
    
    # Should contain letters
    if not any(c.isalpha() for c in line):
        return False
    
    # Should not be mostly numbers
    digit_ratio = sum(c.isdigit() for c in line) / len(line)
    if digit_ratio > 0.4:
        return False
    
    # Should not be common header words
    header_words = ['particulars', 'description', 'items', 'qty', 'quantity', 'rate', 'amount', 'city']
    if any(word in line.lower() for word in header_words):
        return False
    
    # Should not be totals or taxes
    total_words = ['total', 'subtotal', 'gst', 'sgst', 'cgst', 'tax', 'vat']
    if any(word in line.lower() for word in total_words):
        return False
    
    return True

def extract_items_near_prices(lines):
    """Extract items that appear near prices in the bill"""
    items = []
    potential_items = []
    prices_found = []
    
    # First pass: collect all potential items and prices
    for i, line in enumerate(lines):
        line_clean = lines[i].strip()
        
        if should_skip_line(line_clean):
            continue
            
        # Collect potential item names
        if is_likely_item_name(line_clean):
            potential_items.append({
                'name': line_clean,
                'line_index': i
            })
        
        # Collect prices
        price = extract_price(line_clean)
        if price and 10 <= price <= 2000:
            prices_found.append({
                'price': price,
                'line_index': i
            })
    
    # Match items with nearby prices
    for price_info in prices_found:
        price_line_index = price_info['line_index']
        price = price_info['price']
        
        # Find the closest item before this price
        closest_item = None
        min_distance = float('inf')
        
        for item_info in potential_items:
            if item_info['line_index'] < price_line_index:
                distance = price_line_index - item_info['line_index']
                if distance < min_distance and distance <= 3:  # Max 3 lines away
                    min_distance = distance
                    closest_item = item_info
        
        if closest_item:
            items.append({
                'name': clean_item_name(closest_item['name']),
                'price': price
            })
            # Remove this item from potential items to avoid reuse
            potential_items = [item for item in potential_items if item['line_index'] != closest_item['line_index']]
    
    return items

def extract_price(line):
    """Extract price from a line"""
    # Multiple price patterns
    patterns = [
        r'(\d{1,4}[.,]\d{2})',  # 123.45
        r'(\d{1,4}[.,]\d{1})',  # 123.4
        r'(\d{1,4})'            # 123
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, line)
        if matches:
            price_str = matches[0].replace(',', '.')
            try:
                price = float(price_str)
                if 5 <= price <= 5000:  # Reasonable price range
                    return price
            except ValueError:
                continue
    
    return None

def clean_item_name(name):
    """Clean item name"""
    if not name:
        return ""
    
    # Remove leading numbers and dots
    name = re.sub(r'^\d+\.?\s*', '', name)
    
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def should_skip_line(line):
    """Check if line should be skipped"""
    if not line or len(line.strip()) < 2:
        return True
        
    line_lower = line.lower()
    
    skip_keywords = [
        'total', 'subtotal', 'tax', 'gst', 'vat', 'service', 'tip',
        'amount', 'cash', 'card', 'change', 'thank', 'visit', 'receipt',
        'bill', 'invoice', 'date', 'time', 'table', 'guest', 'discount',
        'offer', 'gstin', 'hsn', 'sac', 'qty', 'quantity', 'rate', 'net',
        'grand', 'final', 'payable', 'balance', 'steward', 'cover',
        'particulars', 'description', 'items', 'city', 'boy', 'counter',
        'fssai', 'thank you', 'visit again'
    ]
    
    return any(keyword in line_lower for keyword in skip_keywords)

def remove_duplicate_items(items):
    """Remove duplicate items"""
    seen = set()
    unique_items = []
    
    for item in items:
        item_key = f"{item['name'].lower()}_{item['price']}"
        if item_key not in seen:
            seen.add(item_key)
            unique_items.append(item)
    
    return unique_items

def extract_totals_universal(lines):
    """
    UNIVERSAL totals extraction
    """
    totals = {'subtotal': 0, 'total': 0, 'taxes': []}
    
    for i, line in enumerate(lines):
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        # Look for subtotal
        if any(word in line_lower for word in ['sub total', 'subtotal', 'total amount']):
            price = extract_price_from_line_or_next(line_clean, lines, i)
            if price:
                totals['subtotal'] = price
        
        # Look for total
        elif any(word in line_lower for word in ['total', 'grand total', 'final amount', 'bill amount']):
            price = extract_price_from_line_or_next(line_clean, lines, i)
            if price:
                totals['total'] = price
        
        # Look for taxes
        elif any(word in line_lower for word in ['cgst', 'sgst', 'gst']):
            price = extract_price_from_line_or_next(line_clean, lines, i)
            if price:
                tax_type = "CGST" if 'cgst' in line_lower else "SGST" if 'sgst' in line_lower else "GST"
                percentage = extract_tax_percentage(line_clean)
                totals['taxes'].append({
                    'type': tax_type,
                    'amount': price,
                    'percentage': percentage
                })
    
    # If no total found but subtotal exists, calculate total
    if totals['total'] == 0 and totals['subtotal'] > 0:
        tax_total = sum(tax['amount'] for tax in totals['taxes'])
        totals['total'] = totals['subtotal'] + tax_total
    
    return totals

def extract_price_from_line_or_next(line, lines, current_index):
    """Extract price from line or the next line"""
    price = extract_price(line)
    if price:
        return price
    
    # Check next line
    if current_index + 1 < len(lines):
        price = extract_price(lines[current_index + 1])
        if price:
            return price
    
    return 0

def extract_tax_percentage(line):
    """Extract tax percentage from line"""
    percentage_pattern = r'@\s*(\d+[.,]?\d*)%'
    matches = re.findall(percentage_pattern, line)
    if matches:
        try:
            return float(matches[0].replace(',', '.'))
        except ValueError:
            pass
    return None

def extract_restaurant_name_universal(lines):
    """Extract restaurant name from text"""
    for i in range(min(8, len(lines))):
        line = lines[i].strip()
        if (len(line) > 3 and 
            not any(word in line.lower() for word in ['bill', 'invoice', 'receipt', 'tax', 'gstin', 'state', 'date', 'time']) and
            sum(c.isdigit() for c in line) < 5 and
            len(line) < 50):
            return line
    
    return "Restaurant"

def get_smart_fallback_data(lines):
    """Smart fallback that tries to extract some data even when main extraction fails"""
    # Try to at least get the restaurant name and totals
    restaurant_name = extract_restaurant_name_universal(lines)
    totals = extract_totals_universal(lines)
    
    return {
        'restaurant_name': restaurant_name,
        'items': [
            {'name': 'Item 1 - Please edit manually', 'price': 0.0},
            {'name': 'Item 2 - Please edit manually', 'price': 0.0},
            {'name': 'Item 3 - Please edit manually', 'price': 0.0}
        ],
        'taxes': totals.get('taxes', []),
        'subtotal': totals.get('subtotal', 0),
        'total': totals.get('total', 0)
    }

if __name__ == "__main__":
    # Test the function
    image_path = "data/receipts/bill1.jpg"
    result = extract_text_from_bill(image_path)
    print("\n Final Result:")
    print(json.dumps(result, indent=2))