import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
import asyncio

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

Return JSON only:
{{
  "name": "...",
  "email": "...",
  "organization": "...",
  "department": "..."
}}

TRANSCRIPT:
{transcript}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise data extraction assistant. Extract only confirmed information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        result = response.choices[0].message.content.strip()
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
        }


if __name__ == "__main__":
    test_transcript = """User (Text): (New Call) Respond as if you are answering the phone.
Agent (Text): In which language would you like to continue: English or
User (Voice): [No response]
Agent (Text): Thank you for calling Faith Agency — where faith, creativity, and technology come together. To help direct your call, you can say: ‘Sales and Partnerships,’ ‘VIVA Audio Bible,’ ‘Casting and Talent,’ ‘Press and Media,’ or ‘Technical Support.’
User (Voice): River Bible.
Agent (Text): You've reached the VIVA Audio Bible team. Are you calling about events, releases, or general info?
User (Voice): Events. Events.
Agent (Text): Got it—events. What's your full name?
User (Voice): [No response]
Agent (Text): Thanks, I heard Muhammad Shahzad. Did I get that right?
User (Voice): Yes.
Agent (Text): Thanks, I confirmed your name as Muhammad Shahzad. What's your email address?
User (Voice): Mshahzedadwaris92@therategmail.com.
Agent (Text): Thanks. Let me spell it back slowly to confirm: m, s, h, a, h, z, a, d, w, a, r, i, s, 9, 2, at, g, m, a, i, l, dot, com. Did I spell that correctly?
User (Voice): No. It's mshahzedadwaris92@therategmail.com.
Agent (Text): Let me try again. You said your email address is: m, s, h, a, h, z, a, d, w, a, r, i, s, 9, 2, at, g, m, a, i, l, dot, com, but the correct one is: m, f, s, h, a, h, z, a, d, w, a, r, i, s, 9, 2, at, t, h, e, r, a, t, g, m, a, i, l, dot, com. Could you please repeat your email address once more, just to confirm?
User (Voice): Mshahzedadwaris92@gmail.com.
Agent (Text): Let me spell it back slowly again: m, s, h, a, h, z, a, d, w, a, r, i, s, 9, 2, at, t, h, e, r, a, t, g, m, a, i, l, dot, com. This time, it matches what you said earlier. Perfect, your email is confirmed. So you're
User (Voice): No. No. It's not u a it's not u a r a s. It's w a r a s.
Agent (Text): Let me try again. You said your email address is: m, s, h, a, h, z, a, d, w, a, r, i, s, 9, 2, at, t, h, e, r, a, t, g, m, a, i, l, dot, com. I'll make sure to get it right this time. To confirm,
User (Voice): Yes.
Agent (Text): So, to confirm, your email address is: m, s, h, a, h, z, a, d, w, a, r, i, s, 9, 2, at, t, h, e, r, a, t, g, m, a, i, l, dot, com. Kindly, explain the purpose of your call?
    """

    asyncio.run(extract_contact_from_transcript(test_transcript))
