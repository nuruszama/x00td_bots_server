import os
import sys
import json
import time
import requests
import datetime
import threading

import modules_manager # Import the modules manager for dynamic feature handling
import master_control  # Import the separate master logic

# define bot configurations and logging files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
ACTIVITY_LOG = os.path.join(BASE_DIR, 'activity_logs.txt')
BOT_LOG = os.path.join(BASE_DIR, 'bot_logs.txt')

# load configuration from JSON file
def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f: return json.load(f)
    except Exception as e:
        print(f"❌ Core configuration failure: {e}"); return {}

CONFIG = load_config()

# define constants for logging the system events
def system_logger(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    print(log_line.strip())
    with open(BOT_LOG, "a", encoding="utf-8") as f: f.write(log_line)

# define the structure for the bot activity log entries
def flatten_telegram_update(msg, bot_name):
    user = msg.get("from", {})
    chat = msg.get("chat", {})
    structure = {
        "bot_instance": bot_name,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message_id": msg.get("message_id", ""),
        "user_id": user.get("id", ""),
        "username": user.get("username", ""),
        "full_name": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
        "chat_id": chat.get("id", ""),
        "chat_title": chat.get("title", "Private"),
        "chat_type": chat.get("type", ""),
        "text_content": (msg.get("text") or msg.get("caption") or "").strip(),
        "media_type": "none",
        "media_file_id": ""
    }
    media_keys = ["photo", "video", "document", "audio", "voice", "poll"]
    for k in media_keys:
        if k in msg:
            structure["media_type"] = k
            if k == "photo": structure["media_file_id"] = msg["photo"][-1]["file_id"]
            elif k == "poll": structure["media_file_id"] = msg["poll"]["id"]
            else: structure["media_file_id"] = msg[k]["file_id"]
            break
    return structure

# Define the function to commit structured activity logs to a file
def commit_activity_log(structured_entry):
    try:
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f: f.write(json.dumps(structured_entry) + "\n")
    except Exception as e: system_logger(f"Failed writing activity record: {e}")

# Define the function to transmit files to a Telegram chat
def transmit_file(token, chat_id, filepath, caption):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0: return False
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            r = requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"document": f}, timeout=30)
            return r.json().get("ok", False)
    except Exception as e:
        system_logger(f"File sync network error: {e}")
        return False

# 
def maintenance_scheduler():
    """Reads execution thresholds parameters cleanly from master_config.json."""
    system_logger("📅 Daily scheduler routine initiated.")
    m_config = master_control.load_master_config()
    master_bot_token = m_config.get("master_bot_token", "")
    dump_group = str(m_config.get("dump_group_id", ""))
    dump_time = m_config.get("dump_time", "00:00")
    
    if not master_bot_token or not dump_group:
        system_logger("⚠️ Scheduler halted: Missing master credentials for automated dumps.")
        return

    while True:
        try:
            if datetime.datetime.now().strftime("%H:%M") == dump_time:
                system_logger("⏰ Target dump threshold reached. Beginning backup chain...")
                if os.path.exists(ACTIVITY_LOG):
                    transmit_file(master_bot_token, dump_group, ACTIVITY_LOG, "📊 Daily Activity Log Dump")
                    os.remove(ACTIVITY_LOG)
                if os.path.exists(BOT_LOG):
                    transmit_file(master_bot_token, dump_group, BOT_LOG, "🛠️ Daily System Status Log Dump")
                    os.remove(BOT_LOG)
                system_logger("🔄 Log flush complete. Hot-rebooting runtime engines...")
                os.execv(sys.executable, ['python'] + sys.argv)
            time.sleep(50)
        except Exception as e:
            system_logger(f"Scheduler core error: {e}"); time.sleep(10)

# 
def client_polling_worker(bot_name, token):
    system_logger(f"✅ Launching client bot framework worker for [{bot_name}]")
    offset = 0
    url = f"https://api.telegram.org/bot{token}"

    while True:
        try:
            r = requests.get(f"{url}/getUpdates", params={"offset": offset, "timeout": 10}, timeout=15)
            if r.status_code != 200: time.sleep(5); continue
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message") or update.get("edited_message")
                if not msg: continue
                
                log_entry = flatten_telegram_update(msg, bot_name)
                commit_activity_log(log_entry)

                active_features = modules_manager.ACTIVE_MATRIX.get(bot_name, [])
                for feature in active_features:
                    try:
                        import importlib
                        mod = importlib.import_module(f"modules.{feature}")
                        importlib.reload(mod)
                        mod.run(msg, token, log_entry)
                    except Exception as feature_err:
                        system_logger(f"💥 Runtime Module Crash [{feature}] via Bot [{bot_name}]: {feature_err}")
        except Exception as loop_error:
            system_logger(f"⚠️ Network error loop intercept on [{bot_name}]: {loop_error}")
            time.sleep(5)

def main():
    system_logger("🚀 Initiating modular multi-bot infrastructure framework...")
    modules_manager.sync_modules_matrix()
    
    # Boot up Master Control Thread seamlessly with zero parameters
    threading.Thread(target=master_control.run_master_loop, daemon=True).start()
    
    # Start Maintenance Lifecycle Scheduler Tasks
    threading.Thread(target=maintenance_scheduler, daemon=True).start()
    
    # Boot up all standard Client Bots from standard config mapping
    bots_dict = CONFIG.get("bots", {})
    for name, token in bots_dict.items():
        t = threading.Thread(target=client_polling_worker, args=(name, token))
        t.daemon = True
        t.start()
        
    while True: time.sleep(1)

if __name__ == "__main__":
    main()