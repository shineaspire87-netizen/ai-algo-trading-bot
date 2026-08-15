# notifier.py - Telegram Instant Mobile Alert Engine
import requests

# ⚠️ உங்களின் Telegram விவரங்களை இங்கே போடவும்
TELEGRAM_BOT_TOKEN = "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE"  # BotFather தந்த Token
TELEGRAM_CHAT_ID = "1072750499"      # userinfobot தந்த Chat ID

def send_telegram_alert(message):
    """டெலிகிராமிற்கு நேரலை எச்சரிக்கை மெசேஜ் அனுப்பும்"""
    if TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        print("[TELEGRAM] Token இல்லை. மெசேஜ் அனுப்பப்படவில்லை.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

if __name__ == "__main__":
    # டெஸ்ட் மெசேஜ்
    send_telegram_alert("🚀 <b>AI ALGO TRADING BOT CONNECTED!</b>\n\nடெலிகிராம் மொபைல் அலர்ட் வெற்றிகரமாக இணைக்கப்பட்டது!")
    print("✅ டெலிகிராம் டெஸ்ட் மெசேஜ் அனுப்பப்பட்டது. உங்கள் மொபைலைச் சரிபார்க்கவும்!")