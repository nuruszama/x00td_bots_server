import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(BASE_DIR, 'modules')
MATRIX_JSON = os.path.join(BASE_DIR, 'bot_modules.json')
CLIENT_CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

ACTIVE_MATRIX = {}

def fetch_available_modules():
    if not os.path.exists(MODULES_DIR): os.makedirs(MODULES_DIR)
    return [f[:-3] for f in os.listdir(MODULES_DIR) if f.endswith('.py') and not f.startswith('__')]

def sync_modules_matrix():
    global ACTIVE_MATRIX
    available = fetch_available_modules()
    
    try:
        with open(CLIENT_CONFIG_PATH, 'r') as f:
            client_bots = list(json.load(f).get("bots", {}).keys())
    except:
        client_bots = []

    if not os.path.exists(MATRIX_JSON):
        initial_map = {bot_name: [] for bot_name in client_bots}
        with open(MATRIX_JSON, 'w') as f: json.dump(initial_map, f, indent=4)

    try:
        with open(MATRIX_JSON, 'r') as f: saved_matrix = json.load(f)
    except:
        saved_matrix = {}

    cleaned_matrix = {}
    for bot in client_bots:
        assigned = saved_matrix.get(bot, [])
        cleaned_matrix[bot] = [m for m in assigned if m in available]

    ACTIVE_MATRIX = cleaned_matrix
    with open(MATRIX_JSON, 'w') as f: json.dump(cleaned_matrix, f, indent=4)

def toggle_bot_feature(bot_name, feature_module, status: bool):
    available = fetch_available_modules()
    if feature_module not in available: return False

    try:
        with open(MATRIX_JSON, 'r') as f: data = json.load(f)
    except: data = {}

    if bot_name not in data: data[bot_name] = []

    if status and feature_module not in data[bot_name]: 
        data[bot_name].append(feature_module)
    elif not status and feature_module in data[bot_name]: 
        data[bot_name].remove(feature_module)

    try:
        with open(MATRIX_JSON, 'w') as f: json.dump(data, f, indent=4)
        sync_modules_matrix()
        return True
    except:
        return False