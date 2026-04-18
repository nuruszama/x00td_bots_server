import subprocess
import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"
    
def get_battery_status():
    try:
        # Reading from the Android system files on your X00TD
        with open("/sys/class/power_supply/battery/capacity", "r") as f:
            percent = f.read().strip()
        with open("/sys/class/power_supply/battery/status", "r") as f:
            status = f.read().strip()

        icons = {
            "Charging": "⚡ Charging",
            "Discharging": "🔋 Discharging",
            "Full": "✅ Full",
            "Not charging": "🔌 Plugged, not charging"
        }
        state_text = icons.get(status, status)
        return f"{percent}% ({state_text})"
    except Exception as e:
        return f"Battery Error: {e}"

# Added 'token' to the arguments to match the universal protocol
def process_logic(msg, admin_id, token):
    # Extract User Info
    user_info = msg.get("from", {})
    user_id = user_info.get("id")
    text = msg.get("text", "").lower().strip()
    
    # Secure Admin Check (comparing as strings for safety)
    is_admin = str(user_id) == str(admin_id)

    # Only process if user is the bot Admin
    if is_admin:
        if text == "/help":
            return {
                "type": "text",
                "data": (
                    "📦 *System:* X00TD / Snapdragon 636\n"
                    "----------------------------------------------------------------\n"
                    "       🤖 *TD-Ghost Admin Panel*\n"
                    "----------------------------------------------------------------\n"
                    "/start         - Alive check\n"
                    "/status      - Battery info\n"
                    "/ip              - Server & SMB Info\n"
                    "/chatlogs     - Activity Database\n"
                    "/botlogs       - bot background logs\n"
                    "/clearlogs  - Reset History\n"
                    "/reload       - Hot-reload all logic"
                )
            }
    
        if text == "/start":
            return {
                "type": "text",
                "data": "Hello Master. TD-Ghost is operational on the X00TD bridge."
            }
    
        if text == "/status":
            bat_info = get_battery_status()
            return {
                "type": "text",
                "data": f"🔋 *Battery:* {bat_info}"
            }
        
        if text == "/ip":
            ip_addr = get_local_ip()
            return {
                "type": "text",
                "data": (
                    f"🌐 *Local IP:* `{ip_addr}`\n"
                    f"📂 *SMB:* `\\\\{ip_addr}\\storage`\n"
                    f"👤 *User:* `x00td`"
                )
            }
        
        if text == "/botlogs":
            return "UPLOAD_BOT_BACKGROUND_LOGS"
            
        if text == "/chatlogs":
            return "UPLOAD_CHAT_LOGS"
                
        if text == "/clearlogs":
            return {
                "type": "text",
                "data": "⚠️ *Warning:* Are you sure you want to wipe the activity logs?\n\nType `/clearlogs_yes` to confirm."
            }
                        
        if text == "/clearlogs_yes":
            return "CLEAR_CHAT_LOGS"
        
        if text == "/reload":
            return "BOT_RELOAD"

    # If someone else tries to use the ghost bot
    elif text.startswith("/"):
        return {
            "type": "text",
            "data": "⛔ *Access Denied.*\n\nThis interface is reserved for the Master Admin."
        }

    return None
