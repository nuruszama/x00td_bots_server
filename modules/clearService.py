import requests

def run(msg, token, log_entry):
    # Check if a system/service payload key exists in the raw message dictionary
    service_keys = ["new_chat_members", "left_chat_member", "new_chat_title", "new_chat_photo"]
    if any(key in msg for key in service_keys):
        url = f"https://api.telegram.org/bot{token}/deleteMessage"
        requests.post(url, data={
            "chat_id": log_entry["chat_id"],
            "message_id": log_entry["message_id"]
        })