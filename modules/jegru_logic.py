import os
import json
import requests

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Moves up one level from 'modules' to the main folder for the JSON
JEGRU_DB = os.path.join(os.path.dirname(BASE_DIR), "jegru_movies_database.json")
LOG_GROUP_ID = "-1002602661603"

def is_bot_admin(chat_id, token):
    if not str(chat_id).startswith("-"): return True 
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
    if "video" in msg or "document" in msg:
        file_type = "video" if "video" in msg else "document"
        file_id = msg[file_type]['file_id']
        
        file_name = msg.get("caption")
        if not file_name and file_type == "document":
            file_name = msg['document'].get('file_name')
        
        if not file_name:
            return {"type": "text", "data": "⚠️ Give this movie a caption to save it."}
        
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
    return None

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

    # --- 1. PRIVATE CHAT LOGIC ---
    if chat_type == "private":
        
        if cmd == "/start":
            first_name = msg.get("from", {}).get("first_name", "User")
            return {"type": "text", "data": f"Hello {first_name}. {bot_name} is online...."}

        else:
            
            if "document" in msg:
                file_id = msg["document"]["file_id"]
                file_name = msg["document"].get("file_name", "file.dat")
                return {"type": "document", "data": file_id, "caption": file_name, "delete_original": True}

            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]

            if "video" in msg:
                file_id = msg["video"]["file_id"]
                file_name = msg["video"].get("file_name", "video.mp4")
                return {"type": "video", "data": file_id, "caption": file_name, "delete_original": True}

            if "audio" in msg:
                file_id = msg["audio"]["file_id"]

            if "voice" in msg:
                file_id = msg["voice"]["file_id"]
        
    # --- 2. GROUP ADMIN SHIELD ---
    if chat_type != "private":
        
        if not is_bot_admin(chat_id, token):
            return None
                
        elif:
            if "document" in msg:
            file_id = msg["document"]["file_id"]
                file_name = msg["document"].get("file_name", "file.dat")
                return {"type": "document", "data": file_id, "caption": file_name, "delete_original": True}

            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]

            if "video" in msg:
                file_id = msg["video"]["file_id"]
                file_name = msg["video"].get("file_name", "video.mp4")
                return {"type": "video", "data": file_id, "caption": file_name, "delete_original": True}

            if "audio" in msg:
                file_id = msg["audio"]["file_id"]

            if "voice" in msg:
                file_id = msg["voice"]["file_id"]

        if text.startswith("/"):
            return {"type": "text", "data": f"⚠️ {bot_name} needs Admin rights to work here / work in progress."}
                
    return None
