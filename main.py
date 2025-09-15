import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv

# Import all functions from functions.py
from functions import (
    get_single_flow_prompt,
    create_ultravox_call,
    monitor_single_flow_call
)

load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", "8000")

# Initialize FastAPI app
app = FastAPI(title="Inbound Calling System", description="AI-powered inbound call management system")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Handle incoming calls
ULTRAVOX_CALL_CONFIG = {
    'model': 'fixie-ai/ultravox',
    'voice': 'Mark',
    'temperature': 0.3,
    'firstSpeaker': 'FIRST_SPEAKER_AGENT',
    'medium': {"twilio": {}}
}

@app.post("/api/incoming", response_class=HTMLResponse)
async def incoming_call(request: Request):
    try:
        # Get form data from the request
        form_data = await request.form()
        caller_phone = form_data.get("From", "Unknown")
        call_sid = form_data.get("CallSid", "")
        
        print(f"Incoming call from {caller_phone}, CallSid: {call_sid}")
        print("Starting single voice flow conversation...")
        
        twiml = VoiceResponse()
        #twiml.say("Connecting you to our AI assistant.")
        
        # Create Ultravox call configuration with single flow prompt
        call_config = ULTRAVOX_CALL_CONFIG.copy()
        call_config['systemPrompt'] = get_single_flow_prompt()
        
        try:
            response = await create_ultravox_call(call_config)
            join_url = response.get('joinUrl')
            call_id = response.get('callId')
            
            print(f"Created single flow Ultravox call {call_id}")
            
            # Start monitoring task for complete conversation
            asyncio.create_task(monitor_single_flow_call(call_id, caller_phone, call_sid))
            
            # Connect to Ultravox using proper TwiML
            connect = twiml.connect()
            connect.stream(url=join_url, name='ultravox')
            
        except Exception as e:
            print(f"Error creating Ultravox call: {e}")
            twiml.say("We're experiencing technical difficulties. Please try again later.")
            
        return HTMLResponse(content=str(twiml), media_type="text/xml")
        
    except Exception as e:
        print(f"Error in incoming_call: {e}")
        twiml = VoiceResponse()
        twiml.say("We're experiencing technical difficulties. Please try again later.")
        return HTMLResponse(content=str(twiml), media_type="text/xml")

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Inbound Calling System"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=int(PORT))