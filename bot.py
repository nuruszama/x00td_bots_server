import time
import json
import importlib
import requests
import os
import threading
import subprocess
from modules import tools 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config():
    config_path = os.path.join(BASE_DIR, 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Error: config.json not found!")
        return {}

# Load config once at the start
CONFIG = load_config()

# Get BOT_ADMIN from config, fallback to None if missing
# We wrap it in str() to ensure it matches the Telegram API ID format
BOT_ADMIN = str(CONFIG.get("bot_admin_id", ""))

LOG_FILE = os.path.join(BASE_DIR, "activity_log.json")

def save_to_json(entry):
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
        
        logs.append(entry)
        
        # Write with indent=4 to make it readable for you
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"Failed to save log: {e}")

# Helper to get battery level from Android
def get_battery_info():
    try:
        # We call 'dumpsys battery' from the Android host via the chroot bridge
        cmd = "cat /sys/class/power_supply/battery/capacity"
        level = subprocess.check_output(cmd, shell=True).decode().strip()
        
        cmd_status = "cat /sys/class/power_supply/battery/status"
        status = subprocess.check_output(cmd_status, shell=True).decode().strip()
        
        return int(level), status # returns (level, "Charging"/"Discharging")
    except:
        return None, None

def battery_monitor(token):
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    last_alert = None # Prevents spamming notifications
    
    while True:
        level, status = get_battery_info()
        if level is not None:
            # Low Battery Alert
            if level <= 20 and status != "Charging" and last_alert != "low":
                requests.post(api_url, data={"chat_id": BOT_ADMIN, "text": f"⚠️ *Battery Low: {level}%*\nPlease plug in the charger!"})
                last_alert = "low"
            
            # High Battery Alert
            elif level >= 90 and status == "Charging" and last_alert != "high":
                requests.post(api_url, data={"chat_id": BOT_ADMIN, "text": f"✅ *Battery Charged: {level}%*\nYou can unplug the charger now."})
                last_alert = "high"
            
            # Reset alert status when battery is back in normal range
            elif 25 < level < 85:
                last_alert = None
                
        time.sleep(300) # Check every 5 minute

