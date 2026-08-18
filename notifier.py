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

def send_copilot_order_ticket_alert(symbol: str, action: str, price: float, target: float, stop_loss: float, ai_conf: float, usdt_amount: float = 5.00) -> bool:
    """Sends the Exact 15-Second Binance Copy-Paste Order Sheet to Telegram"""
    clean_sym = f"{symbol}/USDT" if "/" not in symbol else symbol
    if "BITCOIN" in symbol: clean_sym = "BTC/USDT"
    elif "ETHEREUM" in symbol: clean_sym = "ETH/USDT"
    elif "SOLANA" in symbol: clean_sym = "SOL/USDT"
    elif "BNB" in symbol: clean_sym = "BNB/USDT"
    elif "XRP" in symbol: clean_sym = "XRP/USDT"

    msg = f"""🎯 <b>ANTONY AI CO-PILOT — BINANCE SPOT ORDER SHEET</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• <b>Symbol / Pair</b>     : <code>{clean_sym}</code>
• <b>Action</b>            : <b>{action} LIMIT ORDER</b> 🟢

📍 <b>PRICE FIELD</b>      ➔ Type: <code>${price:,.2f}</code>
📍 <b>TOTAL FIELD</b>      ➔ Type: <code>{usdt_amount:.2f} USDT</code>

☑️ <b>Check [x] TP/SL Box on Binance:</b>
🎯 <b>TAKE PROFIT (TP)</b> ➔ Type: <code>${target:,.2f}</code> (+6.0% Gain)
🛡️ <b>STOP LOSS (SL)</b>   ➔ Type: <code>${stop_loss:,.2f}</code> (-3.0% Risk Cap)

🤖 <b>AI CONFIDENCE</b>    ➔ <b>{ai_conf:.1f}%</b> (Institutional Rules Passed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>15-Second Copy-Paste Execution | Zero API Stress</i>"""
    return send_telegram_alert(msg)