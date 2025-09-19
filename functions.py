import os
import csv
import json
import time
import re
import httpx
import asyncio
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from twilio_sms import send_sms
# from email_automation import send_faith_agency_email  # Commented out - now using SendGrid
from sendgrid_mailer import send_email  # New SendGrid email system
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from google_sheet import save_to_google_sheets
from ultravox_prompt import get_single_flow_prompt

load_dotenv()

# Global variable to store transfer status
transfer_status_cache = {}

def store_transfer_status(call_sid, status):
    """Store transfer status for a call SID"""
    transfer_status_cache[call_sid] = status
    print(f"📝 Stored transfer status for {call_sid}: {status}")

def get_transfer_status(call_sid):
    """Get transfer status for a given call SID"""
    status = transfer_status_cache.get(call_sid, None)
    print(f"🔍 Retrieved transfer status for {call_sid}: {status}")
    return status

# Configuration
ULTRAVOX_API_KEY = os.getenv("ULTRAVOX_API_KEY")
ULTRAVOX_API_URL = 'https://api.ultravox.ai/api/calls'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
MANAGEMENT_REDIRECT_NUMBER = os.getenv("MANAGEMENT_REDIRECT_NUMBER")

# Initialize OpenAI and Twilio clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

async def handle_transfer_background(call_sid, destination_number, transfer_reason):
    """Handle transfer in background without blocking Ultravox response"""
    try:
        print(f"🔄 Background transfer started: {transfer_reason}")
        result = await handle_transfer(call_sid, destination_number)
        print(f"📊 Background transfer result: {result}")
        return result
    except Exception as e:
        print(f"❌ Background transfer error: {e}")
        return {"status": "failed", "message": f"Background transfer error: {str(e)}"}

async def quick_transfer_check(call_sid, destination_number):
    """Quick transfer check with shorter timeout for Ultravox responsiveness"""
    try:
        print(f"⚡ Quick transfer check to {destination_number}...")
        
        # Create a test call to management with shorter timeout
        # Create management call
        management_call = twilio_client.calls.create(
            to=MANAGEMENT_REDIRECT_NUMBER,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            timeout=25,  # Give management 25 seconds to answer
            url="http://demo.twilio.com/docs/voice.xml"  # Simple holding pattern
        )
        
        management_call_sid = management_call.sid
        print(f"📞 Created management call: {management_call_sid}")
        
        # Wait and check management call status
        max_wait_time = 20  # Wait up to 20 seconds minimum
        check_interval = 4  # Check every 4 seconds
        checks = max_wait_time // check_interval  # 5 checks total (at 4s, 8s, 12s, 16s, 20s)
        
        for i in range(checks):
            print(f"⏰ Checking management call status (attempt {i+1}/{checks})...")
            time.sleep(check_interval)
            
            # Get current call status
            call_status = twilio_client.calls(management_call_sid).fetch().status
            print(f"📊 Management call status: {call_status}")
            
            if call_status == "in-progress":
                
                # Management already answered our test call, so we need to bridge
                # the customer call with the existing management call
                try:
                    # Create a conference room to bridge the calls
                    conference_name = f"transfer-{call_sid[-8:]}"
                    
                    # First, put the customer call into the conference
                    customer_twiml = f'''
                    <Response>
                        <Say>One moment please, connecting you now.</Say>
                        <Dial>
                            <Conference waitUrl="" startConferenceOnEnter="true" endConferenceOnExit="true">
                                {conference_name}
                            </Conference>
                        </Dial>
                    </Response>
                    '''
                    
                    # Then, redirect the management call (which is already answered) to the same conference
                    management_twiml = f'''
                    <Response>
                        <Dial>
                            <Conference waitUrl="" startConferenceOnEnter="true" endConferenceOnExit="false">
                                {conference_name}
                            </Conference>
                        </Dial>
                    </Response>
                    '''
                    
                    # Update both calls to join the conference
                    print(f"🔗 Bridging customer call {call_sid} to conference {conference_name}")
                    twilio_client.calls(call_sid).update(twiml=customer_twiml)
                    
                    print(f"🔗 Bridging management call {management_call_sid} to conference {conference_name}")
                    twilio_client.calls(management_call_sid).update(twiml=management_twiml)
                    
                    print(f"✅ Both calls bridged in conference: {conference_name}")
                    return {"status": "success", "message": "Connecting you to management now"}
                    
                except Exception as bridge_error:
                    print(f"❌ Bridge error: {bridge_error}")
                    # If bridge fails, hang up management call and return failure
                    try:
                        twilio_client.calls(management_call_sid).update(status='completed')
                    except:
                        pass
                    return {"status": "failed", "message": "Transfer failed - technical error"}
            
            elif call_status in ["busy", "no-answer", "failed", "canceled", "completed"]:
                print(f"❌ Management not available: {call_status}")
                break
        
        # Clean up test call
        try:
            twilio_client.calls(management_call_sid).update(status='completed')
        except:
            pass
        
        return {"status": "failed", "message": "Management is currently unavailable"}
        
    except Exception as e:
        print(f"❌ Quick transfer error: {e}")
        return {"status": "failed", "message": f"Transfer error: {str(e)}"}

