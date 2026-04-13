import os
import random
import shutil
import textwrap
import subprocess
import json
import time
import base64
import datetime

import imageio_ffmpeg
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# =========================
# 🧠 SCHEDULER CONFIG
# =========================
LOG_FILE = "upload_log.txt"

TIME_WINDOWS = {
    "morning": (6, 7),
    "noon": (11, 12),
    "evening": (19, 20)
}

def get_ist():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def get_slot(hour):
    for slot, (start, end) in TIME_WINDOWS.items():
        if start <= hour < end:
            return slot
    return None

def get_today():
    return str(get_ist().date())  # ✅ FIXED IST DATE

def already_uploaded(slot):
    if not os.path.exists(LOG_FILE):
        return False
    with open(LOG_FILE, "r") as f:
        logs = f.read().splitlines()
    return f"{get_today()}-{slot}" in logs

def mark_uploaded(slot):
    with open(LOG_FILE, "a") as f:
        f.write(f"{get_today()}-{slot}\n")

# =========================
# CONFIG & DIRECTORIES
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")
USED_DIR = os.path.join(BASE_DIR, "images_used")
BGM_DIR = os.path.join(BASE_DIR, "bgm")
FONT_PATH = os.path.join(BASE_DIR, "fonts", "font.ttf")
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "reel.mp4")

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(USED_DIR, exist_ok=True)
os.makedirs(BGM_DIR, exist_ok=True)
os.makedirs(os.path.dirname(FONT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# =========================
# 1. AI QUOTE
# =========================
def get_ai_quote(image_path):
    try:
        print(f"👁️ Analyzing Image: {image_path}")
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")

        file = genai.upload_file(image_path)

        prompt = """
        Generate a Hindi quote based on this image.
        Return JSON only:
        {
        "quote": "2-line Hindi quote",
        "title": "Viral Title",
        "description": "Caption + Hashtags"
        }
        """

        res = model.generate_content([file, prompt])
        raw = res.text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw)

    except Exception as e:
        print(f"❌ AI ERROR: {e}")
        return {
            "quote": "Radhe Radhe 🙏\nBhakti hi shakti hai ❤️",
            "title": "Krishna Bhakti ✨",
            "description": "#krishna #bhakti #viral"
        }

# =========================
# 2. VIDEO RENDER
# =========================
def render_video(image_path, quote):
    try:
        print("🎬 Rendering Video...")

        if not os.listdir(BGM_DIR):
            raise Exception("No BGM found")

        bgm_path = os.path.join(BGM_DIR, random.choice(os.listdir(BGM_DIR)))

        img = Image.open(image_path).resize((1080, 1920))
        img.save("bg.png")

        overlay = Image.new("RGBA", (1080, 1920))
        draw = ImageDraw.Draw(overlay)

        box = Image.new("RGBA", (1080, 500), (0, 0, 0, 140))
        overlay.paste(box, (0, 1350), box)

        font = ImageFont.truetype(FONT_PATH, 70)
        lines = textwrap.wrap(quote, width=22)

        y = 1400
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            x = (1080 - (bbox[2] - bbox[0])) // 2
            draw.text((x, y), line, font=font, fill="white")
            y += 95

        overlay.save("overlay.png")

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        subprocess.run([
            ffmpeg, "-y",
            "-loop", "1", "-i", "bg.png",
            "-i", "overlay.png",
            "-i", bgm_path,
            "-filter_complex", "[0][1]overlay",
            "-t", "15",
            "-pix_fmt", "yuv420p",
            OUTPUT_FILE
        ])

        return OUTPUT_FILE

    except Exception as e:
        print(f"❌ RENDER ERROR: {e}")
        return None

# =========================
# 3. UPLOADERS
# =========================
def upload_to_youtube(video, title, desc):
    try:
        creds = Credentials(
            None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"]
        )

        youtube = build("youtube", "v3", credentials=creds)

        youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": desc},
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload(video)
        ).execute()

        print("✅ YouTube Uploaded")

    except Exception as e:
        print(f"❌ YouTube ERROR: {e}")

def upload_instagram(video, caption):
    try:
        from instagrapi import Client

        cl = Client()

        session_data = base64.b64decode(os.environ["INSTA_SESSION"])
        with open("session.json", "wb") as f:
            f.write(session_data)

        cl.load_settings("session.json")

        time.sleep(random.randint(15, 45))
        cl.clip_upload(video, caption=caption)

        print("✅ Instagram Uploaded")

    except Exception as e:
        print(f"❌ Instagram ERROR: {e}")

# =========================
# 🚀 EXECUTION
# =========================
if __name__ == "__main__":
    now = get_ist()
    slot = get_slot(now.hour)

    print(f"⏰ IST Time: {now.strftime('%H:%M:%S')}")

    if slot and not already_uploaded(slot):
        print(f"🚀 Running for: {slot}")

        try:
            images = [i for i in os.listdir(IMAGE_DIR) if i.lower().endswith(('.png', '.jpg', '.jpeg'))]

            if not images:
                raise Exception("Images folder empty!")

            img_name = random.choice(images)
            img_path = os.path.join(IMAGE_DIR, img_name)

            ai_data = get_ai_quote(img_path)

            video_path = render_video(img_path, ai_data["quote"])

            if video_path:
                upload_to_youtube(video_path, ai_data["title"], ai_data["description"])
                upload_instagram(video_path, ai_data["description"])

                shutil.move(img_path, os.path.join(USED_DIR, img_name))
                mark_uploaded(slot)

                print(f"🔥 SUCCESS: {slot} upload done!")

        except Exception as e:
            print(f"💀 CRITICAL ERROR: {e}")

    else:
        print("😴 Skip: Not time or already uploaded.")
