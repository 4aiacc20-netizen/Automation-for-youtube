import os
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import subprocess
import datetime
import textwrap
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.auth.transport.requests

# ---------------- CONFIG ----------------
SCRIPT_TEXT = "Success is not final, failure is not fatal. It is the courage to continue that counts."
VIDEO_DURATION = 15
VIDEO_RES = (720, 1280)
OUTPUT_VIDEO = "short.mp4"
AUDIO_FILE = "audio.mp3"
IMAGE_FILE = "frame.png"
MUSIC_FILE = "background_music.mp3"  # optional, set to None if not used

# ---------------- STEP 1: TEXT TO SPEECH ----------------
tts = gTTS(text=SCRIPT_TEXT, lang="en")
tts.save(AUDIO_FILE)

# ---------------- STEP 2: CREATE IMAGE FRAME ----------------
img = Image.new("RGB", VIDEO_RES, color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# Load font
font_size = 50
try:
    font = ImageFont.truetype("arial.ttf", font_size)
except:
    font = ImageFont.load_default()

# Wrap text to fit width
max_width = VIDEO_RES[0] - 40
lines = textwrap.wrap(SCRIPT_TEXT, width=25)  # adjust width for best fit

# Calculate total height
line_heights = []
for line in lines:
    bbox = draw.textbbox((0, 0), line, font=font)
    line_heights.append(bbox[3] - bbox[1])
total_height = sum(line_heights) + (len(lines)-1)*10  # 10px spacing

# Draw each line centered
current_y = (VIDEO_RES[1] - total_height) // 2
for i, line in enumerate(lines):
    bbox = draw.textbbox((0,0), line, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (VIDEO_RES[0] - text_w) // 2
    draw.text((x, current_y), line, font=font, fill=(255,255,255))
    current_y += text_h + 10

img.save(IMAGE_FILE)

# ---------------- STEP 3: CREATE VIDEO USING FFMPEG ----------------
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-loop", "1",
    "-i", IMAGE_FILE,
    "-i", AUDIO_FILE,
    "-c:v", "libx264",
    "-t", str(VIDEO_DURATION),
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
]

# Add background music if exists
if MUSIC_FILE and os.path.exists(MUSIC_FILE):
    ffmpeg_cmd.extend(["-i", MUSIC_FILE, "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=shortest"])
else:
    ffmpeg_cmd.extend(["-shortest"])

ffmpeg_cmd.append(OUTPUT_VIDEO)
subprocess.run(ffmpeg_cmd)

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
creds.refresh(google.auth.transport.requests.Request())

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