async def handle_transfer(call_sid, destination_number=None):
    """Handle call transfer with failover logic and answer detection"""
    if not destination_number:
        destination_number = MANAGEMENT_REDIRECT_NUMBER
    
    try:
        print(f"🔄 Initiating transfer to {destination_number}...")
        print("⏰ Management has 20 seconds to answer...")
        
        # Create a separate outbound call to management without affecting the customer call
        # This way the customer call stays with Ultravox until we confirm management answers
        management_call = twilio_client.calls.create(
            to=destination_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            timeout=20,  # Ring for 20 seconds  
            url="http://demo.twilio.com/docs/voice.xml"  # Simple holding pattern
        )
        
        management_call_sid = management_call.sid
        print(f"📞 Created management call: {management_call_sid}")
        print(f"📞 Customer call {call_sid} remains with Ultravox during monitoring...")
        
        # Monitor the management call status every 5 seconds for 20 seconds total
        call_status = await monitor_transfer_status(management_call_sid, destination_number)
        
        if call_status == "answered":
            print(f"✅ Management answered - now transferring customer call...")
            # Only now do we transfer the customer to management
            connect_twiml = f'''
            <Response>
                <Dial timeout="60">
                    {destination_number}
                </Dial>
            </Response>
            '''
            twilio_client.calls(call_sid).update(twiml=connect_twiml)
            # End the test call to management since we're making a real connection
            try:
                twilio_client.calls(management_call_sid).update(status='completed')
            except:
                pass
            return {"status": "success", "message": "Transfer successful - management answered"}
        else:
            print(f"❌ Management didn't answer - customer stays with Ultravox")
            # Clean up the management call
            try:
                twilio_client.calls(management_call_sid).update(status='completed')
            except:
                pass
            # Customer call continues with Ultravox (no changes made to it)
            return {"status": "failed", "message": f"Management not available - continuing with assistant"}

    except TwilioRestException as e:
        print(f"❌ Transfer failed: {e}")
        return {"status": "failed", "message": f"Transfer failed: {str(e)}"}
    except Exception as e:
        print(f"❌ Unexpected transfer error: {e}")
        return {"status": "failed", "message": f"Unexpected error: {str(e)}"}

async def monitor_transfer_status(call_sid, destination_number):
    """Monitor transfer status every 5 seconds for 20 seconds total"""
    try:
        total_monitoring_time = 20  # Total time to monitor in seconds
        check_interval = 5  # Check every 5 seconds
        checks_performed = 0
        max_checks = total_monitoring_time // check_interval  # 4 checks total
        
        print(f"🔍 Starting transfer monitoring - will check every {check_interval}s for {total_monitoring_time}s")
        
        for check_number in range(1, max_checks + 1):
            # Wait for the interval
            await asyncio.sleep(check_interval)
            checks_performed += 1
            
            # Get current call status
            call = twilio_client.calls(call_sid).fetch()
            call_status = call.status
            elapsed_time = check_number * check_interval
            
            print(f"📊 Check {check_number}/{max_checks} ({elapsed_time}s): Call status = {call_status}")
            
            # If call is in-progress, management has answered
            if call_status == "in-progress":
                print(f"✅ Management answered after {elapsed_time} seconds")
                return "answered"
            
            # If call ended (busy, no-answer, failed, canceled, completed)
            elif call_status in ["busy", "no-answer", "failed", "canceled", "completed"]:
                print(f"❌ Transfer failed - call ended with status: {call_status}")
                return call_status
            
            # If still ringing, continue monitoring (unless this was the last check)
            elif call_status == "ringing":
                if check_number < max_checks:
                    print(f"📞 Still ringing... continuing to monitor")
                else:
                    print(f"⏰ Timeout reached - management did not answer within {total_monitoring_time} seconds")
                    return "no-answer"
            
            # Handle any other unexpected statuses
            else:
                print(f"⚠️ Unexpected call status: {call_status}")
                if check_number == max_checks:
                    return call_status
        
        # If we've completed all checks and never got "in-progress", consider it failed
        print(f"⏰ Monitoring complete - management did not answer within {total_monitoring_time} seconds")
        return "no-answer"
        
    except Exception as e:
        print(f"❌ Error monitoring transfer status: {e}")
        return "unknown"


