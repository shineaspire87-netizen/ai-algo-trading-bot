# notifier.py - Bulletproof Dual-Route Telegram Notifier

import requests
import logging
import html
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_alert(message: str, parse_mode: str = "HTML") -> bool:
    """HTML Error Fallback உடன் கூடிய Dual-Route Telegram Alert Engine"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("⚠️ Telegram Token or Chat ID Missing in Config/Secrets!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Route 1: Try Sending with HTML Parse Mode
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logging.info("✅ Telegram HTML Alert Delivered Successfully.")
            return True
        else:
            logging.warning(f"⚠️ Telegram HTML Route Failed ({response.status_code}): {response.text}")
    except Exception as e:
        logging.error(f"❌ Telegram Route 1 Error: {e}")

    # Route 2: Fallback to Clean Plain Text (Strips HTML tags if Route 1 fails)
    try:
        clean_text = message.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<code>", "").replace("</code>", "")
        fallback_payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": clean_text
        }
        fallback_res = requests.post(url, json=fallback_payload, timeout=5)
        if fallback_res.status_code == 200:
            logging.info("✅ Telegram Fallback Plain-Text Alert Delivered.")
            return True
        else:
            logging.error(f"❌ Telegram Fallback Route Failed ({fallback_res.status_code}): {fallback_res.text}")
    except Exception as e:
        logging.error(f"❌ Telegram Route 2 Error: {e}")

    return False