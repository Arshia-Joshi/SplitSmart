import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
gemi_key=os.getenv("gemini_api_key")
genai.configure()

# Use Gemini Flash model
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")

response = model.generate_content("""
Raw OCR Text Lines:
- D
- PORTRONI
- Chitale
- BANDHU LONGE WAS
- Samant And Company
- Tax Invoice.........
- Ravel, Pune Sector 29 Plot No 87 Opposite
- Unity Namk Pradhikaran, Pune. Ph:
- 8177993864
- GSTIN: 27AAKHN7860D1ZX
- Date: 20-07-25 06:44 PM Bill No INA-26970
- HSN
- Item (3)
- Qty
- Rate
- GST %
- Amount
- Nachani Ladoo
- 21069099
- 0.500 KG
- 5.00%
- 420.00
- 210.00
- 21069099
- Chakli Sticks 200 g
- 1.000 No
- 80.00
- 12.00%
- 80.00
- 21069099
- Kaju Katli (Mini Pack) 80g
- 1.000 No
- 99.00
- 5.00%
- 99.00
- ......... GST Break up Details.........
- Total CGST
- Total GST
- Total SGST
- 11.65
- 23.3
- 11 65
- Total:
- { 389.00
- We herely certify that food/foods mentioned in this
- invoice is/are warrauted

 Extract **only the food items and their prices**. Ignore total, taxes, and extra info.
Return as a list like:
- Item Name — Price
""")

print(response.text)
