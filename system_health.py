# system_health.py
import requests
import logging
from config import GOOGLE_SHEET_WEB_APP_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def run_system_diagnostic_check():
    health_status = {"Google_Sheets_DB": False, "Telegram_Notifier": False, "Data_Feed": False}
    
    # 1. Google Sheets V2 Cloud DB Ping Check
    try:
        res = requests.get(GOOGLE_SHEET_WEB_APP_URL, timeout=5)
        if res.status_code == 200:
            health_status["Google_Sheets_DB"] = True
    except Exception as e:
        logging.error(f"❌ Cloud DB Connection Failed: {e}")

    # 2. Telegram Dual-Route Notifier Check
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            health_status["Telegram_Notifier"] = True
    except Exception as e:
        logging.error(f"❌ Telegram Connection Failed: {e}")

    return health_status
