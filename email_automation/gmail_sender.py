import os
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class FaithAgencyEmailer:
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
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
                    print("🔄 Refreshed existing credentials")
                except Exception as e:
                    print(f"⚠️ Error refreshing token: {e}")
                    # Delete the token file and re-authenticate
                    if os.path.exists(self.token_file):
                        os.remove(self.token_file)
                    creds = None
            
            if not creds:
                print("🔐 Starting new authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=8080)

                print("✅ Authentication completed!")
            
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            print("✅ Gmail API service ready!")
        except HttpError as error:
            print(f"❌ Gmail service creation failed: {error}")
            raise
    
    def create_faith_agency_email(self, to_email, caller_name="", department="", inquiry="", caller_phone=""):
        """Create Faith Agency follow-up email"""
        
        # Email subject
        subject = f"Thank you for contacting Faith Agency - {department or 'General Inquiry'}"
        
        # HTML Email Body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Faith Agency - Thank You</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 0;">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: bold;">Faith Agency</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Where faith, creativity, and technology come together</p>
                </div>
                
                <!-- Main Content -->
                <div style="padding: 40px 30px;">
                    <h2 style="color: #333; margin-bottom: 20px;">Thank you for reaching out!</h2>
                    
                    <p style="color: #555; line-height: 1.6; font-size: 16px;">
                        Dear <strong>{caller_name or 'Valued Customer'}</strong>,
                    </p>
                    
                    <p style="color: #555; line-height: 1.6; font-size: 16px;">
                        We received your inquiry regarding <strong>{department or 'our services'}</strong> and truly appreciate you taking the time to contact us.
                    </p>
                    
                    <!-- Inquiry Details Box -->
                    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 25px 0; border-radius: 0 8px 8px 0;">
                        <h3 style="margin: 0 0 10px 0; color: #333; font-size: 18px;">Your Inquiry:</h3>
                        <p style="margin: 0; color: #555; font-style: italic;">"{inquiry or 'General information request'}"</p>
                        {f'<p style="margin: 10px 0 0 0; color: #777; font-size: 14px;">Contact: {caller_phone}</p>' if caller_phone else ''}
                    </div>
                    
                    <!-- Promise -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 25px 0;">
                        <h3 style="margin: 0 0 10px 0; font-size: 18px;">Our Promise</h3>
                        <p style="margin: 0; font-size: 16px;">We will get back to you within <strong>24 hours</strong></p>
                    </div>
                    
                    <!-- Website Link -->
                    <div style="text-align: center; margin: 30px 0;">
                        <p style="color: #555; margin-bottom: 15px;">In the meantime, explore our work:</p>
                        <a href="http://www.vivabiblia.com" style="display: inline-block; background-color: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; transition: background-color 0.3s;">
                            Visit www.vivabiblia.com
                        </a>
                    </div>
                    
                    <!-- Departments Info -->
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 25px 0;">
                        <h3 style="margin: 0 0 15px 0; color: #333;">Our Departments:</h3>
                        <ul style="margin: 0; padding-left: 20px; color: #555; line-height: 1.8;">
                            <li><strong>VIVA</strong> - Spanish Audio Bible</li>
                            <li><strong>Casting</strong> - Talent & Auditions</li>
                            <li><strong>Press</strong> - Media Relations</li>
                            <li><strong>Support</strong> - Technical Help</li>
                            <li><strong>Sales</strong> - Partnerships</li>
                            <li><strong>Management</strong> - Executive Team</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #333; color: white; padding: 20px 30px; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-weight: bold;">The Faith Agency Team</p>
                    <p style="margin: 0; font-size: 14px; opacity: 0.8;">Faith Agency - Where faith, creativity, and technology come together</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text version (fallback)
        text_body = f"""
        Thank you for contacting Faith Agency!
        
        Dear {caller_name or 'Valued Customer'},
        
        We received your inquiry regarding {department or 'our services'}.
        
        Your inquiry: "{inquiry or 'General information request'}"
        {f'Contact: {caller_phone}' if caller_phone else ''}
        
        Our Promise: We will get back to you within 24 hours.
        
        In the meantime, visit our website: www.vivabiblia.com
        
        Best regards,
        The Faith Agency Team
        
        Faith Agency - Where faith, creativity, and technology come together
        """
        
        return subject, text_body, html_body
    
    def send_email(self, to_email, subject, text_body, html_body):
        """Send an email with both text and HTML versions"""
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['to'] = to_email
            message['subject'] = subject
            
            # Add text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send the email
            sent_message = self.service.users().messages().send(
                userId='me', 
                body={'raw': raw_message}
            ).execute()
            
            print(f"✅ Email sent successfully to {to_email}")
            print(f"📧 Message ID: {sent_message['id']}")
            return sent_message['id']
            
        except HttpError as error:
            print(f"❌ Gmail API error: {error}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error sending email: {e}")
            return None
    
    def send_faith_agency_followup(self, to_email, caller_name="", department="", inquiry="", caller_phone=""):
        """Send Faith Agency follow-up email to customer"""
        subject, text_body, html_body = self.create_faith_agency_email(
            to_email, caller_name, department, inquiry, caller_phone
        )
        
        return self.send_email(to_email, subject, text_body, html_body)


def email_system():
    """Test the email system with a sample email"""
    try:
        print("🚀 Initializing Faith Agency Email System...")
        emailer = FaithAgencyEmailer()
        
        # Test email (replace with a real email for testing)
        test_email = "l227530@lhr.nu.edu.pk"  # ⚠️ Replace with your email for testing
        
        print(f"📧 Sending test email to {test_email}...")
        result = emailer.send_faith_agency_followup(
            to_email=test_email,
            caller_name="John Doe",
            department="VIVA Audio Bible",
            inquiry="I'm interested in learning more about the Spanish Audio Bible project",
            caller_phone="+1234567890"
        )
        
        if result:
            print("✅ Email system test successful!")
            print("🎉 Faith Agency email automation is ready!")
        else:
            print("❌ Email system test failed!")
            
    except Exception as e:
        print(f"❌ Email system error: {e}")


if __name__ == "__main__":
    print("Faith Agency Email Automation System")
    print("=" * 40)
    email_system()