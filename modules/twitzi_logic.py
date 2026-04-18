def process_logic(msg, admin_id, token):
    text = msg.get("text", "").lower().strip()
    
    if text == "/start":
        return {
            "type": "text", 
            "data": "🐦 *Twitzi is Online*\nYour social media and notification bridge is active."
        }
    return None