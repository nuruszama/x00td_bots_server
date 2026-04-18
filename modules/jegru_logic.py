import os
import json
import requests

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JEGRU_DB = os.path.join(os.path.dirname(BASE_DIR), "jegru_movies_database.json")
LOG_GROUP_ID = "-1002602661603"

def is_bot_admin(chat_id, token):
    """Extracts bot_id from token and checks admin rights."""
    if not str(chat_id).startswith("-"): return True 
    bot_id = token.split(":")[0]
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": chat_id, "user_id": bot_id}, timeout=5).json()
        return res.get("ok") and res["result"].get("status") in ["administrator", "creator"]
    except: return False

def send_group_log(text, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": LOG_GROUP_ID, "text": f"🎬 Jegru Log: {text}"}, timeout=5)
    except: pass

# UPDATED: Added bot_name to function signature to match your bot.py
def process_logic(msg, admin_id, token):
    user_info = msg.get("from", {})
    user_id = str(user_info.get("id"))
    chat_id = str(msg.get("chat", {}).get("id"))
    first_name = user_info.get("first_name", "No First Name")
    last_name = user_info.get("last_name", "")
    full_name = first_name + last_name
    text = msg.get("text", "").strip() or msg.get("caption", "").strip()
    is_admin = user_id == str(admin_id)
    cmd = text.lower()

    if text == "/start":
        return {
            "type": "text",
            "data": f"Hello {full_name}. Jegru is online...."
        }

    # --- 1. BOT ADMIN SHIELD ---
    if chat_id.startswith("-"):
        if not is_bot_admin(chat_id, token):
            if text.startswith("/"):
                return {"type": "text", "data": "⚠️ Jegru needs Admin rights to work here."}
            return None

    # --- 2. Handle Saving (Video & Document) ---
    if "video" in msg or "document" in msg:
        # Only admins can add movies to the DB
        if not is_admin:
            return None 

        file_type = "video" if "video" in msg else "document"
        file_id = msg[file_type]['file_id']
        
        # Priority: Caption > Document Filename
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
        
        send_group_log(f"Added: {file_name}", token)
        return {"type": "text", "data": f"✅ Saved: {file_name}", "delete_original": True}

    # --- 3. Commands ---
    if cmd == "/start":
        return {"type": "text", "data": "🎬 *Jegru Movie System Online*\nUse /search [name] to find movies."}

    # SEARCH
    if cmd.startswith("/search "):
        query = text[8:].strip().lower()
        if not os.path.exists(JEGRU_DB):
            return {"type": "text", "data": "📂 Database empty."}
            
        with open(JEGRU_DB, "r") as f:
            db = json.load(f)
            
        matches = [i['name'] for i in db if query in i['name'].lower()]
        if not matches:
            return {"type": "text", "data": f"❌ No matches for '{query}'."}
            
        res = "\n".join([f"🎬 `{m}`" for m in matches[:10]])
        return {"type": "text", "data": f"🔍 *Results:*\n{res}\n\nUse `/get [name]`"}

    # GET
    if cmd.startswith("/get "):
        query = text[5:].strip().lower()
        if not os.path.exists(JEGRU_DB): return None
        
        with open(JEGRU_DB, "r") as f:
            db = json.load(f)
            
        for item in db:
            if query == item['name'].lower():
                return {
                    "type": item['type'], 
                    "data": item['file_id'], 
                    "caption": f"🎥 {item['name']}",
                    "reply_to": True
                }
        return {"type": "text", "data": "❌ Not found. Use /search."}

    # DELETE (Admin Only)
    if cmd.startswith("/delete ") and is_admin:
        query = text[8:].strip().lower()
        if not os.path.exists(JEGRU_DB): return None
        
        with open(JEGRU_DB, "r") as f:
            db = json.load(f)
        
        new_db = [item for item in db if item['name'].lower() != query]
        if len(db) == len(new_db):
            return {"type": "text", "data": f"❌ '{query}' not found."}
            
        with open(JEGRU_DB, "w") as f:
            json.dump(new_db, f, indent=4)
        
        send_group_log(f"Deleted: {query}", token)
        return {"type": "text", "data": f"🗑️ Removed '{query}'."}

    return None