import boto3
import os
from dotenv import load_dotenv


load_dotenv()


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

    print("\n Detected Text Lines:\n")
    for item in response['TextDetections']:
        if item['Type'] == 'LINE':
            print(f"- {item['DetectedText']}")

image_path = "data/receipts/bill11.jpg"
extract_text_from_bill(image_path)
