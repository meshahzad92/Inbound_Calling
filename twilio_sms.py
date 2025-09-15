# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_sms(to_number, message_body,from_number):
    """
    Send SMS message using Twilio API
    
    Args:
        to_number (str): The recipient's phone number in E.164 format (e.g., +1XXXXXXXXXX)
        message_body (str): The content of the SMS message
        
    Returns:
        str: The SID of the sent message if successful
    """
    try:
        # Find your Account SID and Auth Token at twilio.com/console
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        #from_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not account_sid or not auth_token or not from_number:
            print("Error: Twilio credentials not found in environment variables")
            return None
            
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_number,
        )

        print(f"SMS sent successfully to {to_number}")
        return message.sid
        
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return None

# # Example usage when script is run directly
# if __name__ == "__main__":
#     # Test the function
#     recipient = "+18639468602"  # Replace with test number
#     test_message = "Thanks for checking out Conversa—your system for turning more leads into funded deals.\nClick below to schedule an appointment and see how Conversa can work for you.\n\nhttps://calendly.com/dromel/30min"
#     send_sms(recipient, test_message)