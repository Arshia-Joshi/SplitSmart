import boto3
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()
gemi_key=os.getenv("gemini_api_key")
genai.configure()

# Use Gemini Flash model
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
    print(f"\nFile: {image_path}")
    print("\nRaw OCR Text Lines:")
    for item in response['TextDetections']:
        if item['Type'] == 'LINE':
            #print(f"- {item['DetectedText']}")
            lines.append(item['DetectedText'])
    print(" ".join(lines))
    response = model.generate_content(f"""{" ".join(lines)}\n Extract **only the food items and their final amount even though it is expensive**. Ignore total, taxes,rate and extra info.
        Return as a list like:
- Item Name — Price""")

    print(response.text)

if __name__ == "__main__":
    image_path = "data/receipts/bill11.jpg"  
    extract_text_from_bill(image_path)
