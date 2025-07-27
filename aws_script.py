import boto3
import os
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv()


genai.configure(api_key=os.getenv("gemini_api_key"))
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
You are given raw OCR text from a restaurant bill. Your task is to extract structured billing information.

OCR Text:
{" ".join(lines)}

Extract the following from this bill:
1. All food items with their final price. Ignore rate/qty/unit prices.
2. All tax details such as SGST, CGST, VAT, Service Tax, service charges etc., along with their percentages if available and total amounts.
3. Subtotal or Gross Total (as labeled in the bill).
4. Final bill total (as labeled: Net Amount / Total / Bill Amount).
Do not calculate the total at the end yourself, extract what is given only.

"""

 
    llm_response = model.generate_content(prompt)
    return llm_response.text


if __name__ == "__main__":
    image_path = "data/receipts/bill6.jpg"
    output = extract_text_from_bill(image_path)
    print(output)
