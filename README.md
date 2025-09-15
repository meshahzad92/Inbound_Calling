# Faith Agency - AI Calling Systemimport requests

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
python3.12 -m venv venv

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

This project is proprietary to Faith Agency.and casting department  
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