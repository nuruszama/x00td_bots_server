def process_logic(msg, bot_name, admin_id, token):
    text = msg.get("text", "").lower().strip()
    
    if text == "/start":
        return {
            "type": "text", 
            "data": "🌸 *Sweety is Online*\nReady to assist you with a touch of kindness."
        }
    return None
