import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREEK_DB = os.path.join(os.path.dirname(BASE_DIR), "creek_notes.json")
CONNECT_DB = os.path.join(os.path.dirname(BASE_DIR), "creek_connect_database.json")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def is_bot_admin(chat_id, token):
    """Checks if the bot has full admin rights in the group."""
    if not str(chat_id).startswith("-"): return True # Always allowed in DMs
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        # Get the bot's own ID from the token
        bot_id = token.split(":")[0]
        res = requests.get(url, params={"chat_id": chat_id, "user_id": bot_id}, timeout=5).json()
        if res.get("ok"):
            status = res["result"].get("status")
            # Check for 'administrator' or 'creator'
            if status in ["administrator", "creator"]:
                # Ensure it has delete_messages permission specifically
                return res["result"].get("can_delete_messages", False)
        return False
    except:
        return False

def is_user_admin(chat_id, user_id, token):
    if not str(chat_id).startswith("-"): return False
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": chat_id, "user_id": user_id}, timeout=5).json()
        return res.get("ok") and res["result"].get("status") in ["administrator", "creator"]
    except: return False

def process_logic(msg, admin_id, token):
    user_info = msg.get("from", {})
    user_id = str(user_info.get("id"))
    chat_id = str(msg.get("chat", {}).get("id"))
    first_name = user_info.get("first_name", "No First Name")
    chat_title = msg.get("chat", {}).get("title", "Private Chat")
    text = msg.get("text", "")
    is_master = user_id == str(admin_id)

    text = msg.get("text", "").lower().strip()
    if not chat_id.startswith("-"):
        if text == "/start":
            return {
                "type": "text", 
                "data": "*Creek_Lab is Online*\n\nUse `!help` to see how to use."
            }
    
        if text == "!help":
            return {
                "type": "text", 
                "data":(
                    "`!connect` : Run group commands locally in DM\n"
                    "`!groups` : See all connected groups and active connection"
                )
            }
    
    if text == "!groups" or text.startswith("!use "):
        conn_data = load_json(CONNECT_DB)
        
        # 1. Get the specific user's data (important!)
        # This assumes your JSON structure is { "users": { "USER_ID": { ... } } }
        user_profile = conn_data.get("users", {}).get(user_id, {})
        
        if not user_profile:
            return {"type": "text", "data": "No groups connected. Use `!connect` in a group first."}

        # --- Handle switching groups via !use [index] ---
        if text.startswith("!use "):
            try:
                idx = int(text.split()[1]) - 1
                g_ids = list(user_profile.get("connected_groups", {}).keys())
                
                if 0 <= idx < len(g_ids):
                    new_id = g_ids[idx]
                    # Update the database
                    conn_data["users"][user_id]["active_group"] = new_id
                    save_json(CONNECT_DB, conn_data)
                    
                    group_name = user_profile["connected_groups"][new_id]
                    return {"type": "text", "data": f"✅ Switched active context to: *{group_name}*"}
                else:
                    return {"type": "text", "data": "❌ Invalid group number."}
            except Exception as e:
                return {"type": "text", "data": "Usage: `!use [number]`"}

        # --- Handle listing groups via !groups ---
        if text == "!groups":
            groups = user_profile.get("connected_groups", {})
            active = user_profile.get("active_group", "")
            
            if not groups:
                return {"type": "text", "data": "No connected groups found."}

            lines = []
            for i, (g_id, g_name) in enumerate(groups.items(), 1):
                prefix = "🟢 *[ACTIVE]*" if g_id == active else "⚪️"
                lines.append(f"{i}. {prefix} {g_name}")
            
            menu = "📂 *Your Connected Groups:*\n\n" + "\n".join(lines)
            menu += "\n\nSwitch using `!use [number]`"
            return {"type": "text", "data": menu}

    # --- 1. BOT ADMIN SHIELD ---
    if chat_id.startswith("-"):
        if not is_bot_admin(chat_id, token):
            # We check if the message is a command to avoid spamming the group
            if text.startswith(("!", "?", ">")):
                return {
                    "type": "text", 
                    "data": "⚠️ *Bot Error:* all admin rights required for me to work in this group."
                }
            return None # Ignore regular chat if not admin

    # --- 2. REGISTRY: Update Group Database ---
    if chat_id.startswith("-"):
        conn_data = load_json(CONNECT_DB)
        if "groups" not in conn_data:
            conn_data["groups"] = {}
        if conn_data["groups"].get(chat_id) != chat_title:
            conn_data["groups"][chat_id] = chat_title
            save_json(CONNECT_DB, conn_data)

    # --- 3. CONNECT LOGIC ---
    if text.lower() == "!connect" and chat_id.startswith("-"):
        if not (is_master or is_user_admin(chat_id, user_id, token)):
            return {"type": "text", "data": "Only admins can connect.", "reply_to": True}
        
        conn_data = load_json(CONNECT_DB)
        if "users" not in conn_data:
            conn_data["users"] = {}
        
        # Initialize user if new
        if user_id not in conn_data["users"]:
            conn_data["users"][user_id] = {"active_group": "", "connected_groups": {}}

        # Add this group to their list and set as active
        conn_data["users"][user_id]["connected_groups"][chat_id] = chat_title
        conn_data["users"][user_id]["active_group"] = chat_id

        save_json(CONNECT_DB, conn_data)
        return {"type": "text", "data": f"🔗 *Connected* {first_name} to '{chat_title}'", "delete_original": True}

    #--- 4. CONTEXT & SWITCHING (DM Side) ---
    active_chat_id = chat_id
    context_name = "this chat"

    # --- 5. NOTE COMMANDS (using active_chat_id) ---
    cmd = text.lower()

    if cmd == "!notes":
        db = load_json(CREEK_DB)
        notes = db.get(active_chat_id, {})
        if not notes: return {"type": "text", "data": f"📂 No notes in {context_name}."}
        
        lines = [f"🔹 {n['original_name']}" for n in notes.values()]
        return {"type": "text", "data": f"📝 *Notes for {context_name}:*\n" + "\n-".join(lines) + "\n\nUse `>name` to fetch."}

    # --- 5. NOTE FETCHING (?note_name) ---
    if text.startswith("?"):
        note_name = text[1:].lower().strip()
        db = load_json(CREEK_DB)
        notes = db.get(active_chat_id, {})
        
        if note_name in notes:
            n = notes[note_name]
            return {
                "type": n["type"], 
                "data": n["id"], 
                "caption": n.get("caption", ""), # Returns the stored caption
                "reply_to": True,
                "delete_original": True
            }
        return {"type": "text", "data": f"'{note_name}' not found in {context_name}.", "reply_to": True}

    # --- 6. SAVE LOGIC (!save note_name) ---
    if cmd.startswith("!save "):
        if not (is_master or is_user_admin(active_chat_id, user_id, token)):
             return {"type": "text", "data": "Admin rights required.", "reply_to": True}
        
        # Extract the intended note name from the command
        note_name = text[6:].lower().strip()
        if not note_name:
            return {"type": "text", "data": "⚠️ Usage: `!save note_name` (Reply to a message)"}

        reply = msg.get("reply_to_message")
        if not reply:
            return {"type": "text", "data": "⚠️ Please reply to the content you want to save.", "reply_to": True}

        # Media extraction logic
        content_type = "text"
        file_id = reply.get("text") # Default for plain text/links
        stored_caption = reply.get("caption", "") # Keep original caption if it exists

        media_map = {
            "photo": lambda m: m["photo"][-1]["file_id"],
            "video": lambda m: m["video"]["file_id"],
            "document": lambda m: m["document"]["file_id"],
            "audio": lambda m: m["audio"]["file_id"]
        }

        for m_type, get_id in media_map.items():
            if m_type in reply:
                content_type = m_type
                file_id = get_id(reply)
                break
        
        if not file_id and not stored_caption:
            return {"type": "text", "data": "⚠️ Could not identify content to save."}

        # Save to Database
        db = load_json(CREEK_DB)
        if active_chat_id not in db: db[active_chat_id] = {}
        
        db[active_chat_id][note_name] = {
            "type": content_type, 
            "id": file_id, 
            "caption": stored_caption,
            "original_name": note_name # For the !notes list
        }
        
        save_json(CREEK_DB, db)
        return {
            "type": "text", 
            "data": f"Note saved as `{note_name}` in {context_name}.",
            "delete_original": True
        }

    # --- 7. REMOVE LOGIC (!remove note_name) ---
    if cmd.startswith("!remove "):
        if not (is_master or is_user_admin(active_chat_id, user_id, token)):
             return {"type": "text", "data": "Admin rights required.", "reply_to": True}

        note_name = text[8:].lower().strip()
        db = load_json(CREEK_DB)
        notes = db.get(active_chat_id, {})

        if note_name in notes:
            del db[active_chat_id][note_name]
            save_json(CREEK_DB, db)
            return {
                "type": "text", 
                "data": f"🗑️ Removed `{note_name}` from {context_name}.",
                "delete_original": True
            }
        
        return {"type": "text", "data": f"Note `{note_name}` does not exist.", "reply_to": True}
    
    # --- 7. SERVICE MESSAGE CLEANER ---
    # Delete "User joined" or "User left" messages automatically
    if any(key in msg for key in ["new_chat_members", "left_chat_member", "new_chat_title"]):
        return "DELETE_MESSAGE"

    return None
