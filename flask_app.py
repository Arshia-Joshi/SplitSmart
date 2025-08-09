from flask import Flask, request, jsonify,render_template
from twilio.rest import Client
from dotenv import load_dotenv
import os
from aws_script import extract_text_from_bill

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to_number, message):
    """Send a WhatsApp message via Twilio"""
    if not to_number or not to_number.startswith("+"):
        print(f"Invalid phone number: {to_number}")
        return
    try:
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=f"whatsapp:{to_number}"
        )
        print(f"✅ WhatsApp message sent to {to_number}")
    except Exception as e:
        print(f"❌ Error sending WhatsApp message to {to_number}: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/split_bill', methods=['POST'])
def split_bill():
    """
    Request format:
    {
        "image_path": "path/to/bill.jpg",
        "people": [
            {"name": "Alice", "phone": "+911234567890"},
            {"name": "Bob", "phone": "+919876543210"}
        ]
    }
    """
    try:
        data = request.json
        image_path = data.get("image_path")
        people = data.get("people")

        if not image_path or not people:
            return jsonify({"error": "Missing image_path or people"}), 400

        # Extract bill data from AWS + Gemini
        extracted_data = extract_text_from_bill(image_path)

        # ⚠️ FIX 1: Add a check for extraction errors
        if "error" in extracted_data.get("restaurant_name", "").lower():
            return jsonify({"error": "Failed to extract bill data from the image. Please try again with a clearer image."}), 500

        num_people = len(people)
        split_amounts = {person["name"]: 0.0 for person in people}

        # Step 1: Calculate each person's share of the items (subtotal)
        for item in extracted_data.get("items", []):
            item_price = item.get("price", 0.0)
            eaters = item.get("eaten_by", [])
            
            if eaters:
                share_per_eater = item_price / len(eaters)
                for eater in eaters:
                    if eater in split_amounts:
                        split_amounts[eater] += share_per_eater
            else:
                # If "eaten_by" is empty, split item equally among all people
                share_per_person = item_price / num_people
                for person in people:
                    split_amounts[person["name"]] += share_per_person

        # Step 2: Calculate and distribute share of taxes and other charges
        total_taxes = sum(tax.get("amount", 0.0) for tax in extracted_data.get("taxes", []))
        subtotal_from_items = sum(split_amounts.values())

        if total_taxes > 0 and subtotal_from_items > 0:
            for name, subtotal_share in split_amounts.items():
                tax_share = (subtotal_share / subtotal_from_items) * total_taxes
                split_amounts[name] += tax_share
        elif total_taxes > 0: # Fallback: if subtotal is 0, split taxes equally
            tax_per_person = total_taxes / num_people
            for name in split_amounts:
                split_amounts[name] += tax_per_person

        # Step 3: Send WhatsApp messages with detailed breakdown
        for person in people:
            name = person["name"]
            phone = person["phone"]
            total_owed = round(split_amounts[name], 2)

            # Build a personalized item breakdown for the message
            person_items_breakdown = []
            person_subtotal_share = 0.0
            
            for item in extracted_data.get("items", []):
                item_price = item.get("price", 0.0)
                eaters = item.get("eaten_by", [])
                
                if name in eaters:
                    share = round(item_price / len(eaters), 2)
                    person_items_breakdown.append(f"• {item.get('name', 'N/A')}: ₹{share}")
                    person_subtotal_share += share
                elif not eaters:
                    share = round(item_price / num_people, 2)
                    person_items_breakdown.append(f"• {item.get('name', 'N/A')} (shared): ₹{share}")
                    person_subtotal_share += share
            
            breakdown_text = "\n".join(person_items_breakdown)
            
            # Calculate person's proportional tax share for the message
            tax_share_amount = 0.0
            if subtotal_from_items > 0:
                tax_share_amount = round((person_subtotal_share / subtotal_from_items) * total_taxes, 2)
            else:
                tax_share_amount = round(total_taxes / num_people, 2)

            message = (
                f"Hi {name},\n"
                f"Here's your bill breakdown from {extracted_data.get('restaurant_name', 'your recent meal')}:\n\n"
                f"**Items:**\n{breakdown_text}\n"
                f"**Your share of Taxes/Charges:** ₹{tax_share_amount}\n\n"
                f"**Total you owe:** ₹{total_owed}\n"
                f"Thanks for using SplitSmart! 😊"
            )

            send_whatsapp_message(phone, message)

        return jsonify({
            "status": "success",
            "split_amounts": {k: round(v, 2) for k, v in split_amounts.items()}
        })

    except Exception as e:
        print(f"An error occurred in the Flask route: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)