import os
import json
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

# Gmail API scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class FaithAgencyEmailSender:
    def __init__(self, credentials_file='email_automation/credentials.json', token_file='email_automation/token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.from_email = os.getenv("FROM_EMAIL", "")
        self.authenticate()
    
    def authenticate(self):
        """Authenticate and build Gmail service"""
        creds = None
        
        # Check if token.json exists (stored credentials)
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    # Delete the token file and re-authenticate
                    if os.path.exists(self.token_file):
                        os.remove(self.token_file)
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    print(f"❌ Credentials file not found: {self.credentials_file}")
                    print("Please ensure you have downloaded the credentials.json file from Google Cloud Console")
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            print("✅ Gmail authentication successful!")
            return True
        except HttpError as error:
            print(f"❌ Gmail authentication failed: {error}")
            return False
    
    def create_faith_agency_message(self, to_email, caller_name="", department=""):
        """Create Faith Agency follow-up email message"""
        subject = "Thank you for contacting Faith Agency"
        
        # Simple professional text content
        body_text = f"""Dear {caller_name or 'Valued Customer'},

Thank you for contacting Faith Agency! We appreciate your interest in our services.

{f'Your inquiry was directed to our {department} department.' if department else 'We have received your inquiry.'}

We will get back to you within 24 hours.

Please visit our website for more information: www.vivabiblia.com

Best regards,
The Faith Agency Team

---
Faith Agency - Where faith, creativity, and technology come together."""
        
        # Create simple text message
        message = MIMEText(body_text, 'plain')
        message['to'] = to_email
        message['from'] = self.from_email
        message['subject'] = subject
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}
    
    def send_faith_agency_email(self, to_email, caller_name="", department=""):
        """Send Faith Agency follow-up email"""
        try:
            if not self.service:
                print("❌ Gmail service not authenticated")
                return None
                
            message = self.create_faith_agency_message(to_email, caller_name, department)
            sent_message = self.service.users().messages().send(
                userId='me', 
                body=message
            ).execute()
            
            print(f"✅ Faith Agency email sent successfully to {to_email}")
            return sent_message['id']
            
        except HttpError as error:
            print(f"❌ Error sending email: {error}")
            return None
        except Exception as e:
            print(f"❌ Unexpected email error: {e}")
            return None


def send_faith_agency_email(to_email, caller_name="", department=""):
    """Standalone function to send Faith Agency email"""
    try:
        email_sender = FaithAgencyEmailSender()
        return email_sender.send_faith_agency_email(to_email, caller_name, department)
    except Exception as e:
        print(f"❌ Error initializing email sender: {e}")
        return None


def test_email_system():
    """Test the email system"""
    try:
        print("🧪 Testing Faith Agency email system...")
        
        # Test email - replace with a real email for testing
        test_result = send_faith_agency_email(
            to_email="l227530@lhr.nu.edu.pk",  # Replace with real email
            caller_name="Muhammad Shahzad",
            department="Sales"
        )
        
        if test_result:
            print("✅ Email system test successful!")
        else:
            print("❌ Email system test failed!")
            
    except Exception as e:
        print(f"❌ Email system error: {e}")


if __name__ == "__main__":
    test_email_system()