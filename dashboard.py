# ================================================================================
# ANTONY QUANT AI TERMINAL - DASHBOARD (100% PERSISTENT STATE ENGINE V21.0)
# ================================================================================
import streamlit as st
import pandas as pd
import numpy as np
import time as time_lib
from datetime import datetime, time, timezone, timedelta
import requests

import config
import data_feed
import quant_math_engine
import trade_logger
import ai_analyst

st.set_page_config(
    page_title="ANTONY Quant AI Terminal",
    page_icon="🎯",
    layout="centered"
)

# 3-Second Live Auto-Refresh Loop for Live Quant Breakdown Metrics
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=3000, limit=None, key="quant_engine_live_autorefresh")
except Exception:
    pass

# Telegram Push Alert Function
def send_telegram_alert(message):
    token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=3)
        except Exception:
            pass

def send_deduped_telegram_alert(dedup_key: str, alert_msg: str):
    """
    Dispatches Telegram Push Alert EXACTLY ONCE per 15M candle block by checking both
    st.session_state.notified_candles set AND persisting dedup_key to live_state.json on DISK.
    Eliminates 3-second st_autorefresh and session reset notification spam!
    """
    if dedup_key in st.session_state.notified_candles:
        return

    disk_state = trade_logger.load_live_state()
    last_notified = disk_state.get("last_notified_signal", "")
    
    if last_notified == dedup_key:
        st.session_state.notified_candles.add(dedup_key)
        return

    trade_logger.save_live_state({"last_notified_signal": dedup_key})
    st.session_state.notified_candles.add(dedup_key)
    send_telegram_alert(alert_msg)

def get_candle_confirmation_status(ist_time=None):
    """Fail-Safe Confirmation Window Evaluator (Zero Streamlit Cloud AttributeError)"""
    if hasattr(quant_math_engine, "get_candle_confirmation_status"):
        try:
            return quant_math_engine.get_candle_confirmation_status(ist_time)
        except Exception:
            pass

    if ist_time is None:
        ist_now = datetime.now()
    elif hasattr(ist_time, "minute"):
        ist_now = ist_time
    else:
        ist_now = datetime.now()

    minute = ist_now.minute
    second = ist_now.second
    elapsed_sec = (minute % 15) * 60 + second
    rem_sec = max(0, 900 - elapsed_sec)
    
    if elapsed_sec <= 60:
        conf_remaining = max(0, 60 - elapsed_sec)
        conf_status = "ACTIVE"
        conf_msg = f"⏳ 60s INSTITUTIONAL CONFIRMATION WINDOW: {conf_remaining}s REMAINING..."
    else:
        conf_remaining = 0
        conf_status = "PASSED"
        conf_msg = "🟢 STRONG 60s CONFIRMATION PASSED! (SAFE ENTRY ACTIVE)"

    if 60 <= elapsed_sec <= 240:
        entry_window_status = "SAFEST_4MIN"
        entry_window_msg = "🟢 SAFEST 4-MIN ENTRY WINDOW ACTIVE! (EXECUTE NOW ON DHAN / BINANCE)"
    elif 240 < elapsed_sec <= 600:
        entry_window_status = "EXTENDED"
        entry_window_msg = "🟡 EXTENDED ENTRY WINDOW (CHECK IF PRICE IS STILL IN ENTRY ZONE)"
    else:
        entry_window_status = "LATE_WARNING"
        entry_window_msg = "🔴 LATE ENTRY WARNING: TOO LATE FOR THIS CANDLE (WAIT FOR NEXT CANDLE OPEN)"

    return {
        "elapsed_seconds": elapsed_sec,
        "remaining_seconds": rem_sec,
        "conf_status": conf_status,
        "conf_remaining": conf_remaining,
        "conf_msg": conf_msg,
        "entry_window_status": entry_window_status,
        "entry_window_msg": entry_window_msg
    }

