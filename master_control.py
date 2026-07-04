import os
import time
import json
import requests
import datetime
import threading
import subprocess
import modules_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_CONFIG_PATH = os.path.join(BASE_DIR, 'master_config.json')
CLIENT_CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

def load_master_config():
    try:
        with open(MASTER_CONFIG_PATH, 'r') as f: return json.load(f)
    except Exception as e:
        print(f"❌ Master Configuration read error: {e}"); return {}

def load_client_bot_names():
    try:
        with open(CLIENT_CONFIG_PATH, 'r') as f:
            return list(json.load(f).get("bots", {}).keys())
    except:
        return []

# --- Android Hardware Integration Layer ---
def get_battery_info():
    """Reads capacity nodes directly from the underlying Linux system sysfs structure."""
    try:
        level = subprocess.check_output("cat /sys/class/power_supply/battery/capacity", shell=True).decode().strip()
        status = subprocess.check_output("cat /sys/class/power_supply/battery/status", shell=True).decode().strip()
        return int(level), status
    except:
        return None, None

def battery_monitor_loop(token, admin_id):
    """Background safety guard thread preventing overcharging or dead server cycles."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    last_alert = None
    
    while True:
        try:
            level, status = get_battery_info()
            if level is not None:
                if level <= 20 and status != "Charging" and last_alert != "low":
                    requests.post(url, data={"chat_id": admin_id, "text": f"⚠️ *Battery Low: {level}%*\nPlease plug in the charger!", "parse_mode": "Markdown"})
                    last_alert = "low"
                elif level >= 90 and status == "Charging" and last_alert != "high":
                    requests.post(url, data={"chat_id": admin_id, "text": f"✅ *Battery Charged: {level}%*\nYou can unplug the charger now.", "parse_mode": "Markdown"})
                    last_alert = "high"
                elif 25 < level < 85:
                    last_alert = None
        except Exception as e:
            print(f"⚠️ Battery Guard warning: {e}")
        time.sleep(300)

# --- Interactive Text Frame Formatters ---
def get_help_text(master_bot_name):
    return (
        "📦 *System:* X00TD / Snapdragon 636\n"
        "----------------------------------------------------------------\n"
        f"        🤖 *{master_bot_name} Admin Panel*\n"
        "----------------------------------------------------------------\n"
        "/start         - Alive check\n"
        "/help          - Command list\n"
        "/status       - Battery & Instance info\n"
        "/ip               - Server & SMB Info\n"
        "/chatlogs     - Activity Database\n"
        "/botlogs       - bot background logs\n"
        "/dashboard  - Manage Bots\n"
        "/reload       - Hot-reload all logic"
    )

def get_start_text():
    return (
        "👑 *Master Control Engine*\n"
        "────────────────────\n"
        "Welcome to the Master Control Engine. This interface allows you to manage all active bot instances and their modular features.\n\n"
        "Use `/dashboard` or the menus below to handle functional allocations dynamically."
    )

def get_status_text(master_bot_name):
    level, status_text = get_battery_info()
    batt_display = f"{level}% ({status_text})" if level is not None else "Unavailable (Check permissions)"
    
    return (
        "📊 *System Status*\n"
        "────────────────────\n"
        f"🕒 Current Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🤖 Master Bot: {master_bot_name}\n"
        f"🔋 Battery: {batt_display}\n"
        f"🔧 Active Modules: {len(modules_manager.fetch_available_modules())}\n"
        f"📦 Managed Bots: {len(load_client_bot_names())}\n"
    )

def get_ip_info_text():
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        public_ip = response.json().get("ip", "Unknown")
        local_ip = os.popen("hostname -I").read().strip().split()[0]
    except:
        public_ip = "Unavailable"
        local_ip = "127.0.0.1"

    try:
        nodename = os.uname().nodename
        sysname = os.uname().sysname
        release = os.uname().release
    except:
        nodename = "Snapdragon-Chroot"
        sysname = "Linux"
        release = "Android-Kernel"

    return (
        "🌐 *Network Information*\n"
        "────────────────────\n"
        f"📡 Public IP: {public_ip}\n"
        f"🖥️ Server Hostname: {nodename}\n"
        f"💻 Platform: {sysname} {release}\n"
        f"🌐 *Local IP:* `{local_ip}`\n"
        f"📂 *SMB:* `\\\\{local_ip}\\storage`\n"
        f"👤 *User:* `x00td`"
    )

# --- Dashboard Layout Generator ---
def send_master_dashboard(url, chat_id, message_id=None):
    modules_manager.sync_modules_matrix()
    client_bots = load_client_bot_names()
    
    text = "🛠️ *System Core Master Dashboard*\n"
    text += "────────────────────\n"
    text += f"📅 *Time:* {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    text += "Select a target bot instance to manage active feature allocations:\n"
    
    inline_keyboard = []
    for username in client_bots:
        inline_keyboard.append([{"text": f"@{username}", "callback_data": f"manage:{username}"}])
        
    inline_keyboard.append([{"text": "🔄 Dynamic Module Reload", "callback_data": "core_reload"}])
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps({"inline_keyboard": inline_keyboard})
    }
    
    if message_id:
        payload["message_id"] = message_id
        requests.post(f"{url}/editMessageText", data=payload)
    else:
        requests.post(f"{url}/sendMessage", data=payload)

def handle_master_bot_callback(url, callback_query):
    qid = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    message_id = callback_query.get("message", {}).get("message_id")
    data = callback_query.get("data", "")
    
    requests.post(f"{url}/answerCallbackQuery", data={"callback_query_id": qid})
    
    if data == "menu_main":
        send_master_dashboard(url, chat_id, message_id)
        return
        
    if data == "core_reload":
        modules_manager.sync_modules_matrix()
        requests.post(f"{url}/sendMessage", data={"chat_id": chat_id, "text": "🔄 Active modules table reloaded from storage directory."})
        send_master_dashboard(url, chat_id, message_id)
        return

    if data.startswith("manage:"):
        target_bot = data.split(":")[1]
        available_mods = modules_manager.fetch_available_modules()
        
        with open(modules_manager.MATRIX_JSON, 'r') as f:
            current_matrix = json.load(f)
        active_mods = current_matrix.get(target_bot, [])
        
        text = f"⚙️ *Managing Bot Instance:* `{target_bot}`\n"
        text += "────────────────────\n"
        text += "Toggle individual modular packages below:\n\n"
        
        inline_keyboard = []
        for m in available_mods:
            is_active = m in active_mods
            status_indicator = "🟢 Enabled" if is_active else "🔴 Disabled"
            btn_text = f"{m} [{status_indicator}]"
            callback_action = f"toggle:{target_bot}:{m}:{ 'off' if is_active else 'on' }"
            inline_keyboard.append([{"text": btn_text, "callback_data": callback_action}])
            
        inline_keyboard.append([{"text": "⬅️ Back to Dashboard", "callback_data": "menu_main"}])
        
        requests.post(f"{url}/editMessageText", data={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": inline_keyboard})
        })
        return

    if data.startswith("toggle:"):
        _, target_bot, module_name, intent = data.split(":")
        state = True if intent == "on" else False
        modules_manager.toggle_bot_feature(target_bot, module_name, state)
        handle_master_bot_callback(url, {"id": qid, "message": {"chat": {"id": chat_id}, "message_id": message_id}, "data": f"manage:{target_bot}"})

# --- Main Runtime Daemon Loop ---
def run_master_loop():
    m_config = load_master_config()
    master_bot_name = m_config.get("master_bot_name", "MasterBot")
    token = m_config.get("master_bot_token", "")
    admin_id = str(m_config.get("bot_admin_id", ""))
    
    if not token or not admin_id:
        print("❌ Master loop aborted: Invalid configuration properties.")
        return

    # Start the hardware monitor sub-thread
    threading.Thread(target=battery_monitor_loop, args=(token, admin_id), daemon=True).start()

    print(f"👑 Master Control Engine active for [{master_bot_name}]")
    offset = 0
    url = f"https://api.telegram.org/bot{token}"
    
    while True:
        try:
            r = requests.get(f"{url}/getUpdates", params={"offset": offset, "timeout": 10}, timeout=15)
            if r.status_code != 200:
                time.sleep(5); continue
                
            payload = r.json()
            for update in payload.get("result", []):
                offset = update["update_id"] + 1
                
                if "callback_query" in update:
                    cb = update["callback_query"]
                    if str(cb.get("from", {}).get("id")) == admin_id:
                        handle_master_bot_callback(url, cb)
                    continue
                
                msg = update.get("message") or update.get("edited_message")
                if not msg: continue
                
                user_id = str(msg.get("from", {}).get("id", ""))
                text = (msg.get("text") or "").strip().lower()
                chat_id = msg.get("chat", {}).get("id")
                
                if user_id != admin_id: continue
                
                # Command routing logic mapping
                if text == "/start":
                    requests.post(f"{url}/sendMessage", data={"chat_id": chat_id, "text": get_start_text(), "parse_mode": "Markdown"})
                elif text in ["/help", "!help"]:
                    requests.post(f"{url}/sendMessage", data={"chat_id": chat_id, "text": get_help_text(master_bot_name), "parse_mode": "Markdown"})
                elif text == "/status":
                    requests.post(f"{url}/sendMessage", data={"chat_id": chat_id, "text": get_status_text(master_bot_name), "parse_mode": "Markdown"})
                elif text == "/ip":
                    requests.post(f"{url}/sendMessage", data={"chat_id": chat_id, "text": get_ip_info_text(), "parse_mode": "Markdown"})
                elif text == "/dashboard":
                    send_master_dashboard(url, chat_id)
                elif text == "/reload":
                    modules_manager.sync_modules_matrix()
                    requests.post(f"{url}/sendMessage", data={"chat_id": chat_id, "text": "🔄 Active matrix forced reload. Modules cleared and synced."})
                elif text in ["/chatlogs", "/botlogs"]:
                    filename = "activity_logs.txt" if text == "/chatlogs" else "bot_logs.txt"
                    filepath = os.path.join(BASE_DIR, filename)
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        with open(filepath, 'rb') as doc:
                            requests.post(f"{url}/sendDocument", data={"chat_id": chat_id, "caption": f"📄 Requested Log: {filename}"}, files={"document": doc})
                    else:
                        requests.post(f"{url}/sendMessage", data={"chat_id": chat_id, "text": f"⚠️ File `{filename}` is completely empty or missing.", "parse_mode": "Markdown"})
                    
        except Exception as e:
            print(f"⚠️ Master Control engine loop intercept error: {e}")
            time.sleep(5)