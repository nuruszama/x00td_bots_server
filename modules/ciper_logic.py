def process_logic(msg, bot_name, admin_id, token):
    text = msg.get("text", "").lower().strip()
    
    if text == "/start":
        return {
            "type": "text", 
            "data": "🔐 *Ciper-Wire is Online*\nSecure communication protocols initialized."
        }
    return None
