import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREEK_DB = os.path.join(os.path.dirname(BASE_DIR), "creek_notes.json")
CONNECT_DB = os.path.join(os.path.dirname(BASE_DIR), "creek_connect_database.json")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def is_user_admin(chat_id, user_id, token):
    api_url = f"https://api.telegram.org/bot{token}/getChatMember"
    try:
        res = requests.get(api_url, params={"chat_id": chat_id, "user_id": user_id})
        status = res.json().get("result", {}).get("status")
        return status in ["administrator", "creator"]
    except:
        return False

def sync_group_to_db(msg, token, conn_data):
    """Logs group and admins if bot has admin rights."""
    chat = msg.get("chat", {})
    chat_id = str(chat.get("id"))
    chat_title = chat.get("title", "Unknown Group")
    
    if not chat_id.startswith("-"):
        return conn_data

    # Check if group already exists to minimize API calls
    if "groups" in conn_data and chat_id in conn_data["groups"]:
        return conn_data

    api_url = f"https://api.telegram.org/bot{token}/getChatAdministrators"
    try:
        response = requests.get(api_url, params={"chat_id": chat_id})
        res_data = response.json()

        if res_data.get("ok"):
            admin_list = {}
            for member in res_data.get("result", []):
                u = member.get("user", {})
                admin_list[str(u.get("id"))] = u.get("first_name", "Admin")

            if "groups" not in conn_data: conn_data["groups"] = {}
            conn_data["groups"][chat_id] = {
                "group_name": chat_title,
                "admins_in_the_group": admin_list
            }
    except:
        pass
    return conn_data

def process_logic(msg, bot_name, admin_id, token):        
    user_info = msg.get("from", {})
    user_id = str(user_info.get("id"))
    chat = msg.get("chat", {})
    chat_id = str(chat.get("id"))
    chat_type = chat.get("type")
    text = msg.get("text", "").strip()
    cmd = text.lower()
    is_master = user_id == str(admin_id)

    # deleting all service messages
    if any(key in msg for key in ["new_chat_members", "left_chat_member", "new_chat_title"]):
        return "DELETE_MESSAGE"

    # load database to memory
    conn_data = load_json(CONNECT_DB)
    
    # Sync group if message comes from a supergroup
    if chat_type in ["supergroup", "group"]:
        conn_data = sync_group_to_db(msg, token, conn_data)
        save_json(CONNECT_DB, conn_data)

    if "users" not in conn_data:
        conn_data["users"] = {}
    if user_id not in conn_data["users"]:
        conn_data["users"][user_id] = {"active_group": "", "connected_groups": {}}
    
    user_profile = conn_data["users"][user_id]
    active_chat_id = chat_id if chat_id.startswith("-") else user_profile.get("active_group", chat_id)
    context_name = user_profile.get("connected_groups", {}).get(active_chat_id, "this chat")

    # --- 2. COMMANDS ---
    
    # Private Chat Logic
    if chat_type == "private":
        if cmd == "/start":
            groups_db = conn_data.get("groups", {})
            admin_in = []
            
            # Cross-check user across all synced groups
            for g_id, g_info in groups_db.items():
                if user_id in g_info.get("admins_in_the_group", {}):
                    admin_in.append(f"• {g_info['group_name']} (`{g_id}`)")

            welcome_text = f"🚀 *Creek_Lab Online*\nContext: `{context_name}`\n\n"
            if admin_in:
                welcome_text += "🛡 *You are an admin in:*\n" + "\n".join(admin_in)
            else:
                welcome_text += "_No admin groups detected._"
                
            return {"type": "text", "data": welcome_text}

        if cmd == "!help":
            return {"type": "text", "data": "📂 `!groups`, `!use [n]`, `!connect` (in group)\n📝 `!notes`, `!save [name]`, `?name`"}

    # --- 3. CONNECTION LOGIC ---
    if cmd == "!connect" and chat_id.startswith("-"):
        if not (is_master or is_user_admin(chat_id, user_id, token)):
            return {"type": "text", "data": "Admin only.", "reply_to": True}
        
        conn_data["users"][user_id]["connected_groups"][chat_id] = chat.get("title", "Group")
        conn_data["users"][user_id]["active_group"] = chat_id
        save_json(CONNECT_DB, conn_data)
        return {"type": "text", "data": f"🔗 Connected to *{chat.get('title')}*", "delete_original": True}

    if cmd == "!groups" or cmd.startswith("!use "):
        groups = user_profile.get("connected_groups", {})
        if not groups:
            return {"type": "text", "data": "No groups connected. Use `!connect` in a group."}

        if cmd.startswith("!use "):
            try:
                idx = int(cmd.split()[1]) - 1
                g_ids = list(groups.keys())
                if 0 <= idx < len(g_ids):
                    new_id = g_ids[idx]
                    conn_data["users"][user_id]["active_group"] = new_id
                    save_json(CONNECT_DB, conn_data)
                    return {"type": "text", "data": f"✅ Switched to: *{groups[new_id]}*"}
                return {"type": "text", "data": "❌ Invalid number."}
            except: return {"type": "text", "data": "Usage: `!use 1`"}

        active = user_profile.get("active_group", "")
        lines = [f"{i}. {'🟢' if g_id == active else '⚪️'} {name}" for i, (g_id, name) in enumerate(groups.items(), 1)]
        return {"type": "text", "data": "📂 *Groups:*\n\n" + "\n".join(lines)}

    # --- 4. NOTE LOGIC ---
    if cmd == "!notes":
        db = load_json(CREEK_DB)
        notes = db.get(active_chat_id, {})
        if not notes: return {"type": "text", "data": f"📂 No notes for {context_name}."}
        lines = [f"🔹 {n['original_name']}" for n in notes.values()]
        return {"type": "text", "data": f"📝 *Notes ({context_name}):*\n" + "\n".join(lines)}

    if cmd.startswith("?"):
        note_name = cmd[1:].strip()
        db = load_json(CREEK_DB)
        notes = db.get(active_chat_id, {})
        if note_name in notes:
            n = notes[note_name]
            return {"type": n["type"], "data": n["id"], "caption": n.get("caption", ""), "reply_to": True}
        return {"type": "text", "data": "Not found."}

    if cmd.startswith("!save "):
        # Check if user is admin of the ACTIVE context
        if not (is_master or is_user_admin(active_chat_id, user_id, token)):
             return {"type": "text", "data": "Admin rights required for the active group."}
        
        note_name = cmd[6:].strip()
        reply = msg.get("reply_to_message")
        if not note_name or not reply: return {"type": "text", "data": "Reply to a message + `!save name`"}

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
        return {"type": "text", "data": f"✅ Saved `{note_name}`"}

    return None
