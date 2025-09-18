import os
import random
import requests
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ===============================
# SETTINGS
# ===============================
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

VIDEO_RES = (1280, 720)   # Normal video
SHORTS_RES = (720, 1280)  # Shorts (portrait)

FPS = 30
DURATION = 10  # seconds

OUTPUT_VIDEO = "daily_video.mp4"
OUTPUT_SHORT = "daily_short.mp4"

SCRIPT_TEXT = "Success is getting what you want. Happiness is wanting what you get. — Dale Carnegie"

# ===============================
# GET DAILY QUOTE
# ===============================
def get_daily_quote():
    try:
        res = requests.get("https://zenquotes.io/api/random")
        if res.status_code == 200:
            data = res.json()[0]
            return f"{data['q']} — {data['a']}"
    except Exception as e:
        print("⚠️ Quote API failed:", e)
    return SCRIPT_TEXT


# ===============================
# DOWNLOAD RANDOM IMAGE
# ===============================
def download_background():
    url = "https://source.unsplash.com/random/1280x720/?nature,landscape"
    img_file = "bg.jpg"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(img_file, "wb") as f:
                f.write(r.content)
            print("✅ Background image downloaded")
            return img_file
    except Exception as e:
        print("⚠️ Image download failed:", e)

    # fallback plain white
    bg = Image.new("RGB", VIDEO_RES, (255, 255, 255))
    bg.save(img_file)
    return img_file


# ===============================
# CREATE TEXT IMAGE
# ===============================
def create_text_image(bg_image_path, output_path, video_res, text):
    try:
        bg = Image.open(bg_image_path).convert("RGB").resize(video_res)
    except Exception as e:
        print(f"⚠️ Failed to load {bg_image_path}, using plain background. Error: {e}")
        bg = Image.new("RGB", video_res, color=(255, 255, 255))

    draw = ImageDraw.Draw(bg)

    # Font scaling
    font_size = int(video_res[1] * 0.07)
    font = ImageFont.truetype("arial.ttf", font_size)

    # Wrap text
    wrapped_text = textwrap.fill(text, width=40)

    # Measure
    text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    # Center
    x = (video_res[0] - text_w) // 2
    y = (video_res[1] - text_h) // 2

    # Shadow + Text
    shadow_offset = 3
    draw.text((x+shadow_offset, y+shadow_offset), wrapped_text, font=font, fill="black")
    draw.text((x, y), wrapped_text, font=font, fill="white")

    bg.save(output_path)
    print(f"✅ Created text image: {output_path}")
    return output_path


# ===============================
# CREATE VIDEO
# ===============================
def create_video(image_file, output_file, res):
    clip = ImageSequenceClip([image_file] * (FPS * DURATION), fps=FPS)
    clip = clip.set_duration(DURATION)
    clip.write_videofile(output_file, codec="libx264", audio=False, fps=FPS)
    print(f"🎬 Video created: {output_file}")


# ===============================
# UPLOAD TO YOUTUBE
# ===============================
def youtube_upload(file_path, title, description, tags, category_id="22", privacy="public"):
    creds, _ = google.auth.default(scopes=YOUTUBE_SCOPES)
    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id
        },
        "status": {"privacyStatus": privacy}
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/*")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print(f"✅ Uploaded: {file_path} → https://youtu.be/{response['id']}")


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    SCRIPT_TEXT = get_daily_quote()
    print("✅ Today's Quote:", SCRIPT_TEXT)

    bg_file = download_background()

    # Normal video
    img_video = create_text_image(bg_file, "frame_video.jpg", VIDEO_RES, SCRIPT_TEXT)
    create_video(img_video, OUTPUT_VIDEO, VIDEO_RES)

    # Shorts
    img_short = create_text_image(bg_file, "frame_short.jpg", SHORTS_RES, SCRIPT_TEXT)
    create_video(img_short, OUTPUT_SHORT, SHORTS_RES)

    today = datetime.now().strftime("%B %d, %Y")

    youtube_upload(
        OUTPUT_VIDEO,
        f"Daily Motivation 🚀 {today}",
        "Stay motivated with today's inspiring quote! #Motivation #DailyQuotes",
        ["motivation", "quotes", "daily inspiration"]
    )

    youtube_upload(
        OUTPUT_SHORT,
        f"Daily Motivation 🚀 {today} #Shorts",
        "Quick motivational shorts to brighten your day! #Motivation #Shorts",
        ["motivation", "quotes", "shorts"]
    )
