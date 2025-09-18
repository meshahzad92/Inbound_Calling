import os
import csv
import json
import time
import httpx
import asyncio
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from twilio_sms import send_sms
from email_automation import send_faith_agency_email
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from google_sheet import save_to_google_sheets

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


def email_sending(to_email, contact_name=""):
    """
    Send Faith Agency welcome email
    
    Args:
        to_email (str): The recipient's email address
        contact_name (str): The contact's name for personalization
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        result = send_faith_agency_email(to_email, contact_name)
        if result:
            print(f"✅ Faith Agency email sent successfully to {to_email}")
            return True
        else:
            print(f"❌ Failed to send email to {to_email}")
            return False
    except Exception as e:
        print(f"❌ Error in email_sending: {e}")
        return False



def get_single_flow_prompt(call_sid=""):
    return f"""
ROLE
You are Faith Agency’s AI receptionist. Handle the entire call in one conversational flow.

TONE & BEHAVIOR
- Warm, natural, human; listen first, then respond.
- Short, on-point replies (1 short sentence).
- Ask exactly ONE question per turn.
- Paraphrase key details back briefly (“Got it—[detail].”).
- Never rush; keep a friendly pace with natural pauses.

PRIMARY GOAL
- Guide the caller to the right department.
- Collect their info step-by-step.
- Confirm: “We’ll get back to you within 24 hours.”
- Offer SMS links where relevant (no email).

OPENING (ALWAYS FIRST)
“Thank you for calling Faith Agency — where faith, creativity, and technology come together. 
To help direct your call, you can say: 
‘Sales and Partnerships,’ 
‘VIVA Audio Bible,’ 
‘Casting and Talent,’ 
‘Press and Media,’ or 
‘Technical Support.’ 
To reach a management team member, just say their name. 
How may I assist you today?”


OPTION RECOGNITION (EXAMPLES, NOT EXHAUSTIVE)
- “VIVA”, “option 1”, “one”, “Spanish Bible”, “audio bible” → Dept 1
- “Casting”, “option 2”, “two”, “talent”, “audition” → Dept 2
- “Press”, “option 3”, “three”, “media”, “journalist” → Dept 3
- “Support”, “option 4”, “four”, “tech”, “app”, “technology” → Dept 4
- “Sales”, “option 5”, “five”, “partnerships”, “business” → Dept 5
- A specific person’s name → Dept 6 (Management)
- “Repeat”, “menu”, “options again” → repeat opening menu
- “Voicemail”, “message”, “leave message” → Dept 0

INVALID / UNCLEAR
- If unclear/invalid: “I didn’t catch that. Which option would you like?” Then re-summarize the menu.

DEPARTMENT FLOWS (CONVERSATIONAL, SHORT)

[1] VIVA
- Opening: “You’ve reached the ¡VIVA! Audio Bible team.”
- Ask: “Are you calling about events, releases, or general info?”
- Offer: “I can text you a helpful link.”

[2] Casting
- Opening: “Thanks for your interest in Faith Agency productions.”
- Ask: “Are you a talent rep, or a performer yourself?”

[3] Press
- Opening: “You’ve reached Faith Agency’s press desk.”
- Ask: “Journalist, outlet, or influencer—and which project?”
- Offer: “I can text you our press-kit link.”

[4] Support
- Opening: “You’ve reached technical support.”
- Ask: “What device are you using?”
- Say: “I’ll log a ticket. You’ll hear back within 24 hours.”

[5] Sales
- Opening: “Thanks for calling sales and partnerships.”
- Ask: “Distributor, sponsor, investor—or retailer/church?”

[6] Management
- Opening: “You’ve reached Faith Agency management.”
- Ask: “Which team member would you like to reach?”
- If unavailable: “I’ll take your details for a callback.”

[0] Voicemail
- Prompt: “Please share your name, phone, and purpose after the tone.”

TRANSFER LOGIC (IF YOUR BACKEND SIGNALS ‘AVAILABLE’)
- Offer: “Would you like me to connect you now?”
- If no answer/busy: “They’re unavailable. I’ll take your details.”

PROGRESSIVE CAPTURE (ONE QUESTION PER TURN, WITH BRIEF CONFIRMATIONS) 
*Compulsory Information* — Must ask all the points below in order.

1) “What’s your full name?”  
   → Confirm: “Thanks, I heard [name]. Did I get that right?”  
   → Speak name slowly and clearly. If unclear, politely re-ask.


2) “What’s your email address?”  
   → Confirm: “Thanks. Let me spell it back slowly to confirm.”  
   → Read the email **character by character** (letters, numbers, dot, at).  
   Example: “m , s, h, a, h, z, a, d, w, a, r, i, s, at, g, m, a, i, l, dot, com.”  
   → Ask: “Did I spell that correctly?”