# Each bot gets its own instance of this function running in parallel
def bot_worker(bot_name, token, admin_id):
    api_url = f"https://api.telegram.org/bot{token}"
    session = requests.Session()
    
    # --- STARTUP NOTIFICATION FOR TD-Ghost ---
    if bot_name == "TD-Ghost":
        session.post(f"{api_url}/sendMessage", data={
            "chat_id": BOT_ADMIN, 
            "text": (
                "---------------------------------------------------\n"
                "    🚀  *TD BOT is now Online*\n"
                "---------------------------------------------------"
            ),
            "parse_mode": "Markdown"
        })
        threading.Thread(target=battery_monitor, args=(token,), daemon=True).start()

    offset = 0
    while True:
        try:
            r = session.get(f"{api_url}/getUpdates", params={"offset": offset, "timeout": 10})
            data = r.json()
            if not data.get("result"):
                continue

            for update in data["result"]:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                thread_id = msg.get("message_thread_id")

                if not chat_id:
                    continue

                # Extracting User Details
                user_info = msg.get("from", {})
                user_id = user_info.get("id") # Fixed: added this line
                username = user_info.get("username", "No Username")
                first_name = user_info.get("first_name", "No First Name")
                last_name = user_info.get("last_name", "") # Added to avoid crash in name concat

                # Create a dictionary to hold the current log entry
                log_entry = {
                    "bot": bot_name,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": {
                        "id": user_id,
                        "username": username,
                        "name": f"{first_name} {last_name}".strip()
                    },
                    "chat_id": chat_id,
                    "type": "text", # Default type
                    "content": msg.get("text") # Default content
                }

                # Check for media types dynamically
                media_types = {
                    "photo": lambda m: m["photo"][-1]["file_id"],
                    "video": lambda m: m["video"]["file_id"],
                    "document": lambda m: m["document"]["file_id"],
                    "audio": lambda m: m["audio"]["file_id"],
                    "voice": lambda m: m["voice"]["file_id"]
                }

                for m_type, get_id in media_types.items():
                    if m_type in msg:
                        log_entry["type"] = m_type
                        log_entry["content"] = get_id(msg)
                        break

                # SAVE TO FILE HERE
                save_to_json(log_entry)

                # IMPORTANT: We now pass 'msg' (the whole dictionary) instead of just 'text'
                response = tools.process_logic(msg, bot_name, admin_id, token)

                if response == "DELETE_MESSAGE":
                    session.post(
                        f"{api_url}/deleteMessage",
                        data={
                            "chat_id": chat_id,
                            "message_id": msg.get("message_id")
                        }
                    )
                    continue
                
                if response == "CLEAR_LOGS":
                    try:
                        if os.path.exists(LOG_FILE):
                            os.remove(LOG_FILE)
                            print("----- LOGS removed -----")
                            response = {
                                "type": "text",
                                "data": "🗑️ Logs have been cleared successfully."
                            }

                        else:
                            response = {
                                "type": "text",
                                "data": "info: Log file was already empty."
                            }

                    except Exception as e:
                        response = {
                            "type": "text",
                            "data": f"Error clearing logs: {e}"
                        }

                elif response == "UPLOAD_LOGS":
                    try:
                        if os.path.exists(LOG_FILE):
                            response = {
                                "type": "document",
                                "data": LOG_FILE,
                                "caption": "📊 Here is the current activity database."
                            }
                            print("----- LOGS uploaded -----")

                        else:
                            response = {
                                "type": "text",
                                "data": "info: Log file was already empty."
                            }

                    except Exception as e:
                        response = {
                            "type": "text",
                            "data": f"Error clearing logs: {e}"
                        }

                elif response == "BOT_RELOAD":
                    # 1. Pull latest code from GitHub
                    try:
                        # 'cwd=BASE_DIR' ensures git runs in your project root
                        pull_result = subprocess.run(
                            ["git", "pull", "origin", "main"], 
                            cwd=BASE_DIR, 
                            capture_output=True, 
                            text=True
                        )
                        pull_msg = "✅ Git: " + (pull_result.stdout[:50] if pull_result.returncode == 0 else "Pull failed")
                    except Exception as e:
                        pull_msg = f"❌ Git Error: {str(e)}"

                    # 2. Reload the Python modules
                    importlib.reload(tools)
                    
                    response = {
                        "type": "text",
                        "data": (
                            "---------------------------------------------------\n"
                            "        🔄 *System Refreshed!*\n"
                            "---------------------------------------------------\n\n"
                            f" {pull_msg}"
                        )
                    }

                if response and isinstance(response, dict):
                    res_type = response.get("type", "text")
                    data_content = response.get("data")
                    payload = {
                        "chat_id": chat_id,
                        "message_thread_id": thread_id,
                        "parse_mode": "Markdown"
                    }

                    # Reply and Delete logic
                    if response.get("reply_to"):
                        payload["reply_to_message_id"] = msg.get("message_id")

                    if response.get("delete_original"):
                        session.post(
                            f"{api_url}/deleteMessage",
                            data={
                                "chat_id": chat_id,
                                "message_id": msg.get("message_id")
                                }
                            )

                    # Mapping types to Telegram methods and parameters
                    methods = {
                        "text": ("sendMessage", "text"),
                        "photo": ("sendPhoto", "photo"),
                        "video": ("sendVideo", "video"),
                        "document": ("sendDocument", "document"),
                        "audio": ("sendAudio", "audio")
                    }

                    if res_type in methods:
                        method_name, param_name = methods[res_type]
                        data_content = response.get("data")

                        # Prepare standard payload
                        payload["parse_mode"] = "Markdown"
                        if response.get("caption"):
                            payload["caption"] = response["caption"]

                        # --- FILE UPLOAD LOGIC ---
                        # Check if the data is a valid local file path (for JSON logs)
                        if isinstance(data_content, str) and os.path.exists(data_content):
                            with open(data_content, "rb") as f:
                                session.post(
                                    f"{api_url}/{method_name}", 
                                    data=payload, 
                                    files={param_name: f}
                                )
                        else:
                            # Standard message (text or file_id)
                            payload[param_name] = data_content
                            session.post(
                                f"{api_url}/{method_name}",
                                data=payload
                            )

        except Exception as e:
            print(f"Error in {bot_name}: {e}")
            time.sleep(5)

def run_all_bots():
    # bots is the dictionary of { "Name": "Token" }
    bots = CONFIG.get('bots', {})

    for name, token in bots.items():
        # We pass the global BOT_ADMIN into the worker
        t = threading.Thread(target=bot_worker, args=(name, token, BOT_ADMIN))
        t.daemon = True
        t.start()
        time.sleep(0.5)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    run_all_bots()