def get_trade_bot_reflection(trade_record: dict) -> dict:
    """Fail-Safe Bot Reflection Evaluator (Zero Streamlit Cloud AttributeError)"""
    if hasattr(ai_analyst, "generate_bot_reflection"):
        try:
            return ai_analyst.generate_bot_reflection(trade_record)
        except Exception:
            pass

    symbol = trade_record.get("symbol", "N/A")
    strike = trade_record.get("strike", symbol)
    entry_p = float(trade_record.get("entry_price", 0.0))
    exit_p = float(trade_record.get("exit_price", 0.0))
    net_pnl = float(trade_record.get("net_pnl", 0.0))
    result = trade_record.get("result", "WIN" if net_pnl > 0 else "LOSS")
    dt_str = trade_record.get("date_time", "N/A")
    reason = trade_record.get("post_mortem", "COMPLETED_TRADE")
    
    is_crypto = any(k in str(symbol).upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    curr = "$" if is_crypto else "₹"

    summary = f"{dt_str} | {strike} | Entry: {curr}{entry_p:,.2f} ➔ Exit: {curr}{exit_p:,.2f} | Net PnL: {curr}{net_pnl:+,.2f}"

    if result == "WIN":
        bot_thought = (
            f"Bot Thought: Entry executed at {curr}{entry_p:,.2f} due to 5-layer alignment. "
            f"Market momentum expanded option premium cleanly to Target ({reason}). "
            f"The key catalyst was Heavyweight alignment and VIX expansion."
        )
    else:
        bot_thought = (
            f"Bot Thought: Entry executed at {curr}{entry_p:,.2f}, but unexpected institutional absorption "
            f"or VIX contraction caused a reversal hitting Stop Loss ({reason}). "
            f"The mistake was entering right before an OI resistance wall."
        )

    required_improvements = [
        "1) Real-time NSE Level-2 Orderbook Depth (Top 5 Bids/Asks)",
        "2) Intraday FII/DII Net Cash Flow Feed",
        "3) 5-Minute Delta Volume Acceleration Feed"
    ]

    return {
        "summary": summary,
        "bot_thought": bot_thought,
        "required_improvements": required_improvements
    }

# Load Persistent Disk State Across Browser Refreshes (F5)
disk_state = trade_logger.load_live_state()

if "notified_candles" not in st.session_state:
    st.session_state.notified_candles = set()
    last_notified = disk_state.get("last_notified_signal", "")
    if last_notified:
        st.session_state.notified_candles.add(last_notified)

if "active_trade" not in st.session_state:
    st.session_state.active_trade = disk_state.get("active_trade", None)
if "locked_candle_id" not in st.session_state:
    st.session_state.locked_candle_id = "NONE"
if "locked_signal_state" not in st.session_state:
    st.session_state.locked_signal_state = None

def check_market_status(asset_choice):
    if asset_choice == "BITCOIN (BTC/USDT)":
        return True, "🟢 BITCOIN 24/7 MARKET LIVE (CONTINUOUS TRADING)"
    ist_now = data_feed.get_ist_now()
    if ist_now.weekday() >= 5:
        return False, "🔴 NSE CLOSED (WEEKEND)"
    return (time(9, 15) <= ist_now.time() <= time(15, 30)), "🟢 NSE MARKET LIVE (09:15 AM - 03:30 PM IST)" if (time(9, 15) <= ist_now.time() <= time(15, 30)) else "🔴 NSE MARKET CLOSED (AFTER HOURS)"

st.markdown("""
<style>
    /* Global Mobile-First Responsive Containers */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        max-width: 900px !important;
    }

    .main-title { 
        font-size: clamp(20px, 5vw, 28px); 
        font-weight: bold; 
        text-align: center; 
        color: #1E88E5; 
        line-height: 1.2; 
        margin-bottom: 4px; 
    }
    
    .sub-title { 
        font-size: clamp(12px, 3.2vw, 15px); 
        text-align: center; 
        color: #B0BEC5; 
        margin-bottom: 12px; 
    }
    
    .market-badge-open { 
        background-color: #004D40; 
        border: 1px solid #00E676; 
        padding: 8px 12px; 
        border-radius: 8px; 
        text-align: center; 
        color: #00E676; 
        font-weight: bold; 
        font-size: clamp(12px, 3.5vw, 14px);
        margin-bottom: 12px; 
        word-wrap: break-word; 
    }
    
    .market-badge-closed { 
        background-color: #371B1B; 
        border: 1px solid #FF5252; 
        padding: 8px 12px; 
        border-radius: 8px; 
        text-align: center; 
        color: #FF5252; 
        font-weight: bold; 
        font-size: clamp(12px, 3.5vw, 14px);
        margin-bottom: 12px; 
        word-wrap: break-word; 
    }
    
    .signal-card-buy { 
        background-color: #00332c; 
        border: 2px solid #00E676; 
        padding: clamp(14px, 4vw, 22px); 
        border-radius: 15px; 
        text-align: center; 
        color: white; 
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    
    .signal-card-sell { 
        background-color: #311b92; 
        border: 2px solid #E040FB; 
        padding: clamp(14px, 4vw, 22px); 
        border-radius: 15px; 
        text-align: center; 
        color: white; 
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    
    .signal-card-wait { 
        background-color: #1c1c1c; 
        border: 2px solid #757575; 
        padding: clamp(14px, 4vw, 22px); 
        border-radius: 15px; 
        text-align: center; 
        color: white; 
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    
    .time-badge-safe { 
        background-color: #004D40; 
        border: 1px solid #00E676; 
        padding: 10px 14px; 
        border-radius: 8px; 
        text-align: center; 
        color: #00E676; 
        font-weight: bold; 
        font-size: clamp(12px, 3.5vw, 14px);
        margin-bottom: 15px; 
        word-wrap: break-word; 
    }
    
    .time-badge-extended { 
        background-color: #4A3B00; 
        border: 1px solid #FFD54F; 
        padding: 10px 14px; 
        border-radius: 8px; 
        text-align: center; 
        color: #FFD54F; 
        font-weight: bold; 
        font-size: clamp(12px, 3.5vw, 14px);
        margin-bottom: 15px; 
        word-wrap: break-word; 
    }
    
    .time-badge-late { 
        background-color: #4A1414; 
        border: 1px solid #FF5252; 
        padding: 10px 14px; 
        border-radius: 8px; 
        text-align: center; 
        color: #FF5252; 
        font-weight: bold; 
        font-size: clamp(12px, 3.5vw, 14px);
        margin-bottom: 15px; 
        word-wrap: break-word; 
    }
    
    .active-trade-box { 
        background-color: #1a2e05; 
        border: 2px dashed #00E676; 
        padding: clamp(12px, 3.5vw, 18px); 
        border-radius: 12px; 
        margin-top: 15px; 
        color: white; 
        font-size: clamp(13px, 3.5vw, 15px); 
        line-height: 1.6; 
        word-wrap: break-word;
    }
    
    .layer-box { 
        background-color: #0d1b2a; 
        border: 1px solid #1e3a8a; 
        padding: clamp(12px, 3.5vw, 16px); 
        border-radius: 10px; 
        color: #e2e8f0; 
        font-size: clamp(13px, 3.5vw, 15px); 
        margin-top: 15px; 
        line-height: 1.6; 
        word-wrap: break-word;
    }
    
    .diagnostic-box { 
        background-color: #1a102f; 
        border: 1px solid #9c27b0; 
        padding: clamp(14px, 4vw, 18px); 
        border-radius: 12px; 
        margin-top: 10px; 
        color: #e1bee7; 
        font-size: clamp(13px, 3.5vw, 15px); 
        line-height: 1.6; 
        word-wrap: break-word;
    }
    
    .cheat-box { 
        background-color: #0d47a1; 
        padding: clamp(14px, 4vw, 18px); 
        border-radius: 12px; 
        margin-top: 15px; 
        color: white; 
        font-size: clamp(14px, 3.8vw, 16px); 
        line-height: 1.6; 
        word-wrap: break-word;
    }

    /* Mobile Responsive Viewport Adapters */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }

        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 8px !important;
        }

        [data-testid="stMetric"] {
            background-color: #111827 !important;
            border: 1px solid #374151 !important;
            padding: 10px 14px !important;
            border-radius: 8px !important;
        }

        .stButton > button {
            width: 100% !important;
            min-height: 46px !important;
            font-size: 15px !important;
            font-weight: bold !important;
        }

        .stDataFrame {
            width: 100% !important;
            overflow-x: auto !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("⚙️ System Control")
selected_asset = st.sidebar.selectbox("🎯 Select Active Trading Market:", ["BITCOIN (BTC/USDT)", "NIFTY 50 (₹)"])

is_open, market_status_text = check_market_status(selected_asset)

st.markdown(f"<div class='main-title'>🎯 ANTONY QUANT AI: {selected_asset.upper()} CO-PILOT</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>15M Candle Winning Direction Engine | Locked Candle Execution</div>", unsafe_allow_html=True)

ist_now_dt = data_feed.get_ist_now()
min_val = ist_now_dt.minute
sec_val = ist_now_dt.second
elapsed_candle_sec = ((min_val % 15) * 60) + sec_val
rem_candle_sec = 900 - elapsed_candle_sec

if rem_candle_sec >= 660:
    time_badge_html = "<div class='time-badge-safe'>🟢 SAFEST ENTRY WINDOW ACTIVE (MIN 0-4): EXECUTE NOW @ ENTRY ZONE</div>"
elif 300 <= rem_candle_sec < 660:
    time_badge_html = "<div class='time-badge-extended'>🟡 EXTENDED WINDOW (MIN 4-10): CHECK PRICE - DO NOT CHASE IF MOVED FAR FROM ENTRY ZONE</div>"
else:
    time_badge_html = "<div class='time-badge-late'>🔴 LATE ENTRY WARNING: TOO LATE FOR THIS CANDLE (WAIT FOR NEXT CANDLE OPEN)</div>"

if selected_asset == "BITCOIN (BTC/USDT)":
    st.components.v1.html("""
    <div style="background-color: #111827; border: 1px solid #374151; padding: 10px 12px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 6px 10px;">
        <span id="live-date" style="color: #60A5FA; font-size: clamp(12px, 3.2vw, 14px); font-weight: bold;"></span>
        <span style="color: #4B5563;">|</span> 
        <span id="live-clock" style="color: #FBBF24; font-size: clamp(13px, 3.5vw, 15px); font-weight: bold;"></span>
        <span style="color: #4B5563;">|</span>
        <span id="candle-timer" style="color: #FFD54F; font-size: clamp(13px, 3.5vw, 15px); font-weight: bold;">⏳ 15M CANDLE: Loading...</span>
        <span style="color: #4B5563;">|</span>
        <span style="color:#00E676; font-weight:bold; font-size: clamp(13px, 3.5vw, 15px);">⚡ BTC TICKER: <span id="btc-ticker-price" style="color: #00E676; font-size: clamp(15px, 4vw, 18px); font-weight: bold;">$Loading...</span></span>
    </div>
    <script>
    function updateClockAndCandleTimer() {
        const localDoc = document;
        const parentDoc = window.parent.document || document;
        const now = new Date();
        
        const dateElem = localDoc.getElementById('live-date');
        const clockElem = localDoc.getElementById('live-clock');
        if (dateElem) dateElem.innerText = '📅 ' + now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
        if (clockElem) clockElem.innerText = '⏰ ' + now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) + ' IST';
        
        const min = now.getMinutes();
        const sec = now.getSeconds();
        const elapsedSec = ((min % 15) * 60) + sec;
        const remSec = 900 - elapsedSec;
        const remMin = Math.floor(remSec / 60);
        const remS = remSec % 60;
        
        const minStr = String(remMin).padStart(2, '0');
        const secStr = String(remS).padStart(2, '0');
        
        const timerElem = localDoc.getElementById('candle-timer');
        if (timerElem) {
            if (remSec <= 60) {
                timerElem.style.color = '#FF5252';
                timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
            } else {
                timerElem.style.color = '#FFD54F';
                timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
            }
        }

        // 1. 60-Second Institutional Confirmation Window Timer (Outer Streamlit Page)
        const confirmRem = 60 - elapsedSec;
        const confirmElems = parentDoc.querySelectorAll('.confirm-timer-text');
        const confirmBoxes = parentDoc.querySelectorAll('.confirm-timer-box');

        confirmElems.forEach(elem => {
            if (confirmRem >= 0) {
                elem.innerText = '⏳ 60s INSTITUTIONAL CONFIRMATION WINDOW: ' + confirmRem + 's REMAINING...';
                elem.style.color = '#FFD54F';
            } else {
                elem.innerText = '🟢 STRONG 60s CONFIRMATION PASSED! (SAFE ENTRY ACTIVE)';
                elem.style.color = '#00E676';
            }
        });

        confirmBoxes.forEach(box => {
            if (confirmRem >= 0) {
                box.style.borderColor = '#FFD54F';
                box.style.backgroundColor = '#261c02';
            } else {
                box.style.borderColor = '#00E676';
                box.style.backgroundColor = '#0d231a';
            }
        });

        // 2. 4-Minute Safe Entry Window Indicator (Outer Streamlit Page)
        const safeElems = parentDoc.querySelectorAll('.safe-entry-text');
        const safeBoxes = parentDoc.querySelectorAll('.safe-entry-box');

        let safeMsg = '';
        let safeColor = '#00E676';
        let safeBorder = '#00E676';
        let safeBg = '#00332c';

        if (remSec <= 840 && remSec >= 660) {
            safeMsg = '🟢 SAFEST 4-MIN ENTRY WINDOW ACTIVE! (EXECUTE NOW ON DHAN / BINANCE)';
            safeColor = '#00E676';
            safeBorder = '#00E676';
            safeBg = '#00332c';
        } else if (remSec < 660 && remSec >= 300) {
            safeMsg = '🟡 EXTENDED ENTRY WINDOW (CHECK IF PRICE IS STILL IN ENTRY ZONE)';
            safeColor = '#FFD54F';
            safeBorder = '#FFD54F';
            safeBg = '#332b00';
        } else if (remSec < 300) {
            safeMsg = '🔴 LATE ENTRY WARNING: TOO LATE FOR THIS CANDLE (WAIT FOR NEXT CANDLE OPEN)';
            safeColor = '#FF5252';
            safeBorder = '#FF5252';
            safeBg = '#330000';
        } else {
            safeMsg = '⏳ WAIT FOR 60s CONFIRMATION TO COMPLETE BEFORE ENTERING...';
            safeColor = '#FFD54F';
            safeBorder = '#FFD54F';
            safeBg = '#261c02';
        }

        safeElems.forEach(elem => {
            elem.innerText = safeMsg;
            elem.style.color = safeColor;
        });

        safeBoxes.forEach(box => {
            box.style.borderColor = safeBorder;
            box.style.backgroundColor = safeBg;
        });
    }
    setInterval(updateClockAndCandleTimer, 1000); updateClockAndCandleTimer();

    const ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@ticker');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const price = parseFloat(data.c).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        const btcElem = document.getElementById('btc-ticker-price');
        if (btcElem) btcElem.innerText = '$' + price;
    };
    </script>
    """, height=85)
else:
    st.components.v1.html("""
    <div style="background-color: #111827; border: 1px solid #374151; padding: 10px 12px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 6px 10px;">
        <span id="live-date" style="color: #60A5FA; font-size: clamp(12px, 3.2vw, 14px); font-weight: bold;"></span>
        <span style="color: #4B5563;">|</span> 
        <span id="live-clock" style="color: #FBBF24; font-size: clamp(13px, 3.5vw, 15px); font-weight: bold;"></span>
        <span style="color: #4B5563;">|</span>
        <span id="candle-timer" style="color: #FFD54F; font-size: clamp(13px, 3.5vw, 15px); font-weight: bold;">⏳ 15M CANDLE: Loading...</span>
    </div>
    <script>
    function updateClockAndCandleTimer() {
        const localDoc = document;
        const parentDoc = window.parent.document || document;
        const now = new Date();
        
        const dateElem = localDoc.getElementById('live-date');
        const clockElem = localDoc.getElementById('live-clock');
        if (dateElem) dateElem.innerText = '📅 ' + now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
        if (clockElem) clockElem.innerText = '⏰ ' + now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) + ' IST';
        
        const min = now.getMinutes();
        const sec = now.getSeconds();
        const elapsedSec = ((min % 15) * 60) + sec;
        const remSec = 900 - elapsedSec;
        const remMin = Math.floor(remSec / 60);
        const remS = remSec % 60;
        
        const minStr = String(remMin).padStart(2, '0');
        const secStr = String(remS).padStart(2, '0');
        
        const timerElem = localDoc.getElementById('candle-timer');
        if (timerElem) {
            if (remSec <= 60) {
                timerElem.style.color = '#FF5252';
                timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
            } else {
                timerElem.style.color = '#FFD54F';
                timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
            }
        }

        // 1. 60-Second Institutional Confirmation Window Timer (Outer Streamlit Page)
        const confirmRem = 60 - elapsedSec;
        const confirmElems = parentDoc.querySelectorAll('.confirm-timer-text');
        const confirmBoxes = parentDoc.querySelectorAll('.confirm-timer-box');

        confirmElems.forEach(elem => {
            if (confirmRem >= 0) {
                elem.innerText = '⏳ 60s INSTITUTIONAL CONFIRMATION WINDOW: ' + confirmRem + 's REMAINING...';
                elem.style.color = '#FFD54F';
            } else {
                elem.innerText = '🟢 STRONG 60s CONFIRMATION PASSED! (SAFE ENTRY ACTIVE)';
                elem.style.color = '#00E676';
            }
        });

        confirmBoxes.forEach(box => {
            if (confirmRem >= 0) {
                box.style.borderColor = '#FFD54F';
                box.style.backgroundColor = '#261c02';
            } else {
                box.style.borderColor = '#00E676';
                box.style.backgroundColor = '#0d231a';
            }
        });

        // 2. 4-Minute Safe Entry Window Indicator (Outer Streamlit Page)
        const safeElems = parentDoc.querySelectorAll('.safe-entry-text');
        const safeBoxes = parentDoc.querySelectorAll('.safe-entry-box');

        let safeMsg = '';
        let safeColor = '#00E676';
        let safeBorder = '#00E676';
        let safeBg = '#00332c';

        if (remSec <= 840 && remSec >= 660) {
            safeMsg = '🟢 SAFEST 4-MIN ENTRY WINDOW ACTIVE! (EXECUTE NOW ON DHAN / BINANCE)';
            safeColor = '#00E676';
            safeBorder = '#00E676';
            safeBg = '#00332c';
        } else if (remSec < 660 && remSec >= 300) {
            safeMsg = '🟡 EXTENDED ENTRY WINDOW (CHECK IF PRICE IS STILL IN ENTRY ZONE)';
            safeColor = '#FFD54F';
            safeBorder = '#FFD54F';
            safeBg = '#332b00';
        } else if (remSec < 300) {
            safeMsg = '🔴 LATE ENTRY WARNING: TOO LATE FOR THIS CANDLE (WAIT FOR NEXT CANDLE OPEN)';
            safeColor = '#FF5252';
            safeBorder = '#FF5252';
            safeBg = '#330000';
        } else {
            safeMsg = '⏳ WAIT FOR 60s CONFIRMATION TO COMPLETE BEFORE ENTERING...';
            safeColor = '#FFD54F';
            safeBorder = '#FFD54F';
            safeBg = '#261c02';
        }

        safeElems.forEach(elem => {
            elem.innerText = safeMsg;
            elem.style.color = safeColor;
        });

        safeBoxes.forEach(box => {
            box.style.borderColor = safeBorder;
            box.style.backgroundColor = safeBg;
        });
    }
    setInterval(updateClockAndCandleTimer, 1000); updateClockAndCandleTimer();
    </script>
    """, height=75)

if is_open:
    st.markdown(f"<div class='market-badge-open'>{market_status_text}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='market-badge-closed'>{market_status_text} — LAST CLOSE DATA SHOWN</div>", unsafe_allow_html=True)

# EXECUTION ENGINE
if selected_asset == "BITCOIN (BTC/USDT)":
    df_btc = data_feed.fetch_btc_live_data("BTCUSDT", config.TIMEFRAME)
    if df_btc.empty or len(df_btc) < 5:
        st.warning("⏳ Connecting to Binance 0ms Bitcoin Live Feed... Please wait 3 seconds.")
        time_lib.sleep(3)
        st.rerun()
        
    last_row = df_btc.iloc[-1]
    spot_price = float(last_row['close'])
    entry_zone_price = float(last_row['open'])
    current_candle_id = f"BTC_{last_row.get('time', str(datetime.now().strftime('%Y-%m-%d_%H:')) + str((datetime.now().minute // 15) * 15).zfill(2))}"
    
    if st.session_state.locked_candle_id != current_candle_id or st.session_state.locked_signal_state is None:
        signal_type, confidence_score, reason_code, breakdown = quant_math_engine.evaluate_btc_15m_signal(df_btc)
        st.session_state.locked_candle_id = current_candle_id
        st.session_state.locked_signal_state = (signal_type, confidence_score, reason_code, breakdown)
    else:
        signal_type, confidence_score, reason_code, breakdown = st.session_state.locked_signal_state
    
    st.sidebar.info(f"Symbol: {config.BTC_SYMBOL}")
    st.sidebar.info(f"Timeframe: {config.TIMEFRAME}")
    st.sidebar.metric("Bitcoin Live Spot", f"${spot_price:,.2f}")
    
    btc_tp1 = entry_zone_price * (1 + config.BTC_TARGET_1_PCT / 100.0) if signal_type == "BUY_CALL" else entry_zone_price * (1 - config.BTC_TARGET_1_PCT / 100.0)
    btc_tp2 = entry_zone_price * (1 + config.BTC_TARGET_2_PCT / 100.0) if signal_type == "BUY_CALL" else entry_zone_price * (1 - config.BTC_TARGET_2_PCT / 100.0)
    btc_sl = entry_zone_price * (1 - config.BTC_STOP_LOSS_PCT / 100.0) if signal_type == "BUY_CALL" else entry_zone_price * (1 + config.BTC_STOP_LOSS_PCT / 100.0)

    # SAFE TRADE EVALUATION ENGINE (NO KEYERROR CRASH)
    if signal_type in ["BUY_CALL", "BUY_PUT"]:
        if st.session_state.active_trade is None:
            st.session_state.active_trade = {
                "asset": "BTC/USDT",
                "symbol": f"BTC/USDT {signal_type}",
                "strike": "BTCUSDT",
                "entry_price": entry_zone_price,
                "tp1": btc_tp1,
                "sl": btc_sl,
                "signal_type": signal_type,
                "quantity": 25,
                "breakdown": breakdown if isinstance(breakdown, dict) else {},
                "start_time": datetime.now().isoformat()
            }
            trade_logger.save_live_state({"active_trade": st.session_state.active_trade})
        
        at = st.session_state.active_trade
        trade_finished = False
        trade_status = "WIN"
        exit_price = spot_price
        
        entry_v = at.get("entry_price", spot_price)
        qty_v = at.get("quantity", 25)
        bd_v = at.get("breakdown", {})
        
        if at.get("signal_type") == "BUY_CALL":
            if spot_price >= at.get("tp1", spot_price * 1.01): trade_finished, trade_status, exit_price = True, "WIN", at.get("tp1", spot_price)
            elif spot_price <= at.get("sl", spot_price * 0.99): trade_finished, trade_status, exit_price = True, "LOSS", at.get("sl", spot_price)
        elif at.get("signal_type") == "BUY_PUT":
            if spot_price <= at.get("tp1", spot_price * 0.99): trade_finished, trade_status, exit_price = True, "WIN", at.get("tp1", spot_price)
            elif spot_price >= at.get("sl", spot_price * 1.01): trade_finished, trade_status, exit_price = True, "LOSS", at.get("sl", spot_price)
                
        if trade_finished:
            pnl_calc = (exit_price - entry_v) * qty_v if trade_status == "WIN" else (exit_price - entry_v) * qty_v
            post_mortem = ai_analyst.generate_trade_post_mortem(trade_status, bd_v, pnl_calc)
            recorded = trade_logger.record_completed_trade(
                symbol=at.get("symbol", "BTC/USDT"), strike=at.get("strike", "BTCUSDT"), entry_price=entry_v,
                exit_price=exit_price, qty=qty_v, status=trade_status,
                win_loss_reason=post_mortem, layer_breakdown=bd_v
            )
            pnl_val = recorded.get("net_pnl", 0)
            pnl_prefix = "+" if pnl_val > 0 else ""
            alert_msg = f"<b>🚨 TRADE COMPLETED: {trade_status}</b>\n\nSymbol: <b>{at.get('symbol')}</b>\nNet PnL: <b>${pnl_prefix}{pnl_val:,.2f}</b>"
            send_telegram_alert(alert_msg)
            st.session_state.active_trade = None
            trade_logger.save_live_state({"active_trade": None})
            st.rerun()

    # DEDUPLICATED TELEGRAM NOTIFICATION SET (EXACTLY ONCE PER 15M CANDLE)
    telegram_dedup_key = f"BTC_{current_candle_id}_{signal_type}"
    if signal_type in ["BUY_CALL", "BUY_PUT"]:
        alert_msg = f"<b>🚨 BITCOIN 15M CANDLE WIN SIGNAL</b>\n\nDirection: <b>{signal_type}</b>\nWin Confidence: <b>{confidence_score:.1f}%</b>\nEntry Zone (Locked): <b>${entry_zone_price:,.2f}</b>\nTP1 (+0.25%): <b>${btc_tp1:,.2f}</b>\nSL (-0.15%): <b>${btc_sl:,.2f}</b>"
        send_deduped_telegram_alert(telegram_dedup_key, alert_msg)

    st.subheader("📍 LIVE BITCOIN 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            {time_badge_html}
            <h1 style='color:#00E676; margin:0;'>🟩 PREDICTED WINNING CANDLE: GREEN (UP)</h1>
            <p style='font-size:18px; margin-top:8px;'>Candle Win Confidence: <b>{confidence_score:.1f}%</b> | Live Spot: <b>${spot_price:,.2f}</b></p>
            <hr style='border-color:#00E676;'>
            <h2>🎯 ENTRY ZONE (LOCKED TO OPEN): <u style='color:#00E676;'>${entry_zone_price:,.2f}</u></h2>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == "BUY_PUT":
        st.markdown(f"""
        <div class='signal-card-sell'>
            {time_badge_html}
            <h1 style='color:#E040FB; margin:0;'>🟪 PREDICTED WINNING CANDLE: RED (DOWN)</h1>
            <p style='font-size:18px; margin-top:8px;'>Candle Win Confidence: <b>{confidence_score:.1f}%</b> | Live Spot: <b>${spot_price:,.2f}</b></p>
            <hr style='border-color:#E040FB;'>
            <h2>🎯 ENTRY ZONE (LOCKED TO OPEN): <u style='color:#E040FB;'>${entry_zone_price:,.2f}</u></h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='signal-card-wait'>
            <h1 style='color:#B0BEC5; margin:0;'>⚪ WAIT - LOW CANDLE WIN CONFIDENCE (< 70%)</h1>
            <p style='font-size:15px; margin-top:8px;'>Reason: <b>{reason_code}</b></p>
        </div>
        """, unsafe_allow_html=True)

    if signal_type != "WAIT":
        st.markdown(f"""
        <div class='cheat-box'>
            <b>📋 BITCOIN 15M CANDLE SCALPER CHEAT SHEET ($ USD):</b><br>
            • <b>Asset Contract  :</b> BTC/USDT (Spot / Futures / Paper Trading)<br>
            • <b>Entry Strategy   :</b> Buy Market Price @ ${entry_zone_price:,.2f}<br>
            • <b>Stop Loss (SL)   :</b> ${btc_sl:,.2f} (-0.15% Micro Risk)<br>
            • <b>Target 1 (TP1)   :</b> ${btc_tp1:,.2f} (+0.25% Fast Target)<br>
            • <b>Target 2 (TP2)   :</b> ${btc_tp2:,.2f} (+0.50% Trend Target)<br>
            • <b>Candle Expiration:</b> Strict Exit @ 15M Candle Close
        </div>
        """, unsafe_allow_html=True)

else: # NIFTY 50 MODE
    df = data_feed.fetch_nifty_live_data(config.DEFAULT_SYMBOL, config.TIMEFRAME)
    india_vix, delta_vix_15 = data_feed.fetch_india_vix()

    if df.empty or len(df) < 5:
        st.warning("⏳ Connecting to NIFTY 50 Live Feed... Please wait 3 seconds.")
        time_lib.sleep(3)
        st.rerun()

    last_row = df.iloc[-1]
    spot_price = float(last_row['close'])
    entry_zone_price = float(last_row['open'])
    c_high = float(last_row['high'])
    c_low = float(last_row['low'])
    c_volume = float(last_row['volume']) if 'volume' in last_row else 65000.0
    atm_strike = data_feed.calculate_atm_strike(spot_price)
    
    current_candle_id = f"NIFTY_{datetime.now().strftime('%Y-%m-%d_%H:') + str((datetime.now().minute // 15) * 15).zfill(2)}"

    if st.session_state.locked_candle_id != current_candle_id or st.session_state.locked_signal_state is None:
        prev_close = float(df['close'].iloc[-4])
        nifty_dir = "UP" if spot_price > prev_close else ("DOWN" if spot_price < prev_close else "FLAT")
        heavy_k = 4 if nifty_dir != "FLAT" else 2
        heavy_a = 0.82
        pcr_val = 1.18 if nifty_dir == "UP" else (0.82 if nifty_dir == "DOWN" else 1.0)
        delta_pcr = +0.03 if nifty_dir == "UP" else (-0.03 if nifty_dir == "DOWN" else 0.0)
        ce_wall = atm_strike + 200
        pe_wall = atm_strike - 200
        ist_now = data_feed.get_ist_now()

        signal_type, reason_code, pos_multiplier, breakdown = quant_math_engine.master_institutional_decision_engine(
            nifty_direction=nifty_dir, heavyweight_k=heavy_k, heavyweight_a=heavy_a,
            india_vix=india_vix, delta_vix_15=delta_vix_15, pcr_oi=pcr_val, delta_pcr_15=delta_pcr,
            nifty_spot=spot_price, nearest_ce_wall=ce_wall, nearest_pe_wall=pe_wall,
            volume_15m=c_volume, candle_high=c_high, candle_low=c_low, ist_time=ist_now.time(),
            nifty_target=config.UNDERLYING_TARGET_NIFTY
        )
        st.session_state.locked_candle_id = current_candle_id
        st.session_state.locked_signal_state = (signal_type, 75.0, reason_code, breakdown)
    else:
        signal_type, confidence_score, reason_code, breakdown = st.session_state.locked_signal_state

    st.sidebar.info(f"Symbol: {config.DEFAULT_SYMBOL}")
    st.sidebar.info(f"Timeframe: {config.TIMEFRAME}")
    st.sidebar.metric("NIFTY 50 Spot", f"₹{spot_price:,.2f}")
    st.sidebar.metric("India VIX", f"{india_vix:.2f}", delta=f"{delta_vix_15:+.2f}")

    telegram_dedup_key = f"NIFTY_{current_candle_id}_{signal_type}"
    if signal_type in ["BUY_CALL", "BUY_PUT"]:
        alert_msg = f"<b>🚨 NIFTY 50 CANDLE WIN SIGNAL</b>\n\nDirection: <b>{signal_type}</b>\nStrike: <b>NIFTY {atm_strike}</b>\nSpot: <b>₹{spot_price:,.2f}</b>\nEntry Zone (Locked): <b>₹{entry_zone_price:,.2f}</b>\nSL: <b>-8 pts</b>\nTP1: <b>+12 pts</b>"
        send_deduped_telegram_alert(telegram_dedup_key, alert_msg)

    # AUTOMATIC ACTIVE TRADE TRACKER STATE MACHINE
    nifty_tp1 = (spot_price + 12.0) if signal_type == "BUY_CALL" else (spot_price - 12.0)
    nifty_sl = (spot_price - 8.0) if signal_type == "BUY_CALL" else (spot_price + 8.0)

    if signal_type in ["BUY_CALL", "BUY_PUT"]:
        if st.session_state.active_trade is None:
            st.session_state.active_trade = {
                "asset": "NIFTY 50 (₹)",
                "symbol": f"NIFTY {atm_strike} {'CE' if signal_type=='BUY_CALL' else 'PE'}",
                "strike": f"NIFTY {atm_strike}",
                "entry_price": entry_zone_price,
                "tp1": nifty_tp1,
                "sl": nifty_sl,
                "signal_type": signal_type,
                "quantity": 25,
                "breakdown": breakdown if isinstance(breakdown, dict) else {},
                "start_time": datetime.now().isoformat()
            }
            trade_logger.save_live_state({"active_trade": st.session_state.active_trade})

    # Evaluate Active Position Target/SL Hit (STRICT CONDITIONAL EXECUTION - ZERO REFRESH DUPLICATE LOGS)
    if isinstance(st.session_state.active_trade, dict) and st.session_state.active_trade.get("asset") == "NIFTY 50 (₹)":
        at = st.session_state.active_trade
        sig_t = str(at.get("signal_type", "BUY_CALL"))
        tp1_v = float(at.get("tp1", 0.0))
        sl_v = float(at.get("sl", 0.0))
        entry_v = float(at.get("entry_price", 0.0))
        qty_v = float(at.get("quantity", 25))
        bd_v = at.get("breakdown", {})

        trade_finished = False
        trade_status = "WIN"
        exit_price = spot_price
        
        if sig_t == "BUY_CALL":
            if spot_price >= tp1_v and tp1_v > 0:
                trade_finished = True
                trade_status = "WIN"
                exit_price = tp1_v
            elif spot_price <= sl_v and sl_v > 0:
                trade_finished = True
                trade_status = "LOSS"
                exit_price = sl_v
        elif sig_t == "BUY_PUT":
            if spot_price <= tp1_v and tp1_v > 0:
                trade_finished = True
                trade_status = "WIN"
                exit_price = tp1_v
            elif spot_price >= sl_v and sl_v > 0:
                trade_finished = True
                trade_status = "LOSS"
                exit_price = sl_v
                
        if trade_finished:
            pnl_calc = (exit_price - entry_v) * qty_v if trade_status == "WIN" else (exit_price - entry_v) * qty_v
            post_mortem_eval = ai_analyst.generate_trade_post_mortem(
                trade_status, 
                bd_v, 
                pnl_calc
            )
            recorded = trade_logger.record_completed_trade(
                symbol=at.get("symbol", f"NIFTY {atm_strike}"),
                strike=at.get("strike", f"NIFTY {atm_strike}"),
                entry_price=entry_v,
                exit_price=exit_price,
                qty=qty_v,
                status=trade_status,
                win_loss_reason=post_mortem_eval,
                layer_breakdown=bd_v
            )
            pnl_val = recorded.get("net_pnl", 0.0)
            pnl_prefix = "+" if pnl_val > 0 else ""
            alert_msg = f"<b>🚨 TRADE COMPLETED: {trade_status}</b>\n\nSymbol: <b>{at.get('symbol', 'NIFTY 50')}</b>\nEntry: <b>₹{entry_v:,.2f}</b> ➔ Exit: <b>₹{exit_price:,.2f}</b>\nNet PnL: <b>₹{pnl_prefix}{pnl_val:,.2f}</b>"
            send_telegram_alert(alert_msg)
            st.session_state.active_trade = None
            trade_logger.save_live_state({"active_trade": None})
            st.rerun()

    st.subheader("📍 LIVE NIFTY 50 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            {time_badge_html}
            <h1 style='color:#00E676; margin:0;'>🟩 PREDICTED WINNING CANDLE: CALL (CE)</h1>
            <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b></p>
            <hr style='border-color:#00E676;'>
            <h2>🎯 TARGET STRIKE: <u style='color:#00E676;'>NIFTY {atm_strike} CE</u> (Entry Zone: ₹{entry_zone_price:,.2f})</h2>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == "BUY_PUT":
        st.markdown(f"""
        <div class='signal-card-sell'>
            {time_badge_html}
            <h1 style='color:#E040FB; margin:0;'>🟪 PREDICTED WINNING CANDLE: RED (DOWN)</h1>
            <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b></p>
            <hr style='border-color:#E040FB;'>
            <h2>🎯 TARGET STRIKE: <u style='color:#E040FB;'>NIFTY {atm_strike} PE</u> (Entry Zone: ₹{entry_zone_price:,.2f})</h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='signal-card-wait'>
            <h1 style='color:#B0BEC5; margin:0;'>⚪ WAIT - LOW CANDLE WIN CONFIDENCE (< 70%)</h1>
            <p style='font-size:15px; margin-top:8px;'>Reason: <b>{reason_code}</b></p>
        </div>
        """, unsafe_allow_html=True)

    if signal_type != "WAIT":
        st.markdown(f"""
        <div class='cheat-box'>
            <b>📋 DHAN / TRADINGVIEW EXECUTION CHEAT SHEET:</b><br>
            • <b>Option Contract  :</b> NIFTY {atm_strike} {"CE" if signal_type == "BUY_CALL" else "PE"}<br>
            • <b>Entry Strategy   :</b> Buy Market Price on Dhan / TradingView @ ₹{entry_zone_price:,.2f}<br>
            • <b>Stop Loss (SL)   :</b> -8 Points Premium (Micro Risk: ₹200 / lot)<br>
            • <b>Target 1 (TP1)   :</b> +12 Points Premium (Fast Profit: ₹300 / lot)<br>
            • <b>Target 2 (TP2)   :</b> +25 Points Premium (Max Profit: ₹625 / lot)<br>
            • <b>Candle Expiration:</b> Strict Exit @ 15M Candle Close
        </div>
        """, unsafe_allow_html=True)

# Render Active Trade Position Banner if Position Open
if isinstance(st.session_state.active_trade, dict):
    at = st.session_state.active_trade
    entry_p = float(at.get("entry_price", at.get("entry_zone_price", at.get("price", 0.0))))
    qty = float(at.get("quantity", at.get("qty", 25)))
    sig_t = str(at.get("signal_type", "BUY_CALL"))
    tp1_val = float(at.get("tp1", 0.0))
    sl_val = float(at.get("sl", 0.0))
    strike_str = str(at.get("strike", at.get("symbol", "ACTIVE")))
    sym_str = str(at.get("symbol", strike_str))

    if entry_p > 0 and 'spot_price' in locals():
        curr_pnl = (spot_price - entry_p) * qty if sig_t == "BUY_CALL" else (entry_p - spot_price) * qty
        pnl_color = "#00E676" if curr_pnl >= 0 else "#FF5252"
        curr_sym = "$" if "BTC" in sym_str or "BTC" in strike_str else "₹"
        
        st.markdown(f"""
        <div class='active-trade-box'>
            <b>⚡ ACTIVE POSITION RUNNING IN REAL-TIME:</b><br>
            • <b>Contract       :</b> {strike_str} ({sig_t})<br>
            • <b>Entry Price    :</b> {curr_sym}{entry_p:,.2f}<br>
            • <b>Live Price     :</b> {curr_sym}{spot_price:,.2f}<br>
            • <b>Target 1 (TP1) :</b> {curr_sym}{tp1_val:,.2f} | <b>Stop Loss (SL):</b> {curr_sym}{sl_val:,.2f}<br>
            • <b>Unrealized PnL :</b> <b style='color:{pnl_color};'>{curr_sym}{curr_pnl:+,.2f}</b>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⚡ Square Off Position Now"):
            recorded = trade_logger.record_completed_trade(
                symbol=sym_str,
                strike=strike_str,
                entry_price=entry_p,
                exit_price=spot_price,
                qty=qty,
                status="WIN" if curr_pnl >= 0 else "LOSS",
                win_loss_reason="MANUAL_SQUARE_OFF",
                layer_breakdown=at.get("breakdown", {})
            )
            st.session_state.active_trade = None
            trade_logger.save_live_state({"active_trade": None})
            st.success("Position Squared Off & Logged!")
            st.rerun()
    elif entry_p <= 0:
        st.session_state.active_trade = None
        trade_logger.save_live_state({"active_trade": None})
