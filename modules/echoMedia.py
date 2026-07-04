import requests

def is_bot_admin(chat_id, token):
    """Helper method verifying if the bot retains execution privileges in groups."""
    try:
        url = f"https://api.telegram.org/bot{token}/getChatMember"
        r = requests.get(url, params={"chat_id": chat_id, "user_id": token.split(':')[0]}, timeout=5)
        if r.status_code == 200:
            status = r.json().get("result", {}).get("status", "")
            return status in ["administrator", "creator"]
    except:
        pass
    return False

def process_logic(msg, bot_name, admin_id, token):
    """
    Modular execution block.
    Returns a response dict if handled, or None to fall through to other modules.
    """
    chat = msg.get("chat", {})
    chat_type = chat.get("type")
    user_id = str(msg.get("from", {}).get("id", ""))
    chat_id = str(chat.get("id", ""))
    
    # Extract text/caption safely
    text = (msg.get("text") or msg.get("caption") or "").strip()
    cmd = text.lower()

    if chat_type != "private":
        bot_is_admin = is_bot_admin(chat_id, token)
        if not bot_is_admin:
            return None
            
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

    if cmd == "/start":
        first_name = msg.get("from", {}).get("first_name", "User")
        return {"type": "text", "data": f"Hello {first_name}. {bot_name} is online...."}

    # If any media was detected, echo it back
    if res_type and file_id:
        caption_text = msg.get("caption") or ""
        file_name = msg.get(res_type, {}).get("file_name") or f"Shared {res_type}"
        caption = caption_text.split('\n')[0] if (res_type == "document" and caption_text) else file_name
            
        return {
            "type": res_type,
            "data": file_id,
            "caption": caption,
            "delete_original": True
        }
            
    return None