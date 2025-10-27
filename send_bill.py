import smtplib
import ssl
from email.message import EmailMessage



SENDER_EMAIL = "arshiaamoljoshi@gmail.com"  


SENDER_PASSWORD = "oaitjvigcvizmnvk"  

def send_bill_email(friend_name, friend_email, amount, meal_name, payment_to_name):
    """
    Sends a formatted bill-splitting email to a friend.
    """
    
    # === Create the Email Message ===
    msg = EmailMessage()

    # Set the Email Headers
    msg["Subject"] = f"Your Bill for {meal_name}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = friend_email

    # Set the Email Body (Plain Text)
    msg.set_content(
        f"""
        Hi {friend_name},

        This is your share for the {meal_name}.

        Amount to pay: ₹{amount}

        Please send your payment to {payment_to_name}.

        Thanks!
        """
    )

    print(f"Attempting to send email to {friend_name} at {friend_email}...")

    # === Connect to Gmail and Send ===
    try:
        # Create a secure SSL context
        context = ssl.create_default_context()
        
        # Connect to Gmail's SMTP server (smtp.gmail.com) on port 465 (SSL)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            # Log in using your App Password
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            
            # Send the email
            server.send_message(msg)
            
            print(f"Successfully sent email to {friend_name}!")
            
    except Exception as e:
        print(f"\n--- ERROR: Failed to send email to {friend_name} ---")
        print(f"Details: {e}")
        print("Check: 1. Is SENDER_EMAIL correct?  2. Is SENDER_PASSWORD correct (16 letters, no spaces)?")

# ===================================================================
# --- HOW TO USE IT IN YOUR PROJECT ---
# ===================================================================

# 1. Define your friends and their bill details
friend_list = [
    {"name": "Arshia", "email": "arshia.joshi23@pccoepune.org", "amount": 150.50},
    {"name": "karu", "email": "varadjrane@gmail.com", "amount": 120.00},
    {"name": "snow", "email": "arshiaamoljoshi@gmail.com", "amount": 150.50}
]

meal_description = "Dinner at BBQ Nation"
your_name = "karu" # The person to be paid

# 2. Loop through your friends and send the email
for person in friend_list:
    send_bill_email(
        friend_name=person["name"],
        friend_email=person["email"],
        amount=person["amount"],
        meal_name=meal_description,
        payment_to_name=your_name
    )
    print("--------------------") # Separator