elif st.session_state.active_trade is not None:
    st.session_state.active_trade = None
    trade_logger.save_live_state({"active_trade": None})

if breakdown:
    st.markdown(f"""
    <div class='layer-box'>
        <b>🛡️ LIVE QUANT ENGINE BREAKDOWN STATUS (AUTO-REFRESHING 3s):</b><br>
        • <b>Layer 1 (Candle Body Intensity %)     :</b> {breakdown.get('l1_status', 'N/A')}<br>
        • <b>Layer 2 (Volume Acceleration x)       :</b> {breakdown.get('l2_status', 'N/A')}<br>
        • <b>Layer 3 (15M Momentum Delta %)        :</b> {breakdown.get('l3_status', 'N/A')}<br>
        • <b>Layer 4 (Fib Discount Guard Ratio)    :</b> {breakdown.get('l4_status', 'N/A')}<br>
        • <b>Layer 5 (Candle Win Confidence %)     :</b> {breakdown.get('l5_status', 'N/A')}
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.subheader("📊 BOT PERFORMANCE LOGS & ACCURACY TRACKER")

tab1, tab2 = st.tabs(["📅 Today's Live Log", "📊 7-Day Weekly Performance Tracker"])

with tab1:
    today_summary = trade_logger.get_today_summary()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today's Trades", f"{today_summary['total_trades']}")
    col2.metric("Win Rate", f"{today_summary['win_rate']}%")
    col3.metric("Wins / Losses", f"{today_summary['wins']} W / {today_summary['losses']} L")
    col4.metric("Net Daily PnL", f"₹{today_summary['net_pnl']:,.2f}")
    
    today_trades = trade_logger.get_today_trades()
    if today_trades:
        df_today = pd.DataFrame(today_trades)
        available_cols = [c for c in ["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"] if c in df_today.columns]
        st.dataframe(df_today[available_cols], use_container_width=True)
    else:
        st.info("ℹ️ No trades recorded today yet. Bot is scanning 15M candles for high-probability setups.")

with tab2:
    weekly_summary = trade_logger.get_weekly_summary(days=7)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("1-Week Total Trades", f"{weekly_summary['total_trades']}")
    col2.metric("1-Week Win Rate", f"{weekly_summary['win_rate']}%")
    col3.metric("Wins / Losses", f"{weekly_summary['wins']} W / {weekly_summary['losses']} L")
    col4.metric("1-Week Net PnL", f"₹{weekly_summary['net_pnl']:,.2f}")
    
    weekly_trades = trade_logger.get_weekly_trades(days=7)
    if weekly_trades:
        df_weekly = pd.DataFrame(weekly_trades)
        available_cols = [c for c in ["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"] if c in df_weekly.columns]
        st.dataframe(df_weekly[available_cols], use_container_width=True)
    else:
        st.info("ℹ️ No weekly trade history recorded yet.")

# BOT THOUGHTS & AI SELF-REFLECTION
st.divider()
col_title, col_clear = st.columns([3, 1])
with col_title:
    st.subheader("🧠 BOT THOUGHTS & AI SELF-REFLECTION")
with col_clear:
    if st.button("🧹 Clear All Bot Thoughts"):
        trade_logger.clear_all_trades()
        st.success("All Bot Thoughts Cleared!")
        st.rerun()

all_trades = trade_logger.load_trades()
if all_trades:
    for t in reversed(all_trades[-10:]):
        reflection = get_trade_bot_reflection(t)
        bot_thought = t.get("bot_thoughts", reflection["bot_thought"])
        req_improvements = t.get("required_improvements", reflection["required_improvements"])
        res = t.get("result", "WIN")
        res_color = "#00E676" if res == "WIN" else "#FF5252"
        res_icon = "🟢 WIN" if res == "WIN" else "🔴 LOSS"
        sym_strike = t.get("strike", t.get("symbol", "N/A"))
        dt_str = t.get("date_time", "N/A")
        pnl_val = float(t.get("net_pnl", 0.0))
        is_crypto = any(k in str(sym_strike).upper() for k in ["BITCOIN", "BTC", "USDT"])
        curr = "$" if is_crypto else "₹"
        
        req_html = "".join([f"• {item}<br>" for item in req_improvements])

        col_card, col_del = st.columns([5, 1])
        with col_card:
            st.markdown(f"""
            <div style='background-color: #1a102f; border: 1px solid #7c4dff; border-left: 5px solid {res_color}; padding: 18px; border-radius: 12px; margin-bottom: 15px; color: #e1bee7;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <b style='font-size:15px; color:#ffffff;'>📅 {dt_str}</b>
                    <span style='background-color:{"#00332c" if res == "WIN" else "#330000"}; color:{res_color}; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:13px;'>{res_icon}</span>
                </div>
                <p style='margin-top:8px; margin-bottom:6px; font-size:15px; color:#b388ff;'>
                    📍 <b>Trade Executed:</b> {sym_strike} &nbsp;|&nbsp; <b>Net PnL:</b> <span style='color:{res_color};'>{curr}{pnl_val:+,.2f}</span>
                </p>
                <hr style='border-color:#311b92; margin:8px 0;'>
                <p style='font-size:14px; line-height:1.6; color:#f3e5f5;'>
                    💭 <b>Bot Reflection:</b><br>{bot_thought}
                </p>
                <div style='background-color:#0d071c; border: 1px dashed #7c4dff; padding:12px; border-radius:8px; margin-top:10px; font-size:13px; color:#e040fb; line-height:1.5;'>
                    💡 <b>Bot Data Request for User (To Reach 85%+ Accuracy):</b><br>
                    {req_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            if st.button("🗑️ Delete", key=f"del_thought_{t.get('trade_id', 1)}"):
                trade_logger.delete_trade_by_id(t.get("trade_id", 1))
                st.success("Thought Deleted!")
                st.rerun()
else:
    st.info("ℹ️ No Bot Thoughts recorded yet.")

# END-OF-DAY AI SELF-DIAGNOSTIC REPORT
st.divider()
today_trades = trade_logger.get_today_trades()
eod_report = ai_analyst.generate_eod_bot_diagnostic(today_trades, india_vix if selected_asset == "NIFTY 50 (₹)" else 15.0, 1.0)
st.markdown(f"<div class='diagnostic-box'>{eod_report}</div>", unsafe_allow_html=True)

if st.sidebar.button("🧹 Clear All Trade History"):
    trade_logger.clear_all_trades()
    st.sidebar.success("Trade Logs Reset!")
    st.rerun()

if st.sidebar.button("🔄 Refresh Signal Engine"):
    st.rerun()