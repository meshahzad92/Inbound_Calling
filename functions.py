import os
import csv
import json
import httpx
import asyncio
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from twilio_sms import send_sms

load_dotenv()

# Configuration
ULTRAVOX_API_KEY = os.getenv("ULTRAVOX_API_KEY")
ULTRAVOX_API_URL = 'https://api.ultravox.ai/api/calls'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

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
“Thank you for calling Faith Agency, where faith, creativity, and technology come together. 

Please say which department you’d like: 
1 for VIVA, 
2 for Casting, 
3 for Press, 
4 for Tech Support, 
5 for Sales, 
or 6 for Management. 


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

PROGRESSIVE CAPTURE (ONE QUESTION PER TURN, WITH BRIEF CONFIRMATIONS) *Compulsory Information* Must ask all the below points.
1) “What’s your full name?” → “Thanks, [name].”
2) “What’s the best phone number?” → “Got it, [digits].”
3) “What’s your email address?” → “Perfect, [email].”
4) “Kindly, explain the purpose of your call?” → “[Short paraphrase].”
5) (If relevant) “What’s your organization or company?” → “Thanks.”

LINK/OFFER (SMS ONLY)
- VIVA/Press: “Want me to text you the info link?”
- Support: “I’ll text your ticket confirmation.”
- Sales: “I’ll text our team your request summary.”

FAIL-SAFES
- If unclear: “Could you clarify in a few words?”
- If caller asks voicemail/‘0’: collect name, phone, purpose; end politely.

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
    fieldnames = ["timestamp", "callSid", "departmentCode", "departmentName", "callerPhone", "name", "phone", "email", "organization", "summary"]
    
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
Extract contact information from this phone call transcript. Return ONLY a JSON object with these exact fields:

- name: caller's full name (empty string if not found)
- phone: phone number (empty string if not found) 
- email: email address (empty string if not found)
- organization: company/organization name (empty string if not found)
- summary: brief reason for calling (empty string if not found)
- department: what department the caller chose. Look for what they said like "viva", "casting", "press", "support", "sales", "management", "voicemail" or "option 1", "option 2", etc. If they said "option 1" or mentioned VIVA, return "viva". If they said "option 2" or mentioned casting, return "casting". If they said "option 3" or mentioned press, return "press". If they said "option 4" or mentioned support, return "support". If they said "option 5" or mentioned sales, return "sales". If they said "option 6" or mentioned management, return "management". If unclear, return "voicemail".

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
            "summary": "",
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
            # Prepare data for CSV
            department_word = contact_info.get("department", "voicemail")
            csv_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "callSid": call_sid,
                "departmentCode": department_word,  # Store what they actually said
                "departmentName": get_department_name(department_word),
                "callerPhone": caller_phone,
                "name": contact_info.get("name", ""),
                "phone": contact_info.get("phone", ""),
                "email": contact_info.get("email", ""),
                "organization": contact_info.get("organization", ""),
                "summary": contact_info.get("summary", "")
            }
            
            # Save to CSV
            save_contact_to_csv(csv_data)
            
            # Send SMS after saving to CSV using caller_phone from incoming API
            print(f"\n=== SENDING SMS TO CALLER ===")
            print(f"Using caller phone: {caller_phone}")
            sms_result = sms_sending(caller_phone, TWILIO_PHONE_NUMBER)
            if sms_result:
                print(f"✅ SMS sent successfully to {caller_phone}")
            else:
                print(f"❌ Failed to send SMS to {caller_phone}")
            
            print(f"\n=== SAVED TO PROGRESS.CSV ===")
            print(f"Department: {csv_data['departmentName']}")
            print(f"Name: {csv_data['name']}")
            print(f"Phone: {csv_data['phone']}")
            print(f"Email: {csv_data['email']}")
            print(f"Organization: {csv_data['organization']}")
            print(f"Summary: {csv_data['summary']}")
            print("=" * 50)
        else:
            print("No contact information found in transcript")
            
    except Exception as e:
        print(f"Error monitoring call {call_id}: {e}")