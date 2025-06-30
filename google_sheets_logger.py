import requests
import datetime

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbysJWNPLQkQ1rygCLSON1VMYWjS9-HCv_2a4a96FUVZPxqyHe9OzOZIJi8Xps8pkdz3eg/exec"  # Replace with your deployed script URL

def log_to_google_sheet(user_id, user_details, time, transcript, arguments, success):
    data = {
        "user_id": user_id,
        "user_details": user_details,
        "time": time,
        "transcript": transcript,
        "arguments": arguments,
        "success": success
    }
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to log to Google Sheets: {e}")
        return None
