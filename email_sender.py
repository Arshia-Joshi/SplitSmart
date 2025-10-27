import smtplib
import ssl
from email.message import EmailMessage

# --- ADD YOUR EMAIL HERE ---
SENDER_EMAIL = "arshiaamoljoshi@gmail.com"
# --- (But leave the password out) ---


# --- REMOVE 'sender_email' from this line ---
def send_bill_email(sender_password, friend_name, friend_email, amount, meal_name, payment_to_name):
    """
    Connects to the email server and sends a bill notification.
    Returns (True, "Success Message") or (False, "Error Message")
    """
    
    # --- 1. Create the Email Content ---
    subject = f"Bill Split for {meal_name}"
    
    body = f"""
    Hi {friend_name},

    This is a friendly reminder about the {meal_name}.
    You owe {payment_to_name} a total of ₹{amount:.2f}.

    Please pay soon!

    Thanks,
    - {payment_to_name} (via Bill Splitter App)
    """

    # --- 2. Create the EmailMessage object ---
    em = EmailMessage()
    # It will use the SENDER_EMAIL from the top of the file
    em['From'] = f"{payment_to_name} <{SENDER_EMAIL}>" 
    em['To'] = friend_email
    em['Subject'] = subject
    em.set_content(body)

    # --- 3. Send the Email ---
    context = ssl.create_default_context()

    try:
        # Connect to Gmail's server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            # Use the SENDER_EMAIL from the top and the password from the argument
            smtp.login(SENDER_EMAIL, sender_password) 
            smtp.sendmail(SENDER_EMAIL, friend_email, em.as_string())
        
        return (True, f"Email successfully sent to {friend_name} ({friend_email})!")
        
    except Exception as e:
        print(f"Error sending email to {friend_email}: {str(e)}")
        return (False, f"Failed to send email to {friend_name}: {str(e)}")