import os
from gtts import gTTS
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import datetime

# ============ STEP 1: DAILY SCRIPT ==============
script_text = "Success is not final, failure is not fatal. It is the courage to continue that counts."

# ============ STEP 2: TEXT TO SPEECH =============
tts = gTTS(text=script_text, lang="en")
tts.save("audio.mp3")

# ============ STEP 3: BACKGROUND VIDEO ============
clip_duration = 15  # 15s short
bg_clip = mp.ColorClip(size=(720, 1280), color=(30, 30, 30), duration=clip_duration)  # black bg

# Add text overlay
txt_clip = mp.TextClip(
    script_text,
    fontsize=60,
    color='white',
    method='caption',
    size=(680, None),
    align='center'
).set_position('center').set_duration(clip_duration)

# Add audio
audio = mp.AudioFileClip("audio.mp3")

# Combine everything
final_clip = mp.CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio)
final_clip.write_videofile("short.mp4", fps=24)

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
