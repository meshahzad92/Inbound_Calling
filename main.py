import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import all functions from functions.py
from functions import (
    get_single_flow_prompt,
    create_ultravox_call,
    monitor_single_flow_call
)

load_dotenv()

# Global dictionary to track active calls
call_mapping = {}  # Maps Ultravox call ID to Twilio Call SID

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


ULTRAVOX_CALL_CONFIG = {
    "model": "fixie-ai/ultravox",
    "voice": "Jessica",
    "temperature": 0.3,
    "firstSpeakerSettings": {"agent": {}},
    "medium": {"twilio": {}},
    "selectedTools": [
         {
            "toolName": "queryCorpus",
            "parameterOverrides": {
                "corpus_id": "009a36f2-0d62-4eb2-b621-9d6302194b40", # Replace with your actual corpus ID
                "max_results": 5
            }
        },
        {
            "toolName": "transferCall",
        },
        {
            "toolName": "pauseForSeconds",
        },
        {
            "toolName": "hangUp"  
        },
         "inactivityMessages": [
        {
            "duration": "5s", 
            "message": "I didn't hear a selection. Let's try it this way: Press 1 for Sales and Partnerships, Press 2 for VIVA Audio Bible, Press 3 for Casting and Talent, Press 4 for Press and Media, Press 5 for Technical Support, Or press 0 to leave a message."
        }
    ]
    ]
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
            
            # Store mapping: Ultravox Call ID → Twilio Call SID
            call_mapping[call_id] = call_sid
            print(f"📝 Stored call mapping: {call_id} → {call_sid}")
            
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

# Transfer call endpoint for Ultravox tool calls
@app.post("/api/transfer")
async def transfer_call(request: Request):
    """Handle transfer requests from Ultravox"""
    try:
        print("🎯 TRANSFER ENDPOINT HIT! Tool is working!")
        # Import here to avoid circular imports
        from functions import handle_transfer, handle_transfer_background, quick_transfer_check
        import os
        
        data = await request.json()
        received_call_sid = data.get("callSid")
        destination_number = data.get("destinationNumber")
        transfer_reason = data.get("transferReason", "Caller requested transfer")
        
        print(f"📥 Received transfer request: {data}")
        
        # Handle placeholder call_sid by finding the real Twilio Call SID
        real_call_sid = None
        if received_call_sid == "active_call_sid" or not received_call_sid:
            # Try to find the real Call SID from our mapping
            # Since we don't have the Ultravox call ID here, we'll use the most recent one
            if call_mapping:
                real_call_sid = list(call_mapping.values())[-1]  # Get the most recent
                print(f"🔍 Found real Call SID: {real_call_sid}")
            else:
                print("⚠️ No call mapping found, cannot transfer")
                return {"error": "Cannot transfer: No active call found", "status": "failed"}
        else:
            real_call_sid = received_call_sid
        
        # Handle placeholder destination number
        if destination_number in ["management_redirect_number", "management_number", "MANAGEMENT_REDIRECT_NUMBER", "MANAGEMENT_NUMBER"] or not destination_number:
            destination_number = os.getenv("MANAGEMENT_REDIRECT_NUMBER")
            print(f"🔧 Using management number from .env: {destination_number}")
        
        if not destination_number:
            return {"error": "No management redirect number configured", "status": "failed"}
        
        # Start the transfer process in background and respond immediately to Ultravox
        import asyncio
        
        # Quick transfer check - test management availability first
        result = await quick_transfer_check(real_call_sid, destination_number)
        
        # Store transfer result for later use in monitoring
        from functions import store_transfer_status
        store_transfer_status(real_call_sid, result.get("status", "failed"))
        
        print(f"🔄 Transfer request: {transfer_reason}")
        print(f"📞 Using real Call SID: {real_call_sid}")
        print(f"🎯 To number: {destination_number}")
        print(f"📊 Quick check result: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in transfer endpoint: {e}")
        return {"status": "failed", "message": f"Transfer endpoint error: {str(e)}"}


@app.get("/api/pause")
async def pause_endpoint(seconds: int = 20):
    """Simple pause endpoint for Ultravox tools"""
    import time
    call_start = time.time()
    call_id = int(call_start * 1000) % 10000  # Simple call ID
    
    try:
        print(f"🔥 PAUSE CALL #{call_id} STARTED - Requested: {seconds} seconds")
        print(f"⏰ Start time: {time.strftime('%H:%M:%S', time.localtime(call_start))}")
        
        sleep_start = time.time()
        await asyncio.sleep(seconds)
        sleep_end = time.time()
        
        actual_sleep_time = sleep_end - sleep_start
        total_time = sleep_end - call_start
        
        print(f"✅ PAUSE CALL #{call_id} COMPLETED")
        print(f"⏱️  Requested: {seconds}s | Actual sleep: {actual_sleep_time:.2f}s | Total time: {total_time:.2f}s")
        print(f"🏁 End time: {time.strftime('%H:%M:%S', time.localtime(sleep_end))}")
        
        from fastapi.responses import JSONResponse
        
        response_data = {
            "status": "success", 
            "duration": seconds,
            "actual_duration": round(actual_sleep_time, 2),
            "total_time": round(total_time, 2),
            "call_id": call_id
        }
        
        # Add headers to speed up Ultravox processing
        return JSONResponse(
            content=response_data,
            headers={
                "Cache-Control": "no-cache",
                "Connection": "close",
                "Content-Type": "application/json"
            }
        )
    except Exception as e:
        error_time = time.time()
        total_time = error_time - call_start
        print(f"❌ PAUSE CALL #{call_id} ERROR after {total_time:.2f}s: {e}")
        error_data = {
            "status": "error", 
            "message": str(e), 
            "duration": 0,
            "total_time": round(total_time, 2),
            "call_id": call_id
        }
        
        return JSONResponse(
            content=error_data,
            headers={
                "Cache-Control": "no-cache",
                "Connection": "close",
                "Content-Type": "application/json"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=int(PORT))