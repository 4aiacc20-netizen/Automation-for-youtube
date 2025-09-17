import os
import requests
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import subprocess
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.auth.transport.requests
import textwrap

# ---------------- CONFIG ----------------
SCRIPT_TEXT = "Success is not final, failure is not fatal. It is the courage to continue that counts."
VIDEO_RES = (720, 1280)
OUTPUT_VIDEO = "short_final.mp4"
AUDIO_FILE = "tts_audio.mp3"
MUSIC_FILE = "background_music.mp3"  # optional
FONT_SIZE = 70
CLIP_DURATION = 5  # seconds per image
TMP_VIDEO_CLIPS = []

# Unsplash URLs for copyright-free images
IMAGE_URLS = [
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=720&q=80",
    "https://images.unsplash.com/photo-1495567720989-cebdbdd97913?auto=format&fit=crop&w=720&q=80"
]

# ---------------- STEP 0: DOWNLOAD IMAGES ----------------
IMAGE_FILES = []
for idx, url in enumerate(IMAGE_URLS):
    img_file = f"bg_{idx}.jpg"
    r = requests.get(url)
    with open(img_file, "wb") as f:
        f.write(r.content)
    IMAGE_FILES.append(img_file)
print("✅ Background images downloaded")

# ---------------- STEP 1: TEXT TO SPEECH ----------------
tts = gTTS(text=SCRIPT_TEXT, lang="en")
tts.save(AUDIO_FILE)
print("✅ TTS audio generated")

# ---------------- STEP 2: CREATE IMAGE FRAMES WITH TEXT ----------------
def create_text_image(bg_image_path, output_path):
    bg = Image.open(bg_image_path).convert("RGB").resize(VIDEO_RES)
    draw = ImageDraw.Draw(bg)
    
    try:
        font = ImageFont.truetype("arial.ttf", FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # wrap text
    lines = textwrap.wrap(SCRIPT_TEXT, width=25)
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    total_height = sum(line_heights) + (len(lines)-1)*10

    # draw each line centered
    current_y = (VIDEO_RES[1] - total_height) // 2
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (VIDEO_RES[0] - text_w) // 2
        # shadow
        draw.text((x+2, current_y+2), line, font=font, fill=(0,0,0))
        draw.text((x, current_y), line, font=font, fill=(255,255,255))
        current_y += text_h + 10

    bg.save(output_path)

# create frames
frame_files = []
for idx, img_file in enumerate(IMAGE_FILES):
    frame_file = f"frame_{idx}.png"
    create_text_image(img_file, frame_file)
    frame_files.append(frame_file)

# ---------------- STEP 3: CREATE VIDEO CLIPS FROM IMAGES ----------------
for idx, frame_file in enumerate(frame_files):
    clip_file = f"clip_{idx}.mp4"
    TMP_VIDEO_CLIPS.append(clip_file)
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_file,
        "-c:v", "libx264",
        "-t", str(CLIP_DURATION),
        "-pix_fmt", "yuv420p",
        "-vf", "zoompan=z='min(zoom+0.0015,1.05)':d=125",
        clip_file
    ]
    subprocess.run(ffmpeg_cmd)

# ---------------- STEP 4: CONCAT VIDEO CLIPS ----------------
with open("file_list.txt", "w") as f:
    for clip in TMP_VIDEO_CLIPS:
        f.write(f"file '{clip}'\n")

concat_video = "video_no_audio.mp4"
subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "file_list.txt",
    "-c", "copy",
    concat_video
])

# ---------------- STEP 5: ADD AUDIO (TTS + MUSIC) ----------------
if MUSIC_FILE and os.path.exists(MUSIC_FILE):
    final_audio = "final_audio.mp3"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", AUDIO_FILE,
        "-i", MUSIC_FILE,
        "-filter_complex", "[0:a]volume=1[a0];[1:a]volume=0.2[a1];[a0][a1]amix=inputs=2:duration=shortest",
        final_audio
    ])
else:
    final_audio = AUDIO_FILE

subprocess.run([
    "ffmpeg", "-y",
    "-i", concat_video,
    "-i", final_audio,
    "-c:v", "copy",
    "-c:a", "aac",
    "-shortest",
    OUTPUT_VIDEO
])
print(f"✅ Video created: {OUTPUT_VIDEO}")

# ---------------- STEP 6: UPLOAD TO YOUTUBE ----------------
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
