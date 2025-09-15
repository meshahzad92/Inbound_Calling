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
        
        return prompt# Inbound Calling System

A standalone AI-powered inbound calling system that handles incoming calls using advanced AI technology. This system processes calls through extension-based routing and provides intelligent conversations using Ultravox AI.

## Features

- **Extension-Based Routing**: Callers enter 5-digit extensions to reach specific companies
- **AI-Powered Conversations**: Uses Ultravox AI for natural, context-aware conversations
- **Company Research**: Automatically researches companies using Perplexity AI for personalized conversations
- **Call Recording & Transcription**: Automatically records and transcripts all calls
- **Sentiment Analysis**: Analyzes call sentiment using OpenAI GPT-4
- **Database Storage**: Stores all call data and company information in PostgreSQL

## System Architecture

```
Incoming Call → Twilio → FastAPI Backend → Extension Validation → Company Lookup → AI Conversation (Ultravox) → Call Recording → Sentiment Analysis → Database Storage
```

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Twilio account with phone number
- Ultravox API key
- OpenAI API key (optional, for sentiment analysis)
- Perplexity API key (optional, for company research)

### Installation

1. **Clone or copy this folder to your desired location**

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and database credentials
   ```

5. **Set up the database**:
   ```bash
   # Create database (if it doesn't exist)
   createdb inbound_calling_system
   
   # Populate with sample data
   python db_populate.py
   ```

### Configuration

Edit the `.env` file with your credentials:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/inbound_calling_system

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# APIs
ULTRAVOX_API_KEY=your_ultravox_api_key
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
```

### Running the Application

1. **Start the server**:
   ```bash
   python main.py
   ```
   
   The API server will run on `http://localhost:8000`

2. **Configure Twilio Webhook**:
   - In your Twilio Console, set the webhook URL for incoming calls to:
   ```
   http://your-domain.com/api/incoming
   ```

3. **Test the system**:
   - Call your Twilio phone number
   - Enter a 5-digit extension (e.g., 00001, 00002, 00003, 00004, or 00005)
   - Experience the AI conversation

## How It Works

### Call Flow

1. **Customer calls** your Twilio phone number
2. **System prompts** for a 5-digit extension
3. **Extension validation** against the company database
4. **Company lookup** and data retrieval
5. **AI prompt generation** using company information and research
6. **Ultravox AI** conducts the conversation
7. **Call monitoring** tracks completion in the background
8. **Transcription** and sentiment analysis are performed
9. **Data storage** saves all call information to the database

### Extension System

The system uses 5-digit extensions to route calls to specific companies:
- `00001` - TechStart Solutions
- `00002` - Digital Marketing Pro
- `00003` - Healthcare Innovations
- `00004` - FinTech Dynamics
- `00005` - EcoGreen Energy

### AI Features

- **Dynamic Prompts**: AI conversations are personalized based on company data
- **Company Research**: Real-time research using Perplexity AI
- **Sentiment Analysis**: Post-call sentiment analysis using OpenAI
- **Natural Conversations**: Powered by Ultravox voice AI

## API Endpoints

- `POST /api/incoming` - Handle incoming Twilio calls
- `POST /extension_handling` - Process extension input
- `GET /health` - Health check endpoint

## Database Schema

### Companies Table
- Extension-based routing
- Company information and metadata
- Contact details and research data

### Inbound Calls Table
- Call records and timestamps
- Caller information
- Transcriptions and sentiment analysis
- Company associations

## Adding New Companies

### Method 1: CSV Import

1. Create a CSV file with company data
2. Run the population script:
   ```bash
   python db_populate.py your_companies.csv
   ```

### Method 2: Manual Addition

Use the CRUD operations in `crud.py` to add companies programmatically.

### Required Company Fields

- `extension`: 5-digit unique identifier
- `company_name`: Company name
- `website`: Company website (optional)
- `industry`: Industry category (optional)
- `seo_description`: Company description (optional)

## Customization

### AI Conversation Prompts

Edit the system prompts in `main.py` or modify the `gpt.py` file to customize AI behavior.

### Call Flow Logic

Modify `main.py` to change the call flow, add features, or integrate additional services.

### Database Schema

Update `models.py` to add new fields or tables as needed.

## Deployment

### Local Development
```bash
python main.py
```

### Production Deployment

1. **Using Docker**:
   ```bash
   docker build -t inbound-calling-system .
   docker run -p 8000:8000 inbound-calling-system
   ```

2. **Using systemd** (Linux):
   Create a service file and enable it for production deployment.

3. **Cloud Deployment**:
   Deploy to AWS, GCP, or Azure with proper environment configuration.

## Monitoring

- Check logs for call processing information
- Monitor database for call records
- Use the health endpoint for system status

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Verify DATABASE_URL in .env
   - Ensure PostgreSQL is running
   - Check database permissions

2. **Twilio Webhook Errors**:
   - Verify webhook URL is accessible
   - Check Twilio credentials
   - Ensure proper HTTPS in production

3. **AI API Errors**:
   - Verify API keys are correct
   - Check API rate limits
   - Monitor API responses in logs

4. **Call Processing Issues**:
   - Check Ultravox API key and quotas
   - Verify network connectivity
   - Review error logs

### Debug Mode

Run with debug logging:
```bash
export PYTHONPATH=. && python -u main.py
```

## Security Considerations

- Use HTTPS in production
- Secure API keys and database credentials
- Implement proper authentication for sensitive endpoints
- Regular security updates

## Support

- Check application logs for detailed error information
- Verify all environment variables are properly configured
- Ensure all required services are running and accessible

## Architecture Notes

This system is designed to be:
- **Standalone**: No dependencies on external codebases
- **Scalable**: Can handle multiple concurrent calls
- **Extensible**: Easy to add new features and integrations
- **Maintainable**: Clean code structure with separation of concerns