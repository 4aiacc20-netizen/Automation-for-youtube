import os
import random
import requests
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
from gtts import gTTS

# Video resolution
VIDEO_SHORTS_RES = (720, 1280)

# Font setup
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SIZE = 48

# Background image URLs (replace with your own stock images if needed)
BACKGROUND_URLS = [
    "https://picsum.photos/720/1280",
    "https://source.unsplash.com/random/720x1280/?nature",
    "https://source.unsplash.com/random/720x1280/?city",
]

# Download backgrounds
def download_backgrounds():
    os.makedirs("backgrounds", exist_ok=True)
    for i, url in enumerate(BACKGROUND_URLS):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(f"backgrounds/bg_{i}.jpg", "wb") as f:
                    f.write(r.content)
        except Exception as e:
            print(f"⚠️ Failed to download {url}: {e}")
    print("✅ Background images ready")

# Safe background loader with fallback
def get_background(bg_image_path, video_res):
    try:
        bg = Image.open(bg_image_path).convert("RGB").resize(video_res)
        print("✅ Background image loaded")
    except Exception as e:
        print("⚠️ Background missing, creating blank fallback")
        bg = Image.new("RGB", video_res, color=(0, 0, 0))  # black fallback
    return bg

# Create text image
def create_text_image(text, output_path, video_res):
    bg_files = [f"backgrounds/{f}" for f in os.listdir("backgrounds") if f.endswith(".jpg")]
    bg_path = random.choice(bg_files) if bg_files else None

    bg = get_background(bg_path, video_res)

    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # Text wrapping
    lines = []
    words = text.split()
    line = ""
    for word in words:
        if draw.textlength(line + " " + word, font=font) < video_res[0] - 100:
            line += " " + word
        else:
            lines.append(line)
            line = word
    lines.append(line)

    y = video_res[1] // 3
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (video_res[0] - w) // 2
        draw.text((x, y), line, font=font, fill="white")
        y += FONT_SIZE + 10

    bg.save(output_path)
    print(f"✅ Text image saved: {output_path}")

# Generate TTS audio
def generate_tts(text, output_path):
    tts = gTTS(text=text, lang="en")
    tts.save(output_path)
    print("✅ TTS audio generated")

# Create final video
def create_video(image_path, audio_path, output_path):
    clip = mp.ImageClip(image_path).set_duration(mp.AudioFileClip(audio_path).duration)
    audio = mp.AudioFileClip(audio_path)
    final = clip.set_audio(audio)
    final.write_videofile(output_path, fps=24)
    print("✅ Final video created")

if __name__ == "__main__":
    quote = "Success is getting what you want. Happiness is wanting what you get."

    download_backgrounds()

    img_file = "frame.jpg"
    audio_file = "audio.mp3"
    video_file = "short.mp4"

    create_text_image(quote, img_file, VIDEO_SHORTS_RES)
    generate_tts(quote, audio_file)
    create_video(img_file, audio_file, video_file)
