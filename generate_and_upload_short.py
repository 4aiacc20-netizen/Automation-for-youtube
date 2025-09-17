import os
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import subprocess
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------- CONFIG ----------------
SCRIPT_TEXT = "Success is not final, failure is not fatal. It is the courage to continue that counts."
VIDEO_DURATION = 15
VIDEO_RES = (720, 1280)
OUTPUT_VIDEO = "short.mp4"
AUDIO_FILE = "audio.mp3"
IMAGE_FILE = "frame.png"

# ---------------- STEP 1: TEXT TO SPEECH ----------------
tts = gTTS(text=SCRIPT_TEXT, lang="en")
tts.save(AUDIO_FILE)

# ---------------- STEP 2: CREATE IMAGE FRAME ----------------
img = Image.new("RGB", VIDEO_RES, color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# Use default font; for custom font, provide path to .ttf
font_size = 50
try:
    font = ImageFont.truetype("arial.ttf", font_size)
except:
    font = ImageFont.load_default()

text_w, text_h = draw.textsize(SCRIPT_TEXT, font=font)
draw.text(
    ((VIDEO_RES[0]-text_w)/2, (VIDEO_RES[1]-text_h)/2),
    SCRIPT_TEXT, font=font, fill=(255, 255, 255)
)
img.save(IMAGE_FILE)

# ---------------- STEP 3: CREATE VIDEO USING FFMPEG ----------------
subprocess.run([
    "ffmpeg", "-y",
    "-loop", "1",
    "-i", IMAGE_FILE,
    "-i", AUDIO_FILE,
    "-c:v", "libx264",
    "-t", str(VIDEO_DURATION),
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-shortest",
    OUTPUT_VIDEO
])

print("✅ short.mp4 created!")

# ---------------- STEP 4: UPLOAD TO YOUTUBE ----------------
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
creds.refresh(Request=google.auth.transport.requests.Request())

youtube = build("youtube", "v3", credentials=creds)

today = datetime.date.today().strftime("%B %d, %Y")
request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": f"Daily Motivation 🚀 {today}",
            "description": SCRIPT_TEXT,
            "tags": ["Motivation", "Shorts", "AI"],
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    },
    media_body=MediaFileUpload(OUTPUT_VIDEO)
)

response = request.execute()
print("✅ Uploaded:", response)
