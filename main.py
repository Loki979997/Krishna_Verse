# =========================
# 🧠 SCHEDULER CONFIG
# =========================
import datetime

DRY_RUN = False   # 🔥 test ke liye True kar sakta hai

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

def already_uploaded(slot):
    if not os.path.exists(LOG_FILE):
        return False
    
    with open(LOG_FILE, "r") as f:
        logs = f.read().splitlines()
    
    today = str(datetime.date.today())
    return f"{today}-{slot}" in logs

def mark_uploaded(slot):
    today = str(datetime.date.today())
    with open(LOG_FILE, "a") as f:
        f.write(f"{today}-{slot}\n")

# =========================
# MAIN WRAPPER (IMPORTANT)
# =========================
def run_main():
    try:
        images = os.listdir(IMAGE_DIR)

        if not images:
            raise Exception("No images found")

        img = random.choice(images)
        path = os.path.join(IMAGE_DIR, img)

        ai = get_ai_quote(path)

        video = render_video(path, ai["quote"])

        if video:
            if not DRY_RUN:
                upload_to_youtube(video, ai["title"], ai["description"])
                upload_instagram(video, ai["description"])
            else:
                print("🧪 DRY RUN: Upload skipped")

            shutil.move(path, os.path.join(USED_DIR, img))

        print("🔥 ALL DONE")

    except Exception as e:
        print("💀 MAIN ERROR:", e)

# =========================
# FINAL EXECUTION
# =========================
if __name__ == "__main__":
    now = get_ist()
    hour = now.hour

    print(f"⏰ Current IST: {now}")

    slot = get_slot(hour)

    if slot:
        if not already_uploaded(slot):
            print(f"🚀 Running for {slot}")
            run_main()
            mark_uploaded(slot)
        else:
            print(f"⚠️ Already uploaded for {slot}")
    else:
        print("😴 Not in upload window")
