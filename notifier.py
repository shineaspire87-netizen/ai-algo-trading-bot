import requests
import os
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except Exception:
    TELEGRAM_BOT_TOKEN = "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE"
    TELEGRAM_CHAT_ID = "1072750499"

if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE"
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = "1072750499"

def send_telegram_alert(message_html: str) -> bool:
    """Send immediate Telegram push alert with sound"""
    if not message_html or not message_html.strip():
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_notification": False  # LOUD SOUND ALERT!
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return True
        # Plain text fallback
        clean_text = message_html.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<code>", "").replace("</code>", "")
        fallback_res = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": clean_text, "disable_notification": False}, timeout=5)
        return fallback_res.status_code == 200
    except Exception as e:
        print(f"Telegram Alert Error: {e}")
        return False