def sms_sending(to_number, from_number):
    """
    Send Faith Agency welcome SMS with website link
    
    Args:
        to_number (str): The recipient's phone number in E.164 format (e.g., +1XXXXXXXXXX)
        from_number (str): The sender's phone number from Twilio
        
    Returns:
        str: The SID of the sent message if successful, None if failed
    """
    content = """Thank you for calling Faith Agency. Here is the link of our website:
www.vivabiblia.com"""
    
    try:
        message_sid = send_sms(to_number, content, from_number)
        if message_sid:
            print(f"✅ Faith Agency SMS sent successfully to {to_number}")
            return message_sid
        else:
            print(f"❌ Failed to send SMS to {to_number}")
            return None
    except Exception as e:
        print(f"❌ Error in sms_sending: {e}")
        return None


def create_faith_agency_email_content(caller_name="", department=""):
    """
    Create Faith Agency email content template
    
    Args:
        caller_name (str): The caller's name for personalization
        department (str): The department the inquiry was directed to
        
    Returns:
        tuple: (subject, content) for the email
    """
    subject = "Thank you for contacting Faith Agency"
    
    # Professional email content matching the original template
    content = f"""Dear {caller_name or 'Valued Customer'},

Thank you for contacting Faith Agency! We appreciate your interest in our services.

{f'Your inquiry was directed to our {department} department.' if department else 'We have received your inquiry.'}

We will get back to you within 24 hours.

Please visit our website for more information: www.vivabiblia.com

Best regards,
The Faith Agency Team

---
Faith Agency - Where faith, creativity, and technology come together."""
    
    return subject, content


def email_sending(to_email, contact_name="", department=""):
    """
    Send Faith Agency welcome email using SendGrid
    
    Args:
        to_email (str): The recipient's email address
        contact_name (str): The contact's name for personalization
        department (str): The department the inquiry was directed to
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get email subject and content from template
        subject, content = create_faith_agency_email_content(caller_name=contact_name, department=department)
        
        # Send email using SendGrid
        result = send_email(to_email, subject, content)
        
        if result:
            print(f"✅ Faith Agency email sent successfully to {to_email} via SendGrid")
            return True
        else:
            print(f"❌ Failed to send email to {to_email} via SendGrid")
            return False
    except Exception as e:
        print(f"❌ Error in email_sending: {e}")
        return False



async def create_ultravox_call(config):
    """Function to create an Ultravox call and get the join URL"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            ULTRAVOX_API_URL,
            json=config,
            headers={'Content-Type': 'application/json', 'X-API-Key': ULTRAVOX_API_KEY}
        )
        response.raise_for_status()
        return response.json()

def format_chat(json_data):
    """Format chat messages for transcript"""
    roles = {
        "MESSAGE_ROLE_USER": "User",
        "MESSAGE_ROLE_AGENT": "Agent"
    }
    
    chat_text = ""
    for message in json_data.get("results", []):
        role = roles.get(message["role"], "Unknown")
        text = message.get("text", "[No response]")
        medium = "(Voice)" if message.get("medium") == "MESSAGE_MEDIUM_VOICE" else "(Text)"
        chat_text += f"{role} {medium}: {text}\n"

    return chat_text

def save_contact_to_csv(contact_data):
    """Save contact information to Progress.csv"""
    csv_file = "Progress.csv"
    fieldnames = [
        "timestamp", "callSid", "departmentCode", "departmentName",
        "callerPhone", "name", "email", "organization", "purpose", "status", "summary"
    ]
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(csv_file)
    
    with open(csv_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        # Write the contact data
        writer.writerow(contact_data)
    
    print(f"Contact information saved to {csv_file}")

def get_department_name(department_input):
    """Get department name from department input (could be number or word)"""
    # Handle both numeric codes and department names
    department_map = {
        # Numeric codes
        "1": "¡VIVA! Audio Bible",
        "2": "Casting & Talent",
        "3": "Press & Media Relations",
        "4": "Tech Support", 
        "5": "Sales & Partnerships",
        "6": "Management Team",
        "0": "General Voicemail",
        # Department names
        "viva": "¡VIVA! Audio Bible",
        "casting": "Casting & Talent",
        "press": "Press & Media Relations", 
        "support": "Tech Support",
        "sales": "Sales & Partnerships",
        "management": "Management Team",
        "voicemail": "General Voicemail"
    }
    
    # Convert to string and lowercase for matching
    dept_key = str(department_input).lower().strip()
    return department_map.get(dept_key, "Unknown Department")

async def extract_contact_from_transcript(transcript: str):
    """
    Extract final confirmed contact info from transcript.
    Email is ONLY valid if:
      - It appears after "Let me spell it back slowly to confirm"
      - AND the user confirms it (yes/ok/perfect/correct/etc.)
    """
    try:
        prompt = f"""
You are a strict data extraction assistant. Use only confirmed information.

RULES:
1. NAME → The name the agent repeats AND caller confirms.
2. EMAIL → Only the version spelled by the agent after the phrase 
   "Let me spell it back slowly to confirm". 
   - Accept it ONLY if the caller then confirms (yes, ok, perfect, correcto, etc.).
   - Convert "at" → "@" and "dot" → "."
   - Remove spaces/commas.
   - Ignore all earlier user-provided emails.
3. DEPARTMENT → The department the user was routed to (viva, casting, press, support, sales, management, voicemail).
4. ORGANIZATION → Only if explicitly mentioned, else empty.
5. PURPOSE → The purpose of the call, as stated or confirmed by the user. Use the agent's paraphrase if confirmed, or the user's own words if not.
6. SUMMARY → Write a short (1-2 lines) summary of the call, focusing on any details, requests, or context NOT already present in the other columns (name, phone, email, organization, purpose, department). Do NOT repeat info from those columns. Instead, mention any extra details, context, or special requests the user made, e.g. "User asked for a press kit and mentioned working with XYZ client." If nothing extra, say "No additional details provided."

Return JSON only:
{{
  "name": "...",
  "email": "...",
  "organization": "...",
  "department": "...",
  "purpose": "...",
  "summary": "..."
}}

TRANSCRIPT:
{transcript}
"""
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise data extraction assistant. Extract only confirmed information. Purpose and summary must follow the rules."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        result = response.choices[0].message.content.strip()
        print(f"🔎 Raw OpenAI response: {result}")
        contact_info = json.loads(result)

        # --- Regex safeguard for email after "spell it back" ---
        match = re.search(
            r"spell it back.*?:\s*([a-z0-9 ,]+).*?Did I spell that correctly\?.*?User.*?(Yes|Ok|Okay|Perfect|Correct|Right|Sure|Sí|Correcto)",
            transcript,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            spelled = match.group(1)
            cleaned = spelled.replace(",", " ").replace("  ", " ").strip()
            cleaned = cleaned.replace(" at ", "@").replace(" dot ", ".").replace(" ", "")
            contact_info["email"] = cleaned

        print(f"✅ Extracted contact info: {contact_info}")
        return contact_info

    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return {
            "name": "",
            "email": "",
            "organization": "",
            "department": "voicemail",
            "purpose": "",
            "summary": "",
        }
    

async def get_call_status(call_id):
    """Poll the Ultravox API for the call status until it ends."""
    headers = {'X-API-Key': ULTRAVOX_API_KEY}
    
    while True:
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{ULTRAVOX_API_URL}/{call_id}', headers=headers)
            response.raise_for_status()
            call_data = response.json()
            
            if call_data.get('ended') is not None:
                return call_data.get('summary')
        await asyncio.sleep(10)

async def get_call_transcript(call_id):
    """Retrieve the transcript of a completed call from Ultravox."""
    headers = {'X-API-Key': ULTRAVOX_API_KEY}
    transcript_url = f'{ULTRAVOX_API_URL}/{call_id}/messages'
    
    async with httpx.AsyncClient() as client:
        response = await client.get(transcript_url, headers=headers)
        response.raise_for_status()
        formatted_chat = format_chat(response.json())
        return formatted_chat

async def monitor_single_flow_call(call_id, caller_phone, call_sid):
    """Monitor the single flow call and save contact information to CSV"""
    try:
        print(f"\n=== MONITORING SINGLE FLOW CALL {call_id} ===")
        print(f"Caller Phone: {caller_phone}")
        print(f"Call SID: {call_sid}")
        print("Waiting for call to complete...")
        
        # Wait for call to end
        await get_call_status(call_id)
        
        # Get the transcript
        transcript = await get_call_transcript(call_id)
        
        print(f"\n=== CALL COMPLETED - ID: {call_id} ===")
        print(f"Full Transcript:\n{transcript}")
        
        # Extract contact information from transcript using OpenAI
        contact_info = await extract_contact_from_transcript(transcript)
        
        if contact_info:
            # Check if there was a transfer attempt and its result
            transfer_result = get_transfer_status(call_sid)

            # Determine status based on transfer result
            if transfer_result == "success":
                status = "Answered"
            else:
                status = "Not answered"

            print(f"📊 Transfer status for {call_sid}: {transfer_result} → Status: {status}")

            # Prepare data for CSV and Sheets
            department_word = contact_info.get("department", "voicemail")
            csv_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "callSid": call_sid,
                "departmentCode": department_word,  # Store what they actually said
                "departmentName": get_department_name(department_word),
                "callerPhone": caller_phone,
                "name": contact_info.get("name", ""),
                "email": contact_info.get("email", ""),
                "organization": contact_info.get("organization", ""),
                "purpose": contact_info.get("purpose", ""),
                "status": status,  # Add status field
                "summary": contact_info.get("summary", "")
            }

            # Save to CSV (update fieldnames if needed)
            save_contact_to_csv(csv_data)

            # Save to Google Sheets
            print(f"\n=== SAVING TO GOOGLE SHEETS ===")
            sheets_success = save_to_google_sheets(csv_data)
            if sheets_success:
                print(f"✅ Data saved to Google Sheets - {csv_data['departmentName']} worksheet")
            else:
                print(f"❌ Failed to save to Google Sheets")

            # Send SMS after saving to CSV using caller_phone from incoming API
            print(f"\n=== SENDING SMS TO CALLER ===")
            print(f"Using caller phone: {caller_phone}")
            sms_result = sms_sending(caller_phone, TWILIO_PHONE_NUMBER)
            if sms_result:
                print(f"✅ SMS sent successfully to {caller_phone}")
            else:
                print(f"❌ Failed to send SMS to {caller_phone}")

            # Send email if email address is available
            if contact_info.get("email"):
                print(f"\n=== SENDING EMAIL TO CALLER ===")
                print(f"Using email: {contact_info.get('email')}")
                email_result = email_sending(contact_info.get("email"), contact_info.get("name", ""))
                if email_result:
                    print(f"✅ Email sent successfully to {contact_info.get('email')}")
                else:
                    print(f"❌ Failed to send email to {contact_info.get('email')}")
            else:
                print("\n=== NO EMAIL ADDRESS AVAILABLE ===")
                print("Skipping email sending - no email provided by caller")

            print(f"\n=== SAVED TO PROGRESS.CSV ===")
            print(f"Department: {csv_data['departmentName']}")
            print(f"Name: {csv_data['name']}")
            print(f"Phone: {csv_data['callerPhone']}")
            print(f"Email: {csv_data['email']}")
            print(f"Organization: {csv_data['organization']}")
            print(f"Purpose: {csv_data['purpose']}")
            print(f"Status: {csv_data['status']}")
            print(f"Summary: {csv_data['summary']}")
            print("=" * 50)
        else:
            print("No contact information found in transcript")
            
    except Exception as e:
        print(f"Error monitoring call {call_id}: {e}")