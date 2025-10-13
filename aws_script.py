import os
from dotenv import load_dotenv
import json

load_dotenv()

def extract_text_from_bill(image_path):
    """
    Simplified version for testing login/signup without Google AI dependencies
    """
    print(f"📸 Processing image: {image_path}")
    
    # Return mock data for testing
    mock_data = {
        'restaurant_name': 'Test Restaurant',
        'items': [
            {'name': 'Pizza', 'price': 12.50},
            {'name': 'Burger', 'price': 8.75},
            {'name': 'Fries', 'price': 4.25},
            {'name': 'Coke', 'price': 2.50}
        ],
        'taxes': [
            {'type': 'GST', 'amount': 2.80, 'percentage': 10.0},
            {'type': 'Service Charge', 'amount': 1.40, 'percentage': 5.0}
        ],
        'subtotal': 28.00,
        'total': 32.20
    }
    
    print("✅ Using mock data for testing")
    return mock_data

if __name__ == "__main__":
    # Test function
    result = extract_text_from_bill("test.jpg")
    print(json.dumps(result, indent=2))