import importlib

# Initial Imports
from modules import ghost_logic
from modules import creek_logic
from modules import jegru_logic
from modules import ciper_logic
from modules import saiha_logic
from modules import twitzi_logic
from modules import sweet_logic

def process_logic(msg, bot_name, admin_id, token):
    # Reload all sub-modules whenever tools itself is reloaded
    # This ensures changes to ghost_logic, jegru_logic, etc., take effect.
    importlib.reload(ghost_logic)
    importlib.reload(creek_logic)
    importlib.reload(jegru_logic)
    importlib.reload(ciper_logic)
    importlib.reload(saiha_logic)
    importlib.reload(twitzi_logic)
    importlib.reload(sweet_logic)

    # Map bot names to their specific modules
    bot_map = {
        "TD-Ghost": ghost_logic,
        "Creek-Lab": creek_logic,
        "Phoenix-Jegru": jegru_logic,
        "Ciper-Wire": ciper_logic,
        "Saihabath": saiha_logic,
        "Twitzi": twitzi_logic,
        "Sweety": sweet_logic
    }

    # Routing Logic
    target_module = bot_map.get(bot_name)

    if target_module:
        # We now pass both admin_id AND token to every single module
        # This allows every bot to check admin rights and send its own logs
        return target_module.process_logic(msg, bot_name, admin_id, token)
    
    # Fallback or Global Logic
    text = msg.get("text", "").lower().strip()
    if text == "/ping":
        return {
            "type": "text",
            "data": f"Pong! {bot_name} is standing by."
        }

    return None
