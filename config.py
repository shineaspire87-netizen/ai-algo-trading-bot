# config.py - Zerodha API & Institutional Trading Parameters
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
USER_ID = "your_zerodha_user_id"

# BankNifty & Nifty Index Constants
INDEX_SYMBOL = "NSE:NIFTY BANK"
LOT_SIZE = 15                 # BankNifty Lot Size
STOP_LOSS_PERCENT = 0.15      # 15% Baseline SL
TARGET_PERCENT = 0.30         # 30% Baseline Target (1:2 RRR)

# 🟢 SEBI QUANTITY FREEZE LIMITS (SEBI Mandate)
SEBI_FREEZE_LIMITS = {
    "NIFTY50": 1755,    # 27 Lots (Max single order cap 1800)
    "BANKNIFTY": 600,   # 20 Lots
    "DEFAULT": 1800
}

# 🟢 INDIA VIX OPERATIONAL REGIMES
VIX_REGIMES = {
    "COMPLACENT": {"max_vix": 12.0, "atr_multiplier": 1.5, "position_scale": 1.2, "label": "Complacent (Trend Bias)"},
    "NORMAL":     {"max_vix": 18.0, "atr_multiplier": 2.0, "position_scale": 1.0, "label": "Normal (Scalp / Mean Reversion)"},
    "ELEVATED":   {"max_vix": 25.0, "atr_multiplier": 3.0, "position_scale": 0.6, "label": "Elevated (Defined-Risk Spreads)"},
    "CRISIS":     {"max_vix": 99.0, "atr_multiplier": 4.0, "position_scale": 0.0, "label": "Crisis (Kill-Switch Active)"}
}

# 🟢 SIDEWAYS REGIME THRESHOLDS
HURST_THRESHOLD = 0.45   # H < 0.45 indicates mean-reverting sideways chop
ADX_SIDEWAYS_MAX = 20.0  # ADX < 20 indicates weak trend

# 🟢 UNIFIED BROKER & INTEGRATION ENGINE PARAMETERS
ACTIVE_BROKER = "ZERODHA"
PAPER_TRADING_MODE = True

ZERODHA_CONFIG = {
    "API_KEY": API_KEY,
    "ACCESS_TOKEN": "your_zerodha_access_token"
}

DHAN_CONFIG = {
    "CLIENT_ID": "your_dhan_client_id",
    "ACCESS_TOKEN": "your_dhan_access_token"
}

# 🟢 CLOUD SYNC & SYSTEM HEALTH
GOOGLE_SHEET_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyavkzC8zCDG0gR274a3EiusQ1ji72mMi6_Ot5dT0L0r0uXfxDHfEnF87NVniJXyybg/exec"
TELEGRAM_BOT_TOKEN = "7864817112:AAFq2c4N3M055W6u1g0wY6q0P5bBqY"
TELEGRAM_CHAT_ID = "1388656143"