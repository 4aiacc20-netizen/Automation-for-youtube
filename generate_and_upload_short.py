import os
from moviepy.editor import *
from google.cloud import texttospeech
import datetime
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ----------------- CONFIG -----------------
SCRIPT_TEXT = "Success is not final, failure is not fatal. It is the courage to continue that counts."
VIDEO_DURATION = 15  # seconds
BACKGROUND_VIDEO = "background.mp4"  # optional: stock or animated background
MUSIC_FILE = "background_music.mp3"  # optional: royalty-free music
OUTPUT_VIDEO = "short.mp4"

# ----------------- STEP 1: TEXT TO SPEECH -----------------
from gtts import gTTS
tts = gTTS(text=SCRIPT_TEXT, lang="en")
tts.save("audio.mp3")

# ----------------- STEP 2: CREATE VIDEO -----------------
clips = []

# Background: stock video or black screen
if os.path.exists(BACKGROUND_VIDEO):
    bg_clip = VideoFileClip(BACKGROUND_VIDEO).subclip(0, VIDEO_DURATION).resize((720,1280))
else:
    bg_clip = ColorClip(size=(720,1280), color=(0,0,0), duration=VIDEO_DURATION)

clips.append(bg_clip)

# Text overlay
txt_clip = TextClip(SCRIPT_TEXT, fontsize=50, color='white', font='Arial', method='caption', size=(700, None))
txt_clip = txt_clip.set_position('center').set_duration(VIDEO_DURATION)
clips.append(txt_clip)

# Merge clips
final_video = CompositeVideoClip(clips)

# Add audio
audio_clip = AudioFileClip("audio.mp3")
if os.path.exists(MUSIC_FILE):
    music_clip = AudioFileClip(MUSIC_FILE).volumex(0.2)
    audio_clip = CompositeAudioClip([audio_clip, music_clip])

final_video = final_video.set_audio(audio_clip)

# Export final video
final_video.write_videofile(OUTPUT_VIDEO, fps=25, codec='libx264', audio_codec='aac')

print("✅ High-quality short.mp4 created!")

# ----------------- STEP 3: UPLOAD TO YOUTUBE -----------------
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
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    },
    media_body=MediaFileUpload(OUTPUT_VIDEO)
)

response = request.execute()
print("✅ Uploaded:", response)
