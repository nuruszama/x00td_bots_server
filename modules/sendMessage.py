import requests

def run(msg, token, log_entry):
    text = log_entry["text_content"]
    if text.lower() == "!ping":
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={
            "chat_id": log_entry["chat_id"],
            "text": "🏓 **Pong!** System engine is online and fully responsive.",
            "parse_mode": "Markdown"
        })