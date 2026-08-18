# ================================================================================
# ANTONY QUANT AI TERMINAL - CONFIGURATION ENGINE (NIFTY 50 EDITION)
# ================================================================================
import os

# --- CORE TRADING MODE ---
PRIMARY_MODE = "NIFTY50_OPTIONS"  # Primary focus mode
DEFAULT_SYMBOL = "^NSEI"           # Yahoo Finance Ticker for NIFTY 50
ALT_SYMBOL = "^NSEBANK"            # Bank Nifty Ticker
TIMEFRAME = "15m"                  # 15-Minute Candle (Pressure-Free Execution)
SECONDARY_TIMEFRAME = "5m"         # 5-Minute Candle (Micro scalp option)

# --- NIFTY OPTIONS RISK PARAMETERS (RUPEES ₹) ---
NIFTY_LOT_SIZE = 25               # Shares per 1 NIFTY Lot (or 50/75 as per index)
LOT_SIZE = 25
DEFAULT_LOTS = 1                   # Initial Trading Size (1 Lot)

# Option Premium Point Targets (Example: ₹15 SL, ₹20 TP1, ₹45 TP2)
STOP_LOSS_POINTS = 15.0            # Strict Risk per Lot (15 points = ₹375)
TARGET_1_POINTS = 20.0             # Quick Target (20 points = ₹500)
TARGET_2_POINTS = 45.0             # Trend Target (45 points = ₹1,125)

# --- RISK CONTROL LIMITS ---
MAX_DAILY_TRADES = 3               # Maximum trades allowed per day
CONSECUTIVE_LOSS_LOCK = 2          # Lock terminal after 2 consecutive losses
SAFE_MID_CANDLE_START = 60         # Wait 60s after 15M candle opens
SAFE_MID_CANDLE_END = 840          # Stop entries 60s before 15M candle closes

# --- SEBI QUANTITY FREEZE LIMITS ---
SEBI_FREEZE_LIMITS = {
    "NIFTY50": 1755,    # 27 Lots
    "BANKNIFTY": 600,   # 20 Lots
    "DEFAULT": 1800
}

# --- BROKER & INTEGRATION ENGINE PARAMETERS ---
ACTIVE_BROKER = "ZERODHA"
PAPER_TRADING_MODE = True

# --- TELEGRAM & CLOUD SYNC CONFIGURATION ---
GOOGLE_SHEET_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyavkzC8zCDG0gR274a3EiusQ1ji72mMi6_Ot5dT0L0r0uXfxDHfEnF87NVniJXyybg/exec"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1072750499")

# --- GOOGLE AI STUDIO GEMINI API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB2qbWqyI6gxy8mNty3ZmVPCIols5l8mhM")