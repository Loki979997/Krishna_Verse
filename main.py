Main.py 

import os
import random
import shutil
import textwrap
import subprocess
import json
import time
import base64

import imageio_ffmpeg
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# =========================
# DECODE INSTA SESSION
# =========================
if "INSTA_SESSION" in os.environ:
    try:
        with open("session.json", "wb") as f:
            f.write(base64.b64decode(os.environ["INSTA_SESSION"]))
        print("✅ session.json created")
    except Exception as e:
        print("❌ Session decode error:", e)

# =========================
# CONFIG
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
        print(f"👁️ Vision AI: {image_path}")

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.5-flash")

        file = genai.upload_file(image_path)

        prompt = """
Generate JSON:
{
"quote": "2-line Hindi quote",
"title": "viral title with emojis",
"description": "caption + hashtags"
}
"""

        res = model.generate_content([file, prompt])
        raw = res.text.strip()

        raw = raw.replace("```json", "").replace("```", "")
        return json.loads(raw)

    except Exception as e:
        print("❌ AI ERROR:", e)
        return {
            "quote": "Zindagi ek safar hai\nMuskurate raho ❤️",
            "title": "Motivation 💯",
            "description": "#motivation #viral #life"
        }

# =========================
# 2. VIDEO (🔥 VIRAL STYLE)
# =========================
def render_video(image_path, quote):
    try:
        print("🎬 Rendering...")

        if not os.listdir(BGM_DIR):
            raise Exception("BGM folder empty")

        bgm = random.choice(os.listdir(BGM_DIR))
        bgm_path = os.path.join(BGM_DIR, bgm)

        img = Image.open(image_path).resize((1080, 1920))
        img.save("bg.png")

        overlay = Image.new("RGBA", (1080, 1920))
        draw = ImageDraw.Draw(overlay)

        # 🔥 DARK BOX (bottom)
        box = Image.new("RGBA", (1080, 500), (0, 0, 0, 120))
        overlay.paste(box, (0, 1350), box)

        font = ImageFont.truetype(FONT_PATH, 70)
        lines = textwrap.wrap(quote, width=22)

        y = 1400

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]

            x = (1080 - w) // 2

            # shadow
            draw.text((x+3, y+3), line, font=font, fill="black")

            # main text
            draw.text((x, y), line, font=font, fill="white")

            y += 90

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
        print("❌ VIDEO ERROR:", e)
        return None

# =========================
# 3. YOUTUBE
# =========================
def upload_to_youtube(video, title, desc):
    try:
        creds = Credentials(
            None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )

        youtube = build("youtube", "v3", credentials=creds)

        req = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": desc},
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload(video)
        )

        req.execute()
        print("✅ YouTube Uploaded")

    except Exception as e:
        print("❌ YouTube ERROR:", e)

# =========================
# 4. INSTAGRAM
# =========================
def upload_instagram(video, caption):
    try:
        from instagrapi import Client

        print("📸 Instagram Upload...")

        cl = Client()
        cl.load_settings("session.json")

        time.sleep(random.randint(10, 30))

        cl.clip_upload(video, caption=caption)

        print("✅ Instagram Uploaded")

    except Exception as e:
        print("❌ Instagram ERROR:", e)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    try:
        images = os.listdir(IMAGE_DIR)

        if not images:
            raise Exception("No images found")

        img = random.choice(images)
        path = os.path.join(IMAGE_DIR, img)

        ai = get_ai_quote(path)

        video = render_video(path, ai["quote"])

        if video:
            upload_to_youtube(video, ai["title"], ai["description"])
            upload_instagram(video, ai["description"])

            shutil.move(path, os.path.join(USED_DIR, img))

        print("🔥 ALL DONE")

    except Exception as e:
        print("💀 MAIN ERROR:", e)