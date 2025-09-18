import os
import requests
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import subprocess
import datetime
import textwrap
import random
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.auth.transport.requests

# ---------------- CONFIG ----------------
CLIP_DURATION = 5  # seconds per image
MUSIC_FILE = "background_music.mp3"  # optional background music
VIDEO_SHORTS_RES = (720, 1280)  # vertical 9:16
FALLBACK_IMAGE = "fallback.jpg"  # backup image
HASHTAGS = "#motivation #shorts #inspiration #mindset #success"

# ---------------- STEP 1: FETCH RANDOM QUOTE ----------------
quote_resp = requests.get("https://zenquotes.io/api/random")
if quote_resp.status_code == 200:
    data = quote_resp.json()[0]
    SCRIPT_TEXT = f"{data['q']}\n\n— {data['a']}"  # ✅ clean quote + author
else:
    SCRIPT_TEXT = "Believe in yourself and all that you are.\n\n— Unknown"
print("✅ Today's Quote:", SCRIPT_TEXT)

# ---------------- STEP 2: DOWNLOAD IMAGES ----------------
def download_image(url, filename):
    try:
        r = requests.get(url, allow_redirects=True, timeout=10)
        if r.status_code == 200 and r.headers["Content-Type"].startswith("image"):
            with open(filename, "wb") as f:
                f.write(r.content)
            return True
    except Exception as e:
        print("⚠️ Image download failed:", e)
    return False

IMAGE_URLS = [
    "https://source.unsplash.com/random/720x1280/?motivation",
    "https://source.unsplash.com/random/720x1280/?nature",
    "https://source.unsplash.com/random/720x1280/?success",
    "https://source.unsplash.com/random/720x1280/?life",
]

IMAGE_FILES = []
for idx, url in enumerate(IMAGE_URLS):
    img_file = f"bg_{idx}.jpg"
    if download_image(url, img_file):
        IMAGE_FILES.append(img_file)

if not IMAGE_FILES:
    print("⚠️ Using fallback image")
    IMAGE_FILES = [FALLBACK_IMAGE]

print("✅ Background images ready")

# ---------------- STEP 3: TTS AUDIO ----------------
AUDIO_FILE = "tts_audio.mp3"
tts = gTTS(text=SCRIPT_TEXT, lang="en")
tts.save(AUDIO_FILE)
print("✅ TTS audio generated")

# ---------------- STEP 4: CREATE TEXT IMAGE ----------------
def create_text_image(bg_image_path, output_path, video_res, text):
    try:
        bg = Image.open(bg_image_path).convert("RGB").resize(video_res)
    except Exception as e:
        print(f"⚠️ Failed to load {bg_image_path}, using plain background. Error: {e}")
        bg = Image.new("RGB", video_res, color=(20, 20, 20))  # dark fallback bg

    draw = ImageDraw.Draw(bg)

    # Bigger font (15% of height)
    font_size = int(video_res[1] * 0.15)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Wrap text properly
    max_chars = int(video_res[0] / (font_size * 0.6))
    wrapped_text = textwrap.fill(text, width=max_chars)

    # Measure with multiline
    text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    x = (video_res[0] - text_w) // 2
    y = (video_res[1] - text_h) // 2

    # Shadow + text
    shadow_offset = 4
    draw.multiline_text((x+shadow_offset, y+shadow_offset), wrapped_text, font=font, fill="black", align="center")
    draw.multiline_text((x, y), wrapped_text, font=font, fill="white", align="center")

    bg.save(output_path)
    print(f"✅ Created text image: {output_path}")
    return output_path

# ---------------- STEP 5: CREATE VIDEO ----------------
def create_video(frame_files, video_res, output_file):
    TMP_VIDEO_CLIPS = []
    for idx, frame_file in enumerate(frame_files):
        clip_file = f"clip_{idx}.mp4"
        TMP_VIDEO_CLIPS.append(clip_file)
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", frame_file,
            "-vf", f"scale={video_res[0]}:{video_res[1]},format=yuv420p",
            "-t", str(CLIP_DURATION),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            clip_file
        ]
        subprocess.run(ffmpeg_cmd)
    
    # Concatenate
    with open("file_list.txt", "w") as f:
        for clip in TMP_VIDEO_CLIPS:
            f.write(f"file '{clip}'\n")

    concat_video = f"{output_file}_no_audio.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "file_list.txt",
        "-c", "copy",
        concat_video
    ])

    # Mix audio
    if MUSIC_FILE and os.path.exists(MUSIC_FILE):
        final_audio = f"{output_file}_audio.mp3"
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
        "-c:v", "libx264",  # re-encode for Shorts
        "-c:a", "aac",
        "-shortest",
        output_file
    ])
    print(f"✅ Video created: {output_file}")

# ---------------- STEP 6: GENERATE SHORTS ----------------
frame_files_shorts = []
for idx, img_file in enumerate(IMAGE_FILES):
    frame_file = f"frame_shorts_{idx}.png"
    create_text_image(img_file, frame_file, VIDEO_SHORTS_RES, SCRIPT_TEXT)
    frame_files_shorts.append(frame_file)

create_video(frame_files_shorts, VIDEO_SHORTS_RES, "shorts_video.mp4")

# ---------------- STEP 7: UPLOAD TO YOUTUBE ----------------
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
            "title": f"Daily Motivation 🚀 {today} #Shorts",
            "description": f"{SCRIPT_TEXT}\n\n{HASHTAGS}",
            "tags": ["Motivation", "Shorts", "Inspiration", "Success", "Mindset"],
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    },
    media_body=MediaFileUpload("shorts_video.mp4")
)
response = request.execute()
print("✅ Uploaded Shorts video:", response)
