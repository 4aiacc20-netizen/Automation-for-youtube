import os
from gtts import gTTS
import subprocess
import datetime
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ============ STEP 1: DAILY SCRIPT ============
script_text = "Success is not final, failure is not fatal. It is the courage to continue that counts."

# ============ STEP 2: TEXT TO SPEECH ==========
tts = gTTS(text=script_text, lang="en")
tts.save("audio.mp3")

# ============ STEP 3: CREATE VIDEO WITH FFMPEG ============
# Background (15s black screen + centered text)
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=15",
    "-vf", f"drawtext=text='{script_text}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "video.mp4"
])

# Merge video + audio
subprocess.run([
    "ffmpeg", "-y",
    "-i", "video.mp4", "-i", "audio.mp3",
    "-c:v", "copy", "-c:a", "aac", "-shortest",
    "short.mp4"
])

print("✅ short.mp4 created!")

# ============ STEP 4: UPLOAD TO YOUTUBE ============
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

today = datetime.date.today().strftime("%B %d, %Y")

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": f"Daily Motivation 🚀 {today}",
            "description": script_text,
            "tags": ["Motivation", "Shorts", "AI"],
            "categoryId": "22"
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
