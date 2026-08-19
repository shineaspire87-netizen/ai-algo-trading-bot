# ================================================================================
# ANTONY QUANT AI TERMINAL - CONFIGURATION ENGINE (5-LAYER INSTITUTIONAL EDITION)
# ================================================================================
import os

# --- CORE TRADING MODE ---
PRIMARY_MODE = "NIFTY50_OPTIONS"
DEFAULT_SYMBOL = "^NSEI"           # Yahoo Finance Ticker for NIFTY 50
VIX_SYMBOL = "^INDIAVIX"           # India VIX Ticker
TIMEFRAME = "15m"                  # 15-Minute Candle Timeframe

# --- NIFTY OPTIONS RISK PARAMETERS (RUPEES ₹) ---
NIFTY_LOT_SIZE = 25               # Shares per 1 NIFTY Lot
DEFAULT_LOTS = 1                   # Initial Trading Size (1 Lot)

STOP_LOSS_POINTS = 15.0            # Strict Risk per Lot (-15 pts = ₹375)
TARGET_1_POINTS = 20.0             # Quick Target (+20 pts = ₹500)
TARGET_2_POINTS = 45.0             # Trend Target (+45 pts = ₹1,125)
UNDERLYING_TARGET_NIFTY = 30.0     # Default NIFTY spot move target in points

# --- 5-LAYER INSTITUTIONAL THRESHOLDS ---
MIN_HEAVYWEIGHT_K = 4              # At least 4 out of 5 Heavyweights aligned
MIN_HEAVYWEIGHT_A = 0.75           # Alignment score threshold
MIN_VIX_BUY_THRESHOLD = 12.0       # Disable option buying if VIX < 12
HIGH_VIX_THRESHOLD = 18.0          # Reduce size to 50% if VIX > 18
PCR_BULLISH_THRESHOLD = 1.10       # PCR >= 1.10 + rising PCR for CALL
PCR_BEARISH_THRESHOLD = 0.90       # PCR <= 0.90 + falling PCR for PUT
MIN_OI_RUNWAY_POINTS = 100.0       # Minimum 100 points runway to nearest OI wall
MIN_TARGET_COVERAGE_RATIO = 2.0    # Runway / Target >= 2.0

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1072750499")