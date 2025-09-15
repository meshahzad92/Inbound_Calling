import requests
import os
import json
from typing import Dict, Any, Optional, Literal
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Get API keys from environment variables
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not PERPLEXITY_API_KEY:
    print("Warning: PERPLEXITY_API_KEY not found in environment variables")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

class CompanyResearchProcessor:
    def __init__(self):
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
    
    def search_company_info(self, company_name: str, website: str = None, linkedin_url: str = None) -> Optional[Dict[str, Any]]:
        """
        Search for information about a company using Perplexity AI
        """
        if not PERPLEXITY_API_KEY:
            print("Perplexity API key not available, using fallback")
            return {"companyDescription": f"Information about {company_name}"}
        
        print(f"Searching for information about {company_name}...")
        
        # Build search query
        search_query = f"Research the company {company_name}."
        if website:
            search_query += f" The company website is {website}."
        if linkedin_url:
            search_query += f" The company LinkedIn page is {linkedin_url}."
        
        search_query += """ Please provide a comprehensive analysis of the company including:
1) Detailed company description and mission statement
2) Complete list of products and services with descriptions
3) Target market segments and customer profiles
4) Company size, revenue, and growth metrics
5) Company history, founding date, and major milestones
6) Leadership team and key personnel
7) Industry position and competitive advantages
8) Recent news, achievements, or awards
9) Company culture and values
10) Geographic presence and office locations
11) Technology stack and infrastructure
12) Partnerships and strategic alliances
13) Customer testimonials or case studies
14) Future plans and growth strategy

Format the response as a structured JSON with the following fields:
{
    "companyDescription": "Detailed company overview and mission",
    "mainProducts": "Comprehensive list of products/services with descriptions",
    "targetMarket": "Detailed market segments and customer profiles",
    "companySize": "Size, revenue, employee count, and growth metrics",
    "companyHistory": "Founding date, milestones, and evolution",
    "leadership": "Key executives and leadership team",
    "industryPosition": "Market position and competitive advantages",
    "recentNews": "Recent achievements, awards, or significant events",
    "companyCulture": "Values, culture, and work environment",
    "locations": "Geographic presence and office locations",
    "technologies": "Technology stack and infrastructure details",
    "partnerships": "Strategic alliances and partnerships",
    "testimonials": "Customer success stories and testimonials",
    "futurePlans": "Growth strategy and future initiatives",
    "additionalDetails": "Any other relevant information"
}"""
        
        # Build request payload
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI research assistant that provides accurate information about companies. Format your response as valid JSON."
                },
                {
                    "role": "user",
                    "content": search_query
                }
            ]
        }
        
        try:
            # Make API request
            response = requests.post(self.perplexity_url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            
            # Extract the content from Perplexity's response
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # Try to extract JSON from the response
                try:
                    company_data = json.loads(content)
                    return company_data
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    if "```json
" in content and "
```" in content:
                        json_content = content.split("```json
")[1].split("
```")[0].strip()
                        try:
                            company_data = json.loads(json_content)
                            return company_data
                        except json.JSONDecodeError:
                            print("Failed to parse JSON from code block")
                    
                    print("Could not parse JSON from Perplexity response, returning raw text")
                    return {"rawDescription": content}
            else:
                print("No valid content in Perplexity response")
                return None
                
        except Exception as e:
            print(f"Error searching for company information: {str(e)}")
            return None
    
    def analyze_call_sentiment(self, call_summary: str) -> Literal["Positive", "Negative", "Neutral"]:
        """
        Analyze the sentiment of a call summary and return only Positive, Negative, or Neutral
        """
        if not client:
            print("OpenAI client not available, returning default sentiment")
            return "Neutral"
            
        print("Analyzing call sentiment...")

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Classify the sentiment of the user's input as exactly one of: Positive, Negative, or Neutral. Respond with ONLY one of these words and nothing else."
                    },
                    {
                        "role": "user",
                        "content": f"Call summary: {call_summary}"
                    }
                ],
                temperature=0.1
            )

            sentiment = response.choices[0].message.content.strip().capitalize()

            if sentiment in {"Positive", "Negative", "Neutral"}:
                return sentiment
            else:
                print(f"Unexpected response: {sentiment}")
                return "Neutral"

        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return "Neutral"
    
    def generate_ultravox_prompt(self, company_db_data: Dict[str, Any], web_research: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a prompt for Ultravox AI based on company DB data and web research
        """
        company_name = company_db_data.get("company_name", "the company")
        industry = company_db_data.get("industry", "")
        technologies = company_db_data.get("technologies", "")
        seo_description = company_db_data.get("seo_description", "")
        
        # Start with basic company info
        prompt = f"""
You are an AI virtual assistant representing {company_name}.
"""
        
        # Add industry information if available
        if industry:
            prompt += f"You are a company in the {industry} industry. "
        
        # Add SEO description if available
        if seo_description:
            prompt += f"\n\nCompany description: {seo_description}\n"
        
        # Add technologies if available
        if technologies:
            prompt += f"\nThe company uses technologies including: {technologies}.\n"
        
        # Add web research information if available
        if web_research:
            if "companyDescription" in web_research:
                prompt += f"\nDetailed company overview: {web_research.get('companyDescription')}\n"
            
            if "mainProducts" in web_research:
                prompt += f"\nProducts and services: {web_research.get('mainProducts')}\n"
                
            if "targetMarket" in web_research:
                prompt += f"\nTarget market: {web_research.get('targetMarket')}\n"
            
            if "companySize" in web_research:
                prompt += f"\nCompany size and metrics: {web_research.get('companySize')}\n"
            
            if "companyHistory" in web_research:
                prompt += f"\nCompany history: {web_research.get('companyHistory')}\n"
            
            if "leadership" in web_research:
                prompt += f"\nLeadership team: {web_research.get('leadership')}\n"
            
            if "industryPosition" in web_research:
                prompt += f"\nIndustry position: {web_research.get('industryPosition')}\n"
            
            if "recentNews" in web_research:
                prompt += f"\nRecent news and achievements: {web_research.get('recentNews')}\n"
            
            if "companyCulture" in web_research:
                prompt += f"\nCompany culture: {web_research.get('companyCulture')}\n"
            
            if "locations" in web_research:
                prompt += f"\nGeographic presence: {web_research.get('locations')}\n"
            
            if "technologies" in web_research:
                prompt += f"\nTechnology infrastructure: {web_research.get('technologies')}\n"
            
            if "partnerships" in web_research:
                prompt += f"\nStrategic partnerships: {web_research.get('partnerships')}\n"
            
            if "testimonials" in web_research:
                prompt += f"\nCustomer success stories: {web_research.get('testimonials')}\n"
            
            if "futurePlans" in web_research:
                prompt += f"\nFuture plans: {web_research.get('futurePlans')}\n"
            
            if "additionalDetails" in web_research:
                prompt += f"\nAdditional information: {web_research.get('additionalDetails')}\n"
        
        # Add instructions for AI behavior
        prompt += """
You are answering an incoming phone call from a customer.
Welcome to Conversa AI. This is a demonstration call for internal evaluation purposes only. Thank you for testing your personalized demo.
Your communication style should be warm, natural, and conversational - like a friendly human colleague.
Avoid sounding robotic or reading from a script. Instead, engage in a natural back-and-forth dialogue.
Keep your responses concise but personable. Use casual, everyday language while maintaining professionalism.
Be proactive in asking relevant questions to understand the caller's needs better.
Show empathy and understanding in your responses.

Remember, our tone is conversational, slightly assertive, friendly, and confident. We always end with a follow-up or clarifying question. Ensure a natural pause after each question to allow for the caller's response.

Fallback Example (if stuck or unsure):

"That's a good question. Based on what I've seen, most clients in your space are solving that by speeding up follow-up. Are you currently using reps or software to manage that?"

When discussing the company:
- Use specific details about products, services, and achievements
- Reference recent news or developments when relevant
- Share relevant customer success stories
- Mention specific industry expertise and experience
- Highlight unique selling points and competitive advantages
- Discuss future plans and growth opportunities when appropriate

If you don't know something specific, be honest and offer to find out or connect them with someone who can help.
Your goal is to provide helpful information while making the caller feel comfortable and valued.
"""
        
        return prompt
    
    def process_company(self, company_data: Dict[str, Any]) -> str:
        """
        Process company data from database and generate an Ultravox prompt
        """
        # Extract company information
        company_name = company_data.get("company_name", "")
        website = company_data.get("website", "")
        linkedin_url = company_data.get("company_linkedin_url", "")
        
        # Skip web research if no company name is provided
        if not company_name:
            print("No company name provided, skipping web research")
            return self.generate_ultravox_prompt(company_data)
        
        # Perform web research
        web_research = self.search_company_info(company_name, website, linkedin_url)
        
        # Generate prompt
        prompt = self.generate_ultravox_prompt(company_data, web_research)
        
        return prompt# Faith Agency Inbound Calling System

AI-powered phone system that handles incoming calls, routes to departments, collects contact information, and automatically sends follow-up SMS messages.

## 🎯 Features

- **AI-Powered Conversations**: Uses Ultravox AI for natural voice interactions
- **Department Routing**: Routes calls to VIVA, Casting, Press, Tech Support, Sales, or Management
- **Smart Data Collection**: Collects caller information (name, phone, email, organization, purpose)
- **Automatic SMS Follow-up**: Sends Faith Agency website link after each call
- **CSV Logging**: Saves all contact data to Progress.csv for analysis
- **OpenAI Integration**: Intelligent contact information extraction from call transcripts

## 🏗️ Project Structure

```
├── main.py                 # FastAPI application with call handling endpoints
├── functions.py            # Core business logic and helper functions
├── twilio_sms.py          # SMS sending functionality
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (create this)
├── Progress.csv           # Contact data storage (auto-generated)
└── README.md              # This file
```

### 📁 File Descriptions

- **`main.py`**: Main FastAPI server handling incoming call webhooks from Twilio
- **`functions.py`**: Contains all business logic including AI prompts, data extraction, CSV operations, and call monitoring
- **`twilio_sms.py`**: Handles SMS sending through Twilio API
- **`Progress.csv`**: Automatically generated file storing all collected contact information

## 🚀 Setup Instructions

### Step 1: Create Environment File

Create a `.env` file in the root directory with the following structure:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database Configuration (optional - commented out)
# DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# Twilio Configuration (for handling phone calls)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Ultravox API Configuration (for AI conversations)
ULTRAVOX_API_KEY=your_ultravox_api_key

# OpenAI Configuration (for contact data extraction)
OPENAI_API_KEY=your_openai_api_key

# Perplexity API Configuration (optional)
PERPLEXITY_API_KEY=your_perplexity_api_key
```

### Step 2: Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### Step 3: Run the Application

```bash
# Start the FastAPI server
python main.py

# Alternative using uvicorn directly:
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🔧 API Configuration

### Required API Keys

1. **Twilio Account**: Sign up at [twilio.com](https://twilio.com)
   - Get Account SID, Auth Token, and Phone Number
   - Configure webhook URL to point to your server's `/api/incoming` endpoint

2. **Ultravox API**: Get API key from [ultravox.ai](https://ultravox.ai)
   - Used for AI voice conversations

3. **OpenAI API**: Get API key from [openai.com](https://openai.com)
   - Used for intelligent contact information extraction

### Webhook Configuration

Configure your Twilio phone number webhook URL to:
```
https://your-domain.com/api/incoming
```

For local development with ngrok:
```bash
# In a separate terminal
ngrok http 8000

# Use the ngrok URL for Twilio webhook:
# https://xxxxx.ngrok.io/api/incoming
```

## 📞 How It Works

1. **Incoming Call**: Twilio receives call and sends webhook to `/api/incoming`
2. **AI Greeting**: Ultravox AI greets caller and presents department options
3. **Department Selection**: Caller chooses from 6 departments or voicemail
4. **Information Collection**: AI systematically collects:
   - Full name
   - Phone number
   - Email address
   - Organization/company
   - Purpose of call
5. **Data Storage**: All information saved to `Progress.csv`
6. **SMS Follow-up**: Automatic SMS sent with Faith Agency website link
7. **Call Completion**: 24-hour follow-up promise given to caller

## 🏢 Department Options

1. **VIVA** - Spanish Audio Bible team
2. **Casting** - Talent and casting department  
3. **Press** - Media relations and press inquiries
4. **Tech Support** - App and technology support
5. **Sales** - Partnerships and sales
6. **Management** - Executive team access
7. **Voicemail** - General message system

## 📊 Data Collection

All call data is automatically saved to `Progress.csv` with the following fields:

- `timestamp` - Call completion time
- `callSid` - Twilio call identifier
- `departmentCode` - Selected department
- `departmentName` - Full department name
- `callerPhone` - Caller's phone number
- `name` - Collected name
- `phone` - Collected phone number
- `email` - Collected email address
- `organization` - Company/organization
- `summary` - Purpose of call

## 🛠️ Development

### Adding New Features

- **New departments**: Update `get_single_flow_prompt()` in `functions.py`
- **SMS templates**: Modify `sms_sending()` function
- **Data fields**: Update CSV fieldnames and extraction prompts

### Monitoring

Check console output for:
- Call status updates
- AI extraction results
- SMS sending confirmations
- Error messages and debugging info

## 📋 Dependencies

Key packages (see `requirements.txt` for complete list):

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `twilio` - Twilio API integration
- `openai` - OpenAI API client
- `httpx` - HTTP client for Ultravox API
- `python-dotenv` - Environment variable management

## 🚨 Troubleshooting

- **SMS not sending**: Check Twilio credentials and phone number format
- **AI not responding**: Verify Ultravox API key and network connectivity
- **Data extraction failing**: Check OpenAI API key and quota
- **Webhook errors**: Ensure ngrok tunnel is active for local development

## 📄 License

This project is proprietary to Faith Agency.