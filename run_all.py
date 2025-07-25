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


def extract_text_from_image(image_path):
    with open(image_path, 'rb') as img_file:
        img_bytes = img_file.read()

    response = rekognition.detect_text(Image={'Bytes': img_bytes})
    print ("esponse",response)
    print(f"\n File: {image_path}")
    print("Detected Text Lines:")

    for item in response['TextDetections']:
        if item['Type'] == 'LINE':
            print(f"  - {item['DetectedText']} (Confidence: {item['Confidence']:.2f}%)")

def process_all_receipts(folder_path):
    supported_ext = ('.jpg', '.jpeg', '.png','webp')

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_ext):
            image_path = os.path.join(folder_path, filename)
            extract_text_from_image(image_path)

process_all_receipts("data/receipts")
