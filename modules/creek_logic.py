import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjusted paths to ensure they are in the parent project folder
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
    if not str(chat_id).startswith("-"): return True 
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        bot_id = token.split(":")[0]
        res = requests.get(url, params={"chat_id": chat_id, "user_id": bot_id}, timeout=5).json()
        if res.get("ok"):
            status = res["result"].get("status")
            return status in ["administrator", "creator"] and res["result"].get("can_delete_messages", False)
        return False
    except: return False

def is_user_admin(chat_id, user_id, token):
    if not str(chat_id).startswith("-"): return False
    url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": chat_id, "user_id": user_id}, timeout=5).json()
        return res.get("ok") and res["result"].get("status") in ["administrator", "creator"]
    except: return False

def process_logic(msg, bot_name, admin_id, token): # Added bot_name to match your bot.py call
    user_info = msg.get("from", {})
    user_id = str(user_info.get("id"))
    chat_id = str(msg.get("chat", {}).get("id"))
    first_name = user_info.get("first_name", "User")
    chat_title = msg.get("chat", {}).get("title", "Private Chat")
    text = msg.get("text", "").strip() # Original text for case-sensitive needs
    cmd = text.lower() # Lowercase for command matching
    is_master = user_id == str(admin_id)

    # --- 1. ESTABLISH CONTEXT (THE FIX) ---
    conn_data = load_json(CONNECT_DB)
    if "users" not in conn_data: conn_data["users"] = {}
    user_profile = conn_data["users"].get(user_id, {})

    if chat_id.startswith("-"):
        active_chat_id = chat_id
        context_name = "this group"
    else:
        # If in DM, look up the connected active group
        active_chat_id = user_profile.get("active_group", chat_id)
        context_name = user_profile.get("connected_groups", {}).get(active_chat_id, "this chat")

    # --- 2. DM START & HELP ---
    if not chat_id.startswith("-"):
        if cmd == "/start":
            return {"type": "text", "data": f"*Creek_Lab is Online*\n\nConnected to: `{context_name}`\nUse `!help` to see commands."}
        if cmd == "!help":
            return {"type": "text", "data": (
                "📂 *Connection Commands:*\n"
                "`!connect` : (In Group) Link group to your DM\n"
                "`!groups` : Show connected groups\n"
                "`!use [num]` : Switch active group\n\n"
                "📝 *Note Commands:*\n"
                "`!notes` : List all notes\n"
                "`!save [name]` : (Reply to content) Save note\n"
                "`!remove [name]` : Delete a note\n"
                "`?name` : Fetch a note"
            )}

    # --- 3. CONNECTION LOGIC (!connect, !groups, !use) ---
    if cmd == "!connect" and chat_id.startswith("-"):
        if not (is_master or is_user_admin(chat_id, user_id, token)):
            return {"type": "text", "data": "Only admins can connect.", "reply_to": True}
        
        if user_id not in conn_data["users"]:
            conn_data["users"][user_id] = {"active_group": "", "connected_groups": {}}

        conn_data["users"][user_id]["connected_groups"][chat_id] = chat_title
        conn_data["users"][user_id]["active_group"] = chat_id
        save_json(CONNECT_DB, conn_data)
        return {"type": "text", "data": f"🔗 *Connected* {first_name} to '{chat_title}'", "delete_original": True}

    if cmd == "!groups" or cmd.startswith("!use "):
        if not user_profile:
            return {"type": "text", "data": "No groups connected. Use `!connect` in a group first."}

        if cmd.startswith("!use "):
            try:
                idx = int(cmd.split()[1]) - 1
                g_ids = list(user_profile.get("connected_groups", {}).keys())
                if 0 <= idx < len(g_ids):
                    new_id = g_ids[idx]
                    conn_data["users"][user_id]["active_group"] = new_id
                    save_json(CONNECT_DB, conn_data)
                    return {"type": "text", "data": f"✅ Context: *{user_profile['connected_groups'][new_id]}*"}
                return {"type": "text", "data": "❌ Invalid number."}
            except: return {"type": "text", "data": "Use: `!use [number]`"}

        if cmd == "!groups":
            groups = user_profile.get("connected_groups", {})
            active = user_profile.get("active_group", "")
            lines = [f"{i}. {'🟢' if g_id == active else '⚪️'} {name}" for i, (g_id, name) in enumerate(groups.items(), 1)]
            return {"type": "text", "data": "📂 *Connected Groups:*\n\n" + "\n".join(lines) + "\n\nSwitch: `!use [num]`"}

    # --- 4. ADMIN SHIELD & REGISTRY ---
    if chat_id.startswith("-"):
        if not is_bot_admin(chat_id, token):
            if cmd.startswith(("!", "?", ">")):
                return {"type": "text", "data": "⚠️ *Bot Error:* I need Admin Rights (Delete Messages) to work here."}
            return None
        
        # Keep group title updated
        if "groups" not in conn_data: conn_data["groups"] = {}
        if conn_data["groups"].get(chat_id) != chat_title:
            conn_data["groups"][chat_id] = chat_title
            save_json(CONNECT_DB, conn_data)

    # --- 5. NOTE COMMANDS ---
    if cmd == "!notes":
        db = load_json(CREEK_DB)
        notes = db.get(active_chat_id, {})
        if not notes: return {"type": "text", "data": f"📂 No notes in *{context_name}*."}
        lines = [f"🔹 {n['original_name']}" for n in notes.values()]
        return {"type": "text", "data": f"📝 *Notes ({context_name}):*\n" + "\n".join(lines) + "\n\nFetch with `?name`"}

    if cmd.startswith("?"):
        note_name = cmd[1:].strip()
        db = load_json(CREEK_DB)
        notes = db.get(active_chat_id, {})
        if note_name in notes:
            n = notes[note_name]
            return {"type": n["type"], "data": n["id"], "caption": n.get("caption", ""), "reply_to": True, "delete_original": True}
        return {"type": "text", "data": f"'{note_name}' not found in {context_name}."}

    if cmd.startswith("!save "):
        if not (is_master or is_user_admin(active_chat_id, user_id, token)):
             return {"type": "text", "data": "Admin rights required.", "reply_to": True}
        
        note_name = cmd[6:].strip()
        reply = msg.get("reply_to_message")
        if not note_name or not reply:
            return {"type": "text", "data": "⚠️ Reply to something and use `!save name`"}

        content_type, file_id = "text", reply.get("text")
        media_map = {"photo": lambda m: m["photo"][-1]["file_id"], "video": lambda m: m["video"]["file_id"],
                     "document": lambda m: m["document"]["file_id"], "audio": lambda m: m["audio"]["file_id"]}

        for m_type, get_id in media_map.items():
            if m_type in reply:
                content_type, file_id = m_type, get_id(reply)
                break
        
        db = load_json(CREEK_DB)
        if active_chat_id not in db: db[active_chat_id] = {}
        db[active_chat_id][note_name] = {"type": content_type, "id": file_id, "caption": reply.get("caption", ""), "original_name": note_name}
        save_json(CREEK_DB, db)
        return {"type": "text", "data": f"✅ Saved `{note_name}` to {context_name}.", "delete_original": True}

    if cmd.startswith("!remove "):
        if not (is_master or is_user_admin(active_chat_id, user_id, token)):
             return {"type": "text", "data": "Admin rights required."}
        note_name = cmd[8:].strip()
        db = load_json(CREEK_DB)
        if note_name in db.get(active_chat_id, {}):
            del db[active_chat_id][note_name]
            save_json(CREEK_DB, db)
            return {"type": "text", "data": f"🗑️ Removed `{note_name}`."}
        return {"type": "text", "data": "Note not found."}

    # --- 6. CLEANER ---
    if any(key in msg for key in ["new_chat_members", "left_chat_member", "new_chat_title"]):
        return "DELETE_MESSAGE"

    return None
