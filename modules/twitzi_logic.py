def process_logic(msg, bot_name, admin_id, token):
    text = msg.get("text", "").lower().strip()
    
    if text == "/start":
        return {
            "type": "text", 
            "data": f"🐦 *{bot_name} is Online*\nYour social media and notification bridge is active."
        }
    return None
