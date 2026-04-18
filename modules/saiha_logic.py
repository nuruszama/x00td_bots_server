def process_logic(msg, admin_id, token):
    text = msg.get("text", "").lower().strip()
    
    if text == "/start":
        return {
            "type": "text", 
            "data": "🛡️ *Saihabath is Online*\nThe guardian bot is watching over this chat."
        }
    return None