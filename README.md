# Faith Agency - AI Calling System

AI-powered phone system that handles incoming calls, routes to departments, collects contact information, and automatically integrates with Google Sheets for data management and follow-up communications.

## 🎯 Features

- **AI-Powered Conversations**: Uses Ultravox AI for natural voice interactions
- **Department Routing**: Routes calls to 7 departments with seamless transfers
- **Smart Data Collection**: Collects caller information (name, phone, email, organization)
- **Google Sheets Integration**: Automatically saves data to department-specific worksheets
- **Automatic SMS Follow-up**: Sends Faith Agency website link after each call
- **Email Automation**: Sends personalized welcome emails with Faith Agency branding
- **CSV Backup**: Maintains local Progress.csv for data redundancy
- **OpenAI Integration**: Intelligent contact information extraction from call transcripts
- **Call Transfer System**: Bridges calls to management with answer detection

## 🏗️ Project Structure

```
├── main.py                   # FastAPI application with call handling endpoints
├── functions.py              # Core business logic and helper functions
├── google_sheet.py           # Google Sheets API integration
├── email_automation.py       # Gmail API integration for email automation
├── twilio_sms.py            # SMS sending functionality
├── requirements.txt          # Python dependencies
├── .env                     # Environment variables (create this)
├── credentials.json         # Google Sheets API credentials (create this)
├── Progress.csv             # Contact data storage (auto-generated)
├── email_automation/        # Email automation folder
│   ├── credentials.json     # Gmail API credentials
│   ├── token.json          # Gmail OAuth token (auto-generated)
│   └── gmail_sender.py     # Gmail sending logic
├── sheets_automation/       # Google Sheets automation folder
│   ├── credentials.json    # Google Sheets API credentials
│   ├── token.json         # Google Sheets OAuth token (auto-generated)
│   ├── requirements.txt   # Sheets-specific dependencies
│   └── read_sheet.py      # Sheets reading and setup utilities
└── README.md              # This file
```

### 📁 File Descriptions

- **`main.py`**: Main FastAPI server handling incoming call webhooks from Twilio
- **`functions.py`**: Contains all business logic including AI prompts, data extraction, CSV operations, call monitoring, SMS and email sending
- **`google_sheet.py`**: Google Sheets API integration for department-specific data storage
- **`email_automation.py`**: Gmail API integration for sending automated welcome emails
- **`twilio_sms.py`**: Handles SMS sending through Twilio API
- **`Progress.csv`**: Automatically generated file storing all collected contact information
- **`email_automation/`**: Contains Gmail credentials and email automation logic
- **`sheets_automation/`**: Contains Google Sheets credentials and automation utilities

## 🚀 Setup Instructions

### Step 1: Create Environment File

Create a `.env` file in the root directory with the following structure:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000

# Twilio Configuration (for handling phone calls)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Ultravox API Configuration (for AI conversations)
ULTRAVOX_API_KEY=your_ultravox_api_key

# OpenAI Configuration (for contact data extraction)
OPENAI_API_KEY=your_openai_api_key

# Gmail Configuration (for email automation)
FROM_EMAIL=your-email@gmail.com

# Google Sheets Configuration
SheetID=your_google_sheet_id

# Management Team Phone Number (for call transfers)
MANAGEMENT_REDIRECT_NUMBER=+1234567890

# Perplexity API Configuration (optional)
PERPLEXITY_API_KEY=your_perplexity_api_key
```

### Step 2: Google Sheets API Setup

1. **Enable Google Sheets API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Sheets API
   - Create credentials (OAuth 2.0 Client ID for Desktop Application)
   - Download the credentials file

2. **Set up authentication folders**:
   ```bash
   # Place credentials in both locations for different services
   # Main Google Sheets integration:
   cp downloaded_credentials.json ./credentials.json
   
   # Sheets automation utilities:
   cp downloaded_credentials.json ./sheets_automation/credentials.json
   ```

3. **First-time Google Sheets authentication**:
   ```bash
   # Run the sheets automation setup to authenticate and create token
   cd sheets_automation
   python read_sheet.py
   ```
   - This will open your browser for Google OAuth
   - Allow the application to read and write to your Google Sheets
   - A `token.json` file will be created automatically in `sheets_automation/`

### Step 3: Gmail API Setup (for Email Automation)

1. **Enable Gmail API**:
   - In the same Google Cloud Console project
   - Enable the Gmail API
   - Use the same OAuth 2.0 credentials or create new ones
   - Download credentials for Gmail

2. **Set up Gmail authentication**:
   ```bash
   # Place Gmail credentials in email automation folder
   cp downloaded_credentials.json ./email_automation/credentials.json
   ```

3. **First-time Gmail authentication**:
   ```bash
   # Run this once to authenticate and generate token.json for Gmail
   python -c "from email_automation import authenticate_gmail; authenticate_gmail()"
   ```
   - This will open your browser for Google OAuth
   - Allow the application to send emails on your behalf
   - A `token.json` file will be created automatically in `email_automation/`

### Step 3: Create Virtual Environment and Install Dependencies

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

### Step 4: Run the Application

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

4. **Gmail API**: Set up Google Cloud Project
   - Used for automated email follow-up system
   - Requires OAuth 2.0 authentication (see Step 2 above)

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
3. **Department Selection**: Caller chooses from 7 departments or voicemail
4. **Information Collection**: AI systematically collects:
   - Full name
   - Phone number
   - Email address
   - Organization/company
5. **Data Storage**: Information saved to both:
   - Local `Progress.csv` file
   - Google Sheets (department-specific worksheet)
6. **SMS Follow-up**: Automatic SMS sent with Faith Agency website link
7. **Email Follow-up**: Personalized welcome email sent to collected email address
8. **Call Transfer**: For management requests, calls are transferred with answer detection
9. **Call Completion**: 24-hour follow-up promise given to caller

## 🏢 Department Options

1. **¡VIVA! Audio Bible** - Spanish Audio Bible team
2. **Casting & Talent** - Talent and casting department  
3. **Press & Media Relations** - Media relations and press inquiries
4. **Tech Support** - App and technology support
5. **Sales & Partnerships** - Partnerships and sales
6. **Management Team** - Executive team access with call transfer
7. **General Voicemail** - General message system

## 📊 Data Collection & Google Sheets Integration

### CSV Data Storage
All call data is automatically saved to `Progress.csv` with the following fields:

- `timestamp` - Call completion time
- `callSid` - Twilio call identifier
- `departmentCode` - Selected department code
- `departmentName` - Full department name
- `callerPhone` - Caller's phone number
- `name` - Collected name
- `phone` - Collected phone number
- `email` - Collected email address
- `organization` - Company/organization

### Google Sheets Integration
Contact data is automatically synchronized to Google Sheets with:

- **Department-specific worksheets**: Each department has its own worksheet
- **Filtered data**: Only relevant contact fields are sent to sheets (excludes internal tracking data)
- **Real-time sync**: Data is saved immediately after collection
- **Standard columns**: All worksheets use consistent column headers:
  - `timestamp`, `callerPhone`, `name`, `phone`, `email`, `organization`

### Department Worksheet Mapping
- `viva` → ¡VIVA! Audio Bible
- `casting` → Casting & Talent  
- `press` → Press & Media Relations
- `support` → Tech Support
- `sales` → Sales & Partnerships
- `management` → Management Team
- `voicemail` → General Voicemail

## � API Configuration

### Required API Keys

1. **Twilio Account**: Sign up at [twilio.com](https://twilio.com)
   - Get Account SID, Auth Token, and Phone Number
   - Configure webhook URL to point to your server's `/api/incoming` endpoint

2. **Ultravox API**: Get API key from [ultravox.ai](https://ultravox.ai)
   - Used for AI voice conversations

3. **OpenAI API**: Get API key from [openai.com](https://openai.com)
   - Used for intelligent contact information extraction

4. **Google APIs**: Set up Google Cloud Project
   - **Gmail API**: Used for automated email follow-up system
   - **Google Sheets API**: Used for data synchronization and department management
   - Requires OAuth 2.0 authentication (see setup steps above)

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

## 🛠️ Development

### Adding New Features

- **New departments**: Update department mappings in `functions.py` and `google_sheet.py`
- **SMS templates**: Modify `sms_sending()` function in `twilio_sms.py`
- **Data fields**: Update CSV fieldnames and Google Sheets column mappings
- **AI prompts**: Modify conversation flow in `get_single_flow_prompt()`

### Google Sheets Management

Use the sheets automation utility for management tasks:

```bash
cd sheets_automation
python read_sheet.py
```

Available options:
- Read specific worksheets
- Set up standard columns across all department worksheets
- Manage worksheet structure

### Monitoring

Check console output for:
- Call status updates and transfer monitoring
- AI extraction results
- Google Sheets synchronization status
- SMS and email sending confirmations
- Error messages and debugging info

## 📋 Dependencies

Key packages (see `requirements.txt` for complete list):

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `twilio` - Twilio API integration
- `openai` - OpenAI API client
- `httpx` - HTTP client for Ultravox API
- `google-api-python-client` - Google APIs integration
- `google-auth` - Google authentication
- `python-dotenv` - Environment variable management

## 🚨 Troubleshooting

### Common Issues

- **SMS not sending**: Check Twilio credentials and phone number format
- **AI not responding**: Verify Ultravox API key and network connectivity
- **Data extraction failing**: Check OpenAI API key and quota
- **Webhook errors**: Ensure ngrok tunnel is active for local development
- **Google Sheets not updating**: Verify credentials.json and token.json files in correct folders
- **Email not sending**: Check Gmail API credentials and authentication scope
- **Call transfers failing**: Verify MANAGEMENT_PHONE number in .env file

### Authentication Issues

If you encounter Google API authentication errors:

1. **Delete existing tokens**:
   ```bash
   rm email_automation/token.json
   rm sheets_automation/token.json
   ```

2. **Re-authenticate**:
   ```bash
   # For Gmail
   python -c "from email_automation import authenticate_gmail; authenticate_gmail()"
   
   # For Google Sheets
   cd sheets_automation && python read_sheet.py
   ```

3. **Check OAuth scopes**: Ensure your Google Cloud Console project has the correct scopes enabled:
   - Gmail API: `https://www.googleapis.com/auth/gmail.send`
   - Sheets API: `https://www.googleapis.com/auth/spreadsheets`

## 📄 License

This project is proprietary to Faith Agency.