import os
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load from secrets
CLIENT_ID = os.getenv("YT_CLIENT_ID")
CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)

creds.refresh(google.auth.transport.requests.Request())
youtube = build("youtube", "v3", credentials=creds)

# Example: upload your short.mp4
request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Daily Auto-Generated Short 🚀",
            "description": "Uploaded automatically via GitHub Actions",
            "tags": ["AI", "Shorts", "Automation"],
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    },
    media_body=MediaFileUpload("short.mp4")
)

response = request.execute()
print("✅ Uploaded:", response)
