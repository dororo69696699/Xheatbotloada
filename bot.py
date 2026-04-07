from telethon import TelegramClient, events
from config import API_ID, API_HASH, BOT_TOKEN
import json
import imagehash
from PIL import Image
import requests
from io import BytesIO
import re
import os

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

DB_FILE = "db.json"
scanning = False

# ===== LOAD DB =====
def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)

# ===== SAVE DB =====
def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ===== HASH IMAGE =====
def get_hash(image_bytes):
    img = Image.open(BytesIO(image_bytes)).convert("L")
    return str(imagehash.phash(img))

# ===== NAME EXTRACTOR =====
def extract_name(caption):
    if not caption:
        return None

    lines = caption.split("\n")

    for line in lines:
        line = line.strip()

        # Case 1
        match = re.search(r'\d+:\s*(.+)', line)
        if match:
            name = match.group(1)
        else:
            name = line

        # CLEAN
        name = re.sub(r'\[.*?\]', '', name)
        name = re.sub(r'[^A-Za-z\s]', '', name)
        name = name.strip()

        blacklist = ["rarity", "edition", "from", "id"]
        if any(x in name.lower() for x in blacklist):
            continue

        if len(name.split()) >= 2:
            return name

    return None

# ===== START =====
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply("✅ Bot Ready")

# ===== SCAN START =====
@client.on(events.NewMessage(pattern="/scandb"))
async def scandb(event):
    global scanning
    scanning = True
    await event.reply("🔍 Scanning Started")

# ===== STOP =====
@client.on(events.NewMessage(pattern="/stopscan"))
async def stopscan(event):
    global scanning
    scanning = False
    await event.reply("⛔ Scanning Stopped")

# ===== COUNT =====
@client.on(events.NewMessage(pattern="/count"))
async def count(event):
    db = load_db()
    await event.reply(f"📊 Total: {len(db)}")

# ===== AUTO SCAN =====
@client.on(events.NewMessage)
async def auto_scan(event):
    global scanning
    if not scanning:
        return

    if not event.message.photo:
        return

    caption = event.message.text
    name = extract_name(caption)

    if not name:
        return

    # DOWNLOAD IMAGE
    file = await event.download_media(bytes)

    img_hash = get_hash(file)

    db = load_db()

    # DUPLICATE CHECK
    for item in db:
        if item["hash"] == img_hash:
            return

    db.append({
        "hash": img_hash,
        "name": name
    })

    save_db(db)
    print(f"Saved: {name}")

# ===== NAME GUESS =====
@client.on(events.NewMessage(pattern="/name"))
async def name(event):
    if not event.is_reply:
        await event.reply("❌ Reply to image")
        return

    reply = await event.get_reply_message()

    if not reply.photo:
        await event.reply("❌ Not image")
        return

    file = await reply.download_media(bytes)
    img_hash = get_hash(file)

    db = load_db()

    # FIND CLOSE MATCH
    for item in db:
        if item["hash"] == img_hash:
            await event.reply(f"✅ {item['name']}")
            return

    await event.reply("❌ Not Found")

# ===== RUN =====
print("Bot Running...")
client.run_until_disconnected()
