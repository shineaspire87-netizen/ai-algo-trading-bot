# system_health.py
import requests

def check_system_integrity(sheets_url, telegram_token):
    status = {"sheets": False, "telegram": False}
    try:
        r = requests.get(sheets_url, timeout=4)
        status["sheets"] = (r.status_code == 200)
    except:
        status["sheets"] = False
        
    try:
        r = requests.get(f"https://api.telegram.org/bot{telegram_token}/getMe", timeout=4)
        status["telegram"] = (r.status_code == 200)
    except:
        status["telegram"] = False
        
    return status
