import sendgrid
import os
import re
import logging
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def send_email(to_email, subject, content):
    """
    Simple function to send an email using SendGrid
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        content (str): Email content (plain text)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get API key from environment
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            logger.error("SENDGRID_API_KEY not found in environment variables")
            return False
            
        # Get sender email from environment
        from_email_address = os.getenv('SENDGRID_VERIFIED_SENDER', 'your-verified-email@example.com')
        
        # Create email
        from_email = Email(from_email_address)
        to_email = To(to_email)
        content = Content("text/plain", content)
        mail = Mail(from_email, to_email, subject, content)
        
        # Send email
        logger.info(f"Sending email to {to_email}")
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        response = sg.client.mail.send.post(request_body=mail.get())
        
        # Check response
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Email sent successfully: {response.status_code}")
            return True
        else:
            logger.error(f"Failed to send email. Status code: {response.status_code}")
            return False
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


# If running this file directly, run a simple test
if __name__ == "__main__":
    print("Running SendGrid mailer test with automatic reminder...")
    
    
    # Create a fake call transcript for testing
    fake_transcript = """
    AI: Hello, this is Conversa AI calling on behalf of Tech Solutions. Am I speaking with John?
    Customer: Yes, this is John.
    AI: Great! I'm calling to discuss how our AI-powered analytics platform could help improve your company's data processing efficiency. Would you be interested in learning more?
    Customer: Sure, I've been looking for solutions to streamline our data analysis.
    AI: Excellent! Our platform has helped similar companies reduce processing time by 40% and increase accuracy by 25%. Would you be available for a quick demo next week?
    Customer: That sounds promising. Yes, I could make time for a demo.
    AI: Perfect! I'll have our team reach out to schedule. Do you have any specific questions I can address now?
    Customer: What about integration with our existing systems?
    AI: Great question. Our platform is designed with flexible APIs that connect with most major systems. We can discuss your specific setup during the demo.
    Customer: Sounds good, looking forward to it.
    """
    
    # Test email with the fake transcript
    test_email = "l227530@lhr.nu.edu.pk"  # Replace with your email
    test_subject = "Follow-up from your Conversa Conversation"
    
    send_email(test_email,test_subject,fake_transcript)
    