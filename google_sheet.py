#!/usr/bin/env python3
"""
Google Sheets Integration for Faith Agency
Saves call data to appropriate department worksheets
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GoogleSheetManager:
    def __init__(self):
        """Initialize Google Sheets manager"""
        self.sheet_id = os.getenv("SheetID")
        self.service = None
        self.credentials_file = "sheets_automation/credentials.json"
        self.token_file = "sheets_automation/token.json"
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate using existing token from sheets_automation folder"""
        try:
            if not os.path.exists(self.token_file):
                print(f"❌ Token file not found: {self.token_file}")
                print("Please run the sheets_automation/read_sheet.py first to authenticate")
                return False
            
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            # Refresh token if needed
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('sheets', 'v4', credentials=creds)
            print(f"✅ Google Sheets authenticated successfully")
            return True
            
        except Exception as e:
            print(f"❌ Google Sheets authentication failed: {e}")
            return False
    
    def get_worksheet_name(self, department_name):
        """Convert department name to worksheet name"""
        # Mapping of department names to worksheet names
        department_mapping = {
            "¡VIVA! Audio Bible": "¡VIVA! Audio Bible",
            "Casting & Talent": "Casting & Talent", 
            "Press & Media Relations": "Press & Media Relations",
            "Tech Support": "Tech Support",
            "Sales & Partnerships": "Sales & Partnerships",
            "Management Team": "Management Team",
            "General Voicemail": "General Voicemail",
            "Unknown Department": "General Voicemail"  # Default fallback
        }
        
        return department_mapping.get(department_name, "General Voicemail")
    
    def append_call_data(self, call_data):
        """
        Append call data to the appropriate worksheet
        Args:
            call_data (dict): Call data containing department info and contact details
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                print("❌ Google Sheets service not authenticated")
                return False

            if not self.sheet_id:
                print("❌ SheetID not found in .env file")
                return False

            # Get the worksheet name based on department
            department_name = call_data.get("departmentName", "Unknown Department")
            worksheet_name = self.get_worksheet_name(department_name)

            print(f"📊 Saving to worksheet: {worksheet_name}")

            # Prepare data row - match the new column order
            row_data = [
                call_data.get("timestamp", ""),
                call_data.get("callerPhone", ""),
                call_data.get("name", ""),
                call_data.get("email", ""),
                call_data.get("organization", ""),
                call_data.get("purpose", ""),
                call_data.get("status", "Not answered"),
                call_data.get("summary", "")
            ]

            # Append data to the worksheet
            range_name = f"{worksheet_name}!A:H"

            body = {
                'values': [row_data]
            }

            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            print(f"✅ Data saved to {worksheet_name} - {result.get('updates', {}).get('updatedCells', 0)} cells updated")
            return True

        except Exception as e:
            print(f"❌ Error saving to Google Sheets: {e}")
            return False

def save_to_google_sheets(call_data):
    """
    Simple function to save call data to Google Sheets
    
    Args:
        call_data (dict): Call data from monitor_single_flow_call
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        manager = GoogleSheetManager()
        if manager.service:
            return manager.append_call_data(call_data)
        else:
            print("❌ Failed to initialize Google Sheets manager")
            return False
    except Exception as e:
        print(f"❌ Google Sheets integration error: {e}")
        return False

# Test function
def test_google_sheets():
    """Test the Google Sheets integration"""
    print("🧪 Testing Google Sheets Integration")
    print("=" * 40)
    
    # Sample test data
    test_data = {
        "timestamp": "2025-09-17 12:00:00",
        "callSid": "TEST123",
        "departmentCode": "viva",
        "departmentName": "¡VIVA! Audio Bible",
        "callerPhone": "+1234567890",
        "name": "Test User",
        "email": "test@example.com",
        "organization": "Test Organization",
        "status": "Not answered"
    }
    
    success = save_to_google_sheets(test_data)
    
    if success:
        print("✅ Google Sheets integration test successful!")
    else:
        print("❌ Google Sheets integration test failed!")
    
    return success

if __name__ == "__main__":
    test_google_sheets()