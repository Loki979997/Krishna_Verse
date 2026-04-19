import os
import random
import shutil
import textwrap
import subprocess
import json
import time
import base64
import re

import imageio_ffmpeg
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# =========================
# SESSION DECODE
# =========================
if "INSTA_SESSION" in os.environ:
    try:
        with open("session.json", "wb") as f:
            f.write(base64.b64decode(os.environ["INSTA_SESSION"]))
        print("✅ session.json ready")
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
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(USED_DIR, exist_ok=True)
os.makedirs(BGM_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# UTILS
# =========================
def safe_json(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None

# =========================
# AI (KRISHNA MODE 🔥)
# =========================
def get_ai_quote(image_path):
    try:
        print("🧠 AI analyzing image...")

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-pro")

        file = genai.upload_file(image_path)

        # STEP 1: IMAGE UNDERSTANDING
        desc_prompt = """
Describe this image of Lord Krishna:
- emotion
- scene (Radha, flute, alone, divine, etc.)
in 1 short line
"""
        desc = model.generate_content([file, desc_prompt]).text.strip()

        # STEP 2: QUOTE GENERATION
        prompt = f"""
Krishna image context: {desc}

Write viral devotional content.

Rules:
- Hindi + Hinglish
- Deep emotional / bhakti tone
- No generic lines

Examples:
"Jo tumhara hai, woh Krishna tum tak zaroor pahuchayenge"
"Radha ne pyar nahi kiya... unhone Krishna ko mehsoos kiya"

Return JSON:
{{
"quote": "2 lines",
"title": "hook with emoji",
"description": "caption + hashtags"
}}
"""

        res = model.generate_content([prompt])
        raw = res.text.strip()

        data = safe_json(raw)

        if not data:
            raise Exception("Invalid JSON")

        return data

    except Exception as e:
        print("❌ AI ERROR:", e)
        return {
            "quote": "Krishna sab dekh rahe hain...\nVishwas rakho 🕊️",
            "title": "Krishna 🙏",
            "description": "#krishna #radhe #bhakti"
        }

# =========================
# VIDEO RENDER
# =========================
def render_video(image_path, quote):
    try:
        print("🎬 Rendering video...")

        timestamp = str(int(time.time()))
        bg_path = f"bg_{timestamp}.png"
        overlay_path = f"overlay_{timestamp}.png"
        output_path = os.path.join(OUTPUT_DIR, f"reel_{timestamp}.mp4")

        # IMAGE
        img = Image.open(image_path).resize((1080, 1920))
        img.save(bg_path)

        # OVERLAY
        overlay = Image.new("RGBA", (1080, 1920))
        draw = ImageDraw.Draw(overlay)

        # gradient box
        for i in range(500):
            draw.rectangle(
                [(0, 1350 + i), (1080, 1350 + i)],
                fill=(0, 0, 0, int(150 * (i / 500)))
            )

        font = ImageFont.truetype(FONT_PATH, 70)
        lines = textwrap.wrap(quote, width=22)

        y = 1400
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            x = (1080 - (bbox[2] - bbox[0])) // 2

            draw.text((x+3, y+3), line, font=font, fill="black")
            draw.text((x, y), line, font=font, fill="white")

            y += 90

        overlay.save(overlay_path)

        # BGM
        bgm_files = os.listdir(BGM_DIR)
        bgm_path = os.path.join(BGM_DIR, random.choice(bgm_files)) if bgm_files else None

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [
            ffmpeg, "-y",
            "-loop", "1", "-i", bg_path,
            "-i", overlay_path,
        ]

        if bgm_path:
            cmd += ["-i", bgm_path]

        cmd += [
            "-filter_complex",
            "[0:v]zoompan=z='min(zoom+0.0005,1.2)':d=375:s=1080x1920[bg];[bg][1:v]overlay",
            "-t", "15",
            "-pix_fmt", "yuv420p",
        ]

        if bgm_path:
            cmd += ["-shortest"]

        cmd.append(output_path)

        subprocess.run(cmd)

        return output_path

    except Exception as e:
        print("❌ VIDEO ERROR:", e)
        return None

# =========================
# YOUTUBE
# =========================
def upload_youtube(video, title, desc):
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
        print("❌ YouTube ERROR:", e)

# =========================
# INSTAGRAM
# =========================
def upload_instagram(video, caption):
    try:
        from instagrapi import Client

        cl = Client()

        if os.path.exists("session.json"):
            cl.load_settings("session.json")
        else:
            cl.login(os.environ["INSTA_USER"], os.environ["INSTA_PASS"])
            cl.dump_settings("session.json")

        time.sleep(random.randint(10, 25))
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

        # 🔥 Hook add
        hook = random.choice([
            "Krishna sab dekh rahe hain 👀",
            "Yeh baat dil ko chhoo jayegi ❤️",
            "Aaj Krishna ne yeh sikhaya 🕊️"
        ])

        final_quote = hook + "\n\n" + ai["quote"]

        video = render_video(path, final_quote)

        if video:
            upload_youtube(video, ai["title"], ai["description"])
            upload_instagram(video, ai["description"])

            shutil.move(path, os.path.join(USED_DIR, img))

        print("🔥 DONE")

    except Exception as e:
        print("💀 MAIN ERROR:", e)