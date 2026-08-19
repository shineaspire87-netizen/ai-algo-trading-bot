# ================================================================================
# ANTONY QUANT AI TERMINAL - CONFIGURATION ENGINE (DUAL ASSET EDITION)
# ================================================================================
import os
from datetime import time

PRIMARY_MODE = "NIFTY50_OPTIONS"
DEFAULT_SYMBOL = "^NSEI"           # NIFTY 50 Ticker
BTC_SYMBOL = "BTC-USD"             # Bitcoin Live Ticker
VIX_SYMBOL = "^INDIAVIX"           # India VIX Ticker
TIMEFRAME = "15m"                  # 15-Minute Candle Timeframe

# --- NIFTY OPTIONS RISK PARAMETERS (RUPEES ₹) ---
NIFTY_LOT_SIZE = 25
DEFAULT_LOTS = 1
STOP_LOSS_POINTS = 15.0            # -15 pts (₹375 / lot)
TARGET_1_POINTS = 20.0             # +20 pts (₹500 / lot)
TARGET_2_POINTS = 45.0             # +45 pts (₹1,125 / lot)
UNDERLYING_TARGET_NIFTY = 30.0

# --- BITCOIN 15M QUANT RISK PARAMETERS ($ USD) ---
BTC_STOP_LOSS_PCT = 0.30           # Strict -0.30% Stop Loss
BTC_TARGET_1_PCT = 0.50            # Quick Target +0.50%
BTC_TARGET_2_PCT = 1.20            # Trend Target +1.20%
BTC_POSITION_SIZE_USD = 100.0      # Default $100 USD position size

# --- 5-LAYER INSTITUTIONAL THRESHOLDS ---
MIN_HEAVYWEIGHT_K = 4
MIN_HEAVYWEIGHT_A = 0.75
MIN_VIX_BUY_THRESHOLD = 12.0
HIGH_VIX_THRESHOLD = 18.0
PCR_BULLISH_THRESHOLD = 1.10
PCR_BEARISH_THRESHOLD = 0.90
MIN_OI_RUNWAY_POINTS = 100.0
MIN_TARGET_COVERAGE_RATIO = 2.0

# --- CHRIS CREAMER CHAMPION FILTERS ---
MIN_15M_CANDLE_VOLUME = 50000
FIB_DISCOUNT_MIN = 0.705
FIB_DISCOUNT_MAX = 0.886
LUNCH_HOUR_START = time(11, 30)
LUNCH_HOUR_END = time(13, 30)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1072750499")