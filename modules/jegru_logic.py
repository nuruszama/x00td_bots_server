import os
import json
import requests

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Moves up one level from 'modules' to the main folder for the JSON
JEGRU_DB = os.path.join(os.path.dirname(BASE_DIR), "jegru_movies_database.json")
LOG_GROUP_ID = "-1002602661603"

def is_bot_admin(chat_id, token):
    bot_id = token.split(":")[0]
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": chat_id, "user_id": bot_id}, timeout=5).json()
        return res.get("ok") and res["result"].get("status") in ["administrator", "creator"]
    except: return False

def send_group_log(text, bot_name, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": LOG_GROUP_ID, "text": f"🎬 {bot_name} Log: {text}"}, timeout=5)
    except: pass

def save_to_db(msg, bot_name, token):
    db = []
    if os.path.exists(JEGRU_DB):
        with open(JEGRU_DB, "r") as f:
            try: db = json.load(f)
            except: db = []
        
    if any(item['file_id'] == file_id or item['name'].lower() == file_name.lower() for item in db):
        return {"type": "text", "data": "ℹ️ Already in database."}
            
    db.append({"file_id": file_id, "type": file_type, "name": file_name})
    with open(JEGRU_DB, "w") as f:
        json.dump(db, f, indent=4)
        
    send_group_log(f"Added: {file_name}", bot_name, token)
    return {"type": "text", "data": f"✅ Saved: {file_name}", "delete_original": True}

def find_movie(query):
    if not os.path.exists(JEGRU_DB): return None
    with open(JEGRU_DB, "r") as f:
        try:
            db = json.load(f)
            for item in db:
                if query == item['name'].lower():
                    return item
        except: pass
    return None

def process_logic(msg, bot_name, admin_id, token):
    chat = msg.get("chat", {})
    chat_type = chat.get("type")
    user_id = str(msg.get("from", {}).get("id", ""))
    chat_id = str(chat.get("id", ""))
    
    # Extract text/caption safely
    text = (msg.get("text") or msg.get("caption") or "").strip()
    cmd = text.lower()
    is_admin = user_id == str(admin_id)

    # Check for media types dynamically
    media_map = {
        "photo": lambda m: m["photo"][-1]["file_id"],
        "video": lambda m: m["video"]["file_id"],
        "document": lambda m: m["document"]["file_id"],
        "audio": lambda m: m["audio"]["file_id"],
        "voice": lambda m: m["voice"]["file_id"]
    }

    # Check for media content
    res_type = None
    file_id = None
    
    for m_type, get_id in media_map.items():
        if m_type in msg:
            res_type = m_type
            file_id = get_id(msg)
            break

    if chat_type == "private":
        if cmd == "/start":
            first_name = msg.get("from", {}).get("first_name", "User")
            return {"type": "text", "data": f"Hello {first_name}. {bot_name} is online...."}

        # If any media was detected, echo it back
        if res_type and file_id:
            raw_caption = msg.get("caption").split('\n')[0] or msg.get(res_type, {}).get("file_name")
            caption = raw_caption if res_type == "document" else msg.get(res_type, {}).get("file_name")
            
            return {
                "type": res_type,
                "data": file_id,
                "caption": clean_caption,
                "delete_original": True
            }

    # --- 2. GROUP ADMIN SHIELD ---
    if chat_type != "private":
        if cmd == "/start":
            return {"type": "text", "data": f"⚠️ {bot_name} needs Admin rights to work here / work in progress."}
            
        # If any media was detected, echo it back
        if res_type and file_id:
            raw_caption = msg.get("caption").split('\n')[0] or msg.get(res_type, {}).get("file_name")
            caption = raw_caption if res_type == "document" else msg.get(res_type, {}).get("file_name")
            
            return {
                "type": res_type,
                "data": file_id,
                "caption": clean_caption
            }
            
    return None