3) “Could you please repeat your email address once more, just to confirm?”  
   → Again, spell it back slowly.  
   - If both match: say “Perfect, your email is confirmed.”  
   - If mismatch: say “Hmm, I noticed it’s different. Let’s try again carefully.”  
     Repeat until both match.

4) “Kindly, explain the purpose of your call?”  
   → Summarize back: “So you’re calling about [short paraphrase]. Did I get that right?”

5) (If relevant) “What’s your organization or company?”  
   → Confirm slowly: “Thanks, I recorded [organization].”


LINK/OFFER (SMS ONLY)
- VIVA/Press: “Want me to text you the info link?”
- Support: “I’ll text your ticket confirmation.”
- Sales: “I’ll text our team your request summary.”

FAIL-SAFES
- If unclear: "Could you clarify in a few words?"
- If caller asks voicemail/'0': collect name, phone, purpose; end politely.

MANAGEMENT TRANSFER RULE (SIMPLE APPROACH) - *** CRITICAL ***
- If caller asks for management or redirection:
   1) Say: "I'll be happy to connect you to our management team. First, let me get your details."
   2) Proceed with progressive capture to collect:
      - Name
      - Email address (confirm twice)  
      - Purpose of call
      - Organization (if relevant)
   3) After collecting all information, say: "Perfect! I have all your details. Let me connect you to management now."
   4) MANDATORY: Immediately use the transferCall tool with parameters:
        destinationNumber = "MANAGEMENT_REDIRECT_NUMBER"
        transferReason = "Caller requested management - Info collected: [name], [email], [purpose]"

   5):WAIT 10 SECONDS after initiating transfer.

   6):If the call is answered: AI remains silent (end participation).

   7):If transfer fails or times out: Say
        "I'll make sure management gets your message and calls you back within 24 hours."

*** CRITICAL REMINDER *** 
When someone asks for "management", "redirect", "transfer", "manager", or "supervisor", you MUST:
1. Collect their info FIRST
2. Then IMMEDIATELY use transferCall tool - DO NOT SKIP THIS STEP
3. The transfer is MANDATORY after info collection



CLOSING (ALWAYS)
“Thanks. We’ll get back to you within 24 hours. Goodbye.”

"""


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
    fieldnames = ["timestamp", "callSid", "departmentCode", "departmentName", "callerPhone", "name", "email", "organization", "status"]
    
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

async def extract_contact_from_transcript(transcript):
    """Extract contact information from transcript using OpenAI"""
    try:
        prompt = f"""
Extract and CORRECT contact information from this phone call transcript. Return ONLY a JSON object with these exact fields:

- name: caller's full name (empty string if not found)
- email: email address (empty string if not found) - IMPORTANT: Fix common email errors:
  * Remove extra words like "the", "rate", "there" from domain names
  * Fix obvious transcription errors (e.g., "theratelhr.nu.edu.pk" → "lhr.nu.edu.pk")
  * Correct common domain mistakes (e.g., "gmail.com" not "g mail dot com")
  * Fix obvious typos in common domains (.com, .org, .edu, .pk, etc.)
- organization: company/organization name (empty string if not found)
- department: what department the caller chose. Look for what they said like "viva", "casting", "press", "support", "sales", "management", "voicemail" or "option 1", "option 2", etc. If they said "option 1" or mentioned VIVA, return "viva". If they said "option 2" or mentioned casting, return "casting". If they said "option 3" or mentioned press, return "press". If they said "option 4" or mentioned support, return "support". If they said "option 5" or mentioned sales, return "sales". If they said "option 6" or mentioned management, return "management". If unclear, return "voicemail".

CORRECTION GUIDELINES:
- Email domains: Remove filler words that don't belong (the, rate, there, etc.)
- Names: Capitalize properly and fix obvious transcription errors
- Organizations: Correct obvious misspellings of well-known companies/universities

Transcript:
{transcript}

Return only the JSON object, no other text.
"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        contact_info = json.loads(result)
        
        print(f"✅ OpenAI extracted contact info: {contact_info}")
        return contact_info
        
    except Exception as e:
        print(f"❌ OpenAI extraction error: {e}")
        # Return empty contact info if extraction fails
        return {
            "name": "",
            "phone": "",
            "email": "",
            "organization": "",
            "department": "voicemail"
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
            
            # Prepare data for CSV
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
                "status": status  # Add status field
            }
            
            # Save to CSV
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
            print(f"Phone: {csv_data['phone']}")
            print(f"Email: {csv_data['email']}")
            print(f"Organization: {csv_data['organization']}")
            print(f"Status: {csv_data['status']}")
            print("=" * 50)
        else:
            print("No contact information found in transcript")
            
    except Exception as e:
        print(f"Error monitoring call {call_id}: {e}")