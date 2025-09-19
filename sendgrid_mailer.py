import os
import logging
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def send_email(to_email: str, subject: str, content: str) -> bool:
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
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            logger.error("SENDGRID_API_KEY not found in environment variables")
            return False

        # Get sender email from environment
        from_email_address = os.getenv(
            "SENDGRID_VERIFIED_SENDER", "contact@faithagencyllc.com"
        )

        # Build email
        from_email = Email(from_email_address)
        to_email_obj = To(to_email)
        content_obj = Content("text/plain", content)
        mail = Mail(from_email, to_email_obj, subject, content_obj)

        # Send email
        logger.info(f"Sending email to {to_email}")
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        response = sg.client.mail.send.post(request_body=mail.get())

        if 200 <= response.status_code < 300:
            logger.info(f"✅ Email sent successfully: {response.status_code}")
            return True
        else:
            logger.error(f"❌ Failed to send email. Status: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Error sending email: {str(e)}")
        return False


# Example usage
if __name__ == "__main__":
    test_email = "mshahzadwaris92@gmail.com"
    subject = "Test Email"
    body = "Hello! This is a test email from SendGrid."

    if send_email(test_email, subject, body):
        print("✅ Test email sent successfully!")
    else:
        print("❌ Failed to send test email.")
