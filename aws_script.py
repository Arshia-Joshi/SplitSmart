import boto3
import os
from dotenv import load_dotenv
from vertexai.language_models import TextGenerationModel
import vertexai

load_dotenv()

# Init Vertex AI
vertexai.init(project=os.getenv("GOOGLE_PROJECT_ID"), location=os.getenv("GOOGLE_LOCATION"))
model = TextGenerationModel.from_pretrained("text-bison")

# Init AWS Rekognition
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
Output format (strict):
- FLAVOURED MOJITO — ₹330.00
...
- SGST 2.5% — ₹32.00
...
- Sub Total — ₹2580.00
- Total — ₹3280.00

If any value is missing, skip it.
"""

    llm_response = model.predict(prompt, temperature=0.2, max_output_tokens=1024)
    return llm_response.text

if __name__ == "__main__":
    image_path = "data/receipts/bill6.jpg"
    output = extract_text_from_bill(image_path)
    print(output)
