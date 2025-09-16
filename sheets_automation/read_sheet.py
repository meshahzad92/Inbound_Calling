#!/usr/bin/env python3
"""
Simple Google Sheets Reader
Just reads a Google Sheet and shows its contents
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class SimpleSheetReader:
    def __init__(self, credentials_file="credentials.json", token_file="token.json"):
        """Initialize with Google OAuth credentials"""
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using OAuth"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            creds = None
            
            # Check if token.json exists (stored credentials)
            if os.path.exists(self.token_file):
                try:
                    creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                except Exception as token_error:
                    print(f"⚠️ Error loading existing token: {token_error}")
                    print("🗑️ Removing old token file...")
                    os.remove(self.token_file)
                    creds = None
            
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        print("🔄 Refreshing credentials...")
                        creds.refresh(Request())
                    except Exception as refresh_error:
                        print(f"⚠️ Token refresh failed: {refresh_error}")
                        print("🗑️ Removing old token, will re-authenticate...")
                        if os.path.exists(self.token_file):
                            os.remove(self.token_file)
                        creds = None
                
                # If we still don't have valid credentials, start OAuth flow
                if not creds or not creds.valid:
                    if not os.path.exists(self.credentials_file):
                        print(f"❌ Credentials file not found: {self.credentials_file}")
                        return
                    
                    print("🔐 Starting OAuth authentication...")
                    print("📱 Browser will open for Google login...")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=8080)
                
                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                print("💾 Credentials saved to token.json")
            
            self.service = build('sheets', 'v4', credentials=creds)
            print(f"✅ Connected to Google Sheets")
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("🔧 Try deleting token.json and running again")
    
    def read_sheet(self, sheet_url_or_id):
        """Read and display Google Sheet contents"""
        try:
            # Extract sheet ID from URL if needed
            if "spreadsheets/d/" in sheet_url_or_id:
                start = sheet_url_or_id.find("/spreadsheets/d/") + len("/spreadsheets/d/")
                end = sheet_url_or_id.find("/", start)
                if end == -1:
                    end = sheet_url_or_id.find("#", start)
                if end == -1:
                    sheet_id = sheet_url_or_id[start:]
                else:
                    sheet_id = sheet_url_or_id[start:end]
            else:
                sheet_id = sheet_url_or_id
            
            print(f"📊 Reading sheet: {sheet_id}")
            
            # Get sheet metadata
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            
            print(f"\n📄 Sheet Name: {sheet_metadata.get('properties', {}).get('title', 'Unknown')}")
            print(f"📊 Available Worksheets:")
            
            # List all worksheets
            for i, sheet in enumerate(sheet_metadata.get('sheets', []), 1):
                sheet_title = sheet['properties']['title']
                rows = sheet['properties']['gridProperties']['rowCount']
                cols = sheet['properties']['gridProperties']['columnCount']
                print(f"  {i}. {sheet_title} ({rows} rows x {cols} columns)")
            
            # Read first worksheet data
            if sheet_metadata.get('sheets'):
                first_sheet = sheet_metadata['sheets'][0]['properties']['title']
                print(f"\n📖 Reading data from '{first_sheet}':")
                
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=first_sheet
                ).execute()
                
                values = result.get('values', [])
                
                if values:
                    print(f"📋 Found {len(values)} rows:")
                    # Show first few rows
                    for i, row in enumerate(values[:10]):
                        print(f"  Row {i+1}: {row}")
                    
                    if len(values) > 10:
                        print(f"  ... and {len(values)-10} more rows")
                else:
                    print("📭 No data found in sheet")
            
            return True
            
        except Exception as e:
            print(f"❌ Error reading sheet: {e}")
            return False
    
    def setup_columns_in_all_sheets(self, sheet_url_or_id):
        """Set up standard columns in all worksheets"""
        try:
            # Extract sheet ID from URL if needed
            if "spreadsheets/d/" in sheet_url_or_id:
                start = sheet_url_or_id.find("/spreadsheets/d/") + len("/spreadsheets/d/")
                end = sheet_url_or_id.find("/", start)
                if end == -1:
                    end = sheet_url_or_id.find("#", start)
                if end == -1:
                    sheet_id = sheet_url_or_id[start:]
                else:
                    sheet_id = sheet_url_or_id[start:end]
            else:
                sheet_id = sheet_url_or_id
            
            print(f"📊 Setting up columns in sheet: {sheet_id}")
            
            # Standard column headers for Faith Agency data
            headers = ["timestamp", "callerPhone", "name", "phone", "email", "organization"]
            
            # Get sheet metadata to find all worksheets
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            
            print(f"\n📄 Sheet Name: {sheet_metadata.get('properties', {}).get('title', 'Unknown')}")
            print(f"📝 Setting up columns in all worksheets...")
            
            # Set up headers in each worksheet
            for sheet in sheet_metadata.get('sheets', []):
                worksheet_name = sheet['properties']['title']
                print(f"  📋 Setting up '{worksheet_name}'...")
                
                # Check if worksheet already has headers
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=f"{worksheet_name}!A1:F1"
                ).execute()
                
                existing_data = result.get('values', [])
                
                if existing_data and existing_data[0]:
                    print(f"    ⚠️ '{worksheet_name}' already has data in row 1:")
                    print(f"      {existing_data[0]}")
                    
                    # Ask if user wants to overwrite
                    overwrite = input(f"    ❓ Overwrite headers in '{worksheet_name}'? (y/n): ").lower().strip()
                    if overwrite != 'y':
                        print(f"    ⏭️ Skipping '{worksheet_name}'")
                        continue
                
                # Write headers to the worksheet
                self.service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=f"{worksheet_name}!A1:F1",
                    valueInputOption='RAW',
                    body={'values': [headers]}
                ).execute()
                
                print(f"    ✅ Headers set in '{worksheet_name}': {headers}")
            
            print(f"\n✅ Column setup completed!")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up columns: {e}")
            return False

def main():
    """Main function"""
    print("📊 Google Sheets Manager for Faith Agency")
    print("=" * 50)
    
    # Check for credentials
    if not os.path.exists("credentials.json"):
        print("❌ Missing credentials.json file")
        print("\nTo get this file:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable Google Sheets API")
        print("4. Go to Credentials > Create Credentials > OAuth client ID")
        print("5. Choose 'Desktop application'")
        print("6. Download JSON credentials")
        print("7. Rename to 'credentials.json'")
        return
    
    # Get sheet URL/ID from user
    sheet_input = input("\nEnter Google Sheet URL or ID: ").strip()
    
    if not sheet_input:
        print("❌ No sheet provided")
        return
    
    # Create reader and connect
    reader = SimpleSheetReader()
    if not reader.service:
        print("❌ Failed to connect to Google Sheets")
        return
    
    # Ask what user wants to do
    print("\n📋 What would you like to do?")
    print("1. Read sheet data")
    print("2. Set up columns in all worksheets")
    print("3. Both (read first, then set up columns)")
    
    choice = input("\nEnter your choice (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        print("\n" + "="*50)
        print("📖 READING SHEET DATA")
        print("="*50)
        success = reader.read_sheet(sheet_input)
        
        if success:
            print("\n✅ Sheet read successfully!")
        else:
            print("\n❌ Failed to read sheet")
            return
    
    if choice in ['2', '3']:
        print("\n" + "="*50)
        print("📝 SETTING UP COLUMNS")
        print("="*50)
        print("This will add these columns to all worksheets:")
        print("📋 timestamp, callerPhone, name, phone, email, organization")
        
        confirm = input("\n❓ Continue with column setup? (y/n): ").lower().strip()
        
        if confirm == 'y':
            success = reader.setup_columns_in_all_sheets(sheet_input)
            
            if success:
                print("\n✅ Column setup completed successfully!")
                print("🎯 All worksheets now have standard Faith Agency columns")
            else:
                print("\n❌ Failed to set up columns")
        else:
            print("⏭️ Column setup cancelled")
    
    if choice not in ['1', '2', '3']:
        print("❌ Invalid choice")
        return

if __name__ == "__main__":
    main()