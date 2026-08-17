# config.py - Locked 100% Bitcoin Pure Focus Configuration

ACTIVE_ASSET_MODE = "BITCOIN_PURE_FOCUS"
DEFAULT_ASSET = "BITCOIN"

# Crypto Bitcoin Specific Risk Calibration ($)
CRYPTO_RISK_RULES = {
    "LOT_QUANTITY": 15,
    "MAX_LOSS_CAP_USD": -25.00,       # Strict -$25.00 Cut Loss
    "PROFIT_LOCK_TRIGGER_USD": 35.00, # Trigger +$35.00 Floating Gain
    "PROFIT_LOCK_AMOUNT_USD": 15.00,  # Lock +$15.00 Net Profit
    "TARGET_1_USD": 50.00,            # +$50.00 Target 1 (+6%)
    "TARGET_2_USD": 100.00,           # +$100.00 Target 2 (+12%)
}

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
TELEGRAM_BOT_TOKEN = "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE"
TELEGRAM_CHAT_ID = "1072750499"

# 🟢 GOOGLE AI STUDIO GEMINI API CONFIGURATION
GEMINI_API_KEY = "AIzaSyB2qbWqyI6gxy8mNty3ZmVPCIols5l8mhM"