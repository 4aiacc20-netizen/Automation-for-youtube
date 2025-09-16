#!/usr/bin/env python3
"""
generate_and_upload_short.py
- Generates a short script (using HF Inference if HF_TOKEN exists, else uses local template)
- Creates a 1080x1920 vertical Short using moviepy
- Uploads to YouTube using YouTube Data API with stored CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN
"""

import os
import random
import time
import json
import io
import math
from pathlib import Path
from datetime import datetime
import requests

# Video libs
from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
# YouTube upload libs
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ---------- CONFIG (from env / GitHub Secrets) ----------
HF_TOKEN = os.getenv("HF_TOKEN", "")  # optional: HuggingFace Inference token
PIXABAY_KEY = os.getenv("PIXABAY_KEY", "")  # optional: for free stock (or use local assets)
YT_CLIENT_ID = os.getenv("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN", "")
YT_UPLOAD_TITLE_TEMPLATE = os.getenv("YT_TITLE", "Quick Tech Tip — {date}")
YT_UPLOAD_DESC_TEMPLATE = os.getenv("YT_DESC", "Auto-generated Short. Topic: {topic}\n#shorts")
YT_UPLOAD_TAGS = os.getenv("YT_TAGS", "shorts,tech,info").split(",")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------- HELPERS ----------
def utc_now_iso():
    return datetime.utcnow().isoformat()

# ---------- 1) Generate text/script ----------
def generate_script(topic=None, length_seconds=40):
    """
    Return a dict: {'title':..., 'script':..., 'segments':[{'text':..., 'duration':...}, ...]}
    Uses HF Inference API if HF_TOKEN present, otherwise returns local template.
    """
    if not topic:
        topics = [
            "quick python tip",
            "AI prompt trick",
            "shortcut for windows",
            "youtube growth tip",
            "productivity hack",
            "css layout trick",
        ]
        topic = random.choice(topics)

    print(f"[+] Generating script for topic: {topic}")

    # Try HF Inference text-generation (short prompt). If fails, fallback.
    if HF_TOKEN:
        try:
            HF_URL = "https://api-inference.huggingface.co/models/google/flan-t5-small"
            prompt = (
                f"Write a short YouTube Shorts script about '{topic}'. "
                "Make it ~40 seconds long. Provide 4 short segments, each with one-sentence content. "
                "Return JSON exactly like: {\"title\":..., \"segments\":[{\"text\":...,\"duration\":seconds}, ...]}"
            )
            resp = requests.post(
                HF_URL,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": prompt, "options": {"wait_for_model": True}},
                timeout=30,
            )
            data = resp.json()
            # The response usually in data[0]['generated_text'] or 'error'
            text_out = ""
            if isinstance(data, list) and "generated_text" in data[0]:
                text_out = data[0]["generated_text"]
            elif isinstance(data, dict) and "error" in data:
                print("[!] HF error:", data["error"])
            else:
                # try to flatten
                text_out = json.dumps(data)
            # naive parsing: attempt to extract JSON object from returned text
            import re, ast
            m = re.search(r"(\{.*\})", text_out, re.S)
            if m:
                parsed = ast.literal_eval(m.group(1))
                return parsed
        except Exception as e:
            print("[!] HF generation failed:", str(e))

    # Fallback local builder
    title = f"{topic.title()} — Quick Tip"
    # split into 4 segments
    full_lines = [
        f"Here's one fast tip about {topic}.",
        "Step 1: Do this simple action now.",
        "Why it works: short reason why.",
        "Try it now — bonus tip at the end!"
    ]
    seg_dur = max(6, length_seconds // len(full_lines))
    segments = [{"text": t, "duration": seg_dur} for t in full_lines]
    return {"title": title, "segments": segments, "topic": topic}

# ---------- 2) Download/get background & music ----------
def get_background_and_music():
    """
    Returns paths: (bg_video_path_or_none, bg_image_path_or_none, music_path_or_none)
    Strategy:
      - If PIXABAY_KEY present, download a free vertical-ish video
      - Otherwise, use a generated solid-color image and silence (or local music if present)
    """
    out = OUTPUT_DIR
    bg_video = out / "bg.mp4"
    bg_image = out / "bg.jpg"
    music = out / "bg_music.mp3"

    # try Pixabay for free videos (requires key). Fetch a random video related to "technology" or "abstract".
    if PIXABAY_KEY:
        try:
            q = "technology"
            r = requests.get("https://pixabay.com/api/videos/", params={"key": PIXABAY_KEY, "q": q, "per_page": 10})
            items = r.json().get("hits", [])
            if items:
                pick = random.choice(items)
                # choose a medium quality
                video_url = pick["videos"]["medium"]["url"]
                print("[+] Downloading background video from Pixabay")
                with requests.get(video_url, stream=True, timeout=30) as rr:
                    with open(bg_video, "wb") as f:
                        for chunk in rr.iter_content(chunk_size=8192):
                            f.write(chunk)
                return str(bg_video), None, None
        except Exception as e:
            print("[!] Pixabay fetch failed:", e)

    # fallback: generate a solid-color image
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1080, 1920), color=(20, 25, 38))
    img.save(bg_image)
    # music: try to use a local music file if user placed one at assets/music.mp3
    local_music = Path("assets/music.mp3")
    if local_music.exists():
        return None, str(bg_image), str(local_music)
    # otherwise create a 1-second silent mp3 (moviepy can handle no audio, but YouTube prefers some audio)
    try:
        from pydub import AudioSegment
        silent = AudioSegment.silent(duration=1000)
        silent.export(music, format="mp3")
        return None, str(bg_image), str(music)
    except Exception:
        # fallback: no music
        return None, str(bg_image), None

# ---------- 3) Make the vertical short ----------
def make_short(video_meta):
    """
    video_meta: {'title':..., 'segments':[{'text':...,'duration':...}], 'topic':...}
    Returns path to generated mp4
    """
    out = OUTPUT_DIR
    ts = int(time.time())
    out_path = out / f"short_{ts}.mp4"
    w, h = 1080, 1920

    bg_video_path, bg_image_path, music_path = get_background_and_music()

    clips = []
    total_dur = 0
    for idx, seg in enumerate(video_meta["segments"]):
        dur = seg.get("duration", 8)
        total_dur += dur
        # base clip
        if bg_video_path:
            base = VideoFileClip(bg_video_path).subclip(0, min(dur, VideoFileClip(bg_video_path).duration))
            # scale/crop to fill 1080x1920
            base = base.resize(height=h)
            base = base.crop(x_center=base.w/2, y_center=base.h/2, width=w, height=h)
        else:
            base = ImageClip(bg_image_path).set_duration(dur).resize((w, h))

        # text overlay: large heading + smaller subtitle
        txt = seg["text"]
        # split if too long
        # create a TextClip that is wrapped
        txt_clip = TextClip(
            txt,
            fontsize=64,
            font="DejaVu-Sans",
            method="caption",
            size=(w - 160, None),
        ).set_position(("center", h * 0.55)).set_duration(dur).crossfadein(0.2)

        # small top label
        label = TextClip(
            video_meta.get("topic", "").upper(),
            fontsize=36,
            font="DejaVu-Sans-Bold",
            method="label",
        ).set_position(("left", 40)).set_duration(dur)

        comp = CompositeVideoClip([base, txt_clip, label], size=(w, h)).set_duration(dur)
        clips.append(comp)

    final = concatenate_videoclips(clips, method="compose")
    # audio
    if music_path:
        try:
            a = AudioFileClip(music_path).fx(lambda audio: audio.volumex(0.6))
            # loop audio if shorter
            if a.duration < final.duration:
                a = a.audio_loop(duration=final.duration)
            final = final.set_audio(a)
        except Exception as e:
            print("[!] attaching music failed:", e)

    # write file (H.264), use bitrate moderate
    final.write_videofile(str(out_path), fps=24, codec="libx264", threads=4, audio_codec="aac", bitrate="2000k")
    final.close()
    return str(out_path)

# ---------- 4) YouTube upload ----------
def get_youtube_service_from_refresh(client_id, client_secret, refresh_token):
    """
    Construct an authorized googleapiclient service using refresh token.
    """
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
    )
    request = Request()
    creds.refresh(request)  # exchanges refresh token for access token
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    return youtube

def upload_video_to_youtube(video_file, title, description, tags):
    if not (YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REFRESH_TOKEN):
        raise RuntimeError("Missing YouTube OAuth credentials. Set YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN as env vars.")
    youtube = get_youtube_service_from_refresh(YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)
    body = {
        "snippet": {"title": title, "description": description, "tags": tags, "categoryId": "28"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/*")
    print("[+] Starting upload...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")
    print("[+] Upload complete. Video ID:", response.get("id"))
    return response.get("id")

# ---------- MAIN ----------
def main():
    # 1) generate script
    meta = generate_script()
    topic = meta.get("topic", meta.get("title", "Short"))
    # title/desc
    title = YT_UPLOAD_TITLE_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"), topic=topic, title=meta.get("title","Short"))
    description = YT_UPLOAD_DESC_TEMPLATE.format(topic=topic, date=datetime.now().strftime("%Y-%m-%d"))

    # 2) make video
    print("[+] Making short...")
    video_path = make_short(meta)
    print("[+] Video created at", video_path)

    # 3) upload
    try:
        vid_id = upload_video_to_youtube(video_path, title, description, YT_UPLOAD_TAGS)
        print("[+] Uploaded video id:", vid_id)
    except Exception as e:
        print("[!] Upload failed:", e)
        raise

if __name__ == "__main__":
    main()
