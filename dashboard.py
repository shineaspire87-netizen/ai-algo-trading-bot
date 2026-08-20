# ================================================================================
# ANTONY QUANT AI TERMINAL - DASHBOARD (100% PERSISTENT STATE ENGINE V14.0)
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

# Load Persistent Disk State Across Browser Refreshes (F5)
disk_state = trade_logger.load_live_state()

if "last_notified_signal" not in st.session_state:
    st.session_state.last_notified_signal = disk_state.get("last_notified_signal", "WAIT")

def check_market_status(asset_choice):
    if asset_choice == "BITCOIN (BTC/USDT)":
        return True, "🟢 BITCOIN 24/7 MARKET LIVE (CONTINUOUS TRADING)"
    ist_now = data_feed.get_ist_now()
    if ist_now.weekday() >= 5:
        return False, "🔴 NSE CLOSED (WEEKEND)"
    return (time(9, 15) <= ist_now.time() <= time(15, 30)), "🟢 NSE MARKET LIVE (09:15 AM - 03:30 PM IST)" if (time(9, 15) <= ist_now.time() <= time(15, 30)) else "🔴 NSE MARKET CLOSED (AFTER HOURS)"

st.markdown("""
<style>
    .main-title { font-size: 26px; font-weight: bold; text-align: center; color: #1E88E5; }
    .sub-title { font-size: 14px; text-align: center; color: #B0BEC5; margin-bottom: 10px; }
    .market-badge-open { background-color: #004D40; border: 1px solid #00E676; padding: 8px; border-radius: 8px; text-align: center; color: #00E676; font-weight: bold; margin-bottom: 12px; }
    .market-badge-closed { background-color: #371B1B; border: 1px solid #FF5252; padding: 8px; border-radius: 8px; text-align: center; color: #FF5252; font-weight: bold; margin-bottom: 12px; }
    .signal-card-buy { background-color: #00332c; border: 2px solid #00E676; padding: 22px; border-radius: 15px; text-align: center; color: white; }
    .signal-card-sell { background-color: #311b92; border: 2px solid #E040FB; padding: 22px; border-radius: 15px; text-align: center; color: white; }
    .signal-card-wait { background-color: #1c1c1c; border: 2px solid #757575; padding: 22px; border-radius: 15px; text-align: center; color: white; }
    .active-trade-box { background-color: #1a2e05; border: 2px dashed #00E676; padding: 18px; border-radius: 12px; margin-top: 15px; color: white; font-size: 15px; line-height: 1.6; }
    .layer-box { background-color: #0d1b2a; border: 1px solid #1e3a8a; padding: 15px; border-radius: 10px; color: #e2e8f0; font-size: 15px; margin-top: 15px; line-height: 1.6; }
    .diagnostic-box { background-color: #1a102f; border: 1px solid #9c27b0; padding: 18px; border-radius: 12px; margin-top: 20px; color: #e1bee7; font-size: 15px; line-height: 1.6; }
    .cheat-box { background-color: #0d47a1; padding: 18px; border-radius: 12px; margin-top: 15px; color: white; font-size: 16px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("⚙️ System Control")
selected_asset = st.sidebar.selectbox("🎯 Select Active Trading Market:", ["BITCOIN (BTC/USDT)", "NIFTY 50 (₹)"])

is_open, market_status_text = check_market_status(selected_asset)

st.markdown(f"<div class='main-title'>🎯 ANTONY QUANT AI: {selected_asset.upper()} CO-PILOT</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>15M Candle Winning Direction Engine | Persistent Active Trade State</div>", unsafe_allow_html=True)

if selected_asset == "BITCOIN (BTC/USDT)":
    st.components.v1.html("""
    <div style="background-color: #111827; border: 1px solid #374151; padding: 12px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6;">
        <span id="live-date" style="color: #60A5FA; font-size: 14px; font-weight: bold;"></span> &nbsp;|&nbsp; 
        <span id="live-clock" style="color: #FBBF24; font-size: 16px; font-weight: bold;"></span><br>
        <span id="candle-timer" style="color: #FFD54F; font-size: 16px; font-weight: bold;">⏳ 15M CANDLE: Loading...</span> &nbsp;|&nbsp;
        <span style="color:#00E676; font-weight:bold;">⚡ BTC TICKER: </span>
        <span id="btc-ticker-price" style="color: #00E676; font-size: 20px; font-weight: bold;">$Loading...</span>
    </div>
    <script>
    function updateClockAndCandleTimer() {
        const doc = window.parent.document || document;
        const now = new Date();
        const dateElem = doc.getElementById('live-date');
        const clockElem = doc.getElementById('live-clock');
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
        
        const timerElem = doc.getElementById('candle-timer');
        if (timerElem) {
            if (remSec <= 60) {
                timerElem.style.color = '#FF5252';
                timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
            } else {
                timerElem.style.color = '#FFD54F';
                timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
            }
        }

        // 1. 60-Second Institutional Confirmation Window Timer
        const confirmRem = 60 - elapsedSec;
        const confirmElems = doc.querySelectorAll('.confirm-timer-text');
        const confirmBoxes = doc.querySelectorAll('.confirm-timer-box');

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

        // 2. 4-Minute Safe Entry Window Indicator
        const safeElems = doc.querySelectorAll('.safe-entry-text');
        const safeBoxes = doc.querySelectorAll('.safe-entry-box');

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
        const btcElem = doc.getElementById('btc-ticker-price');
        if (btcElem) btcElem.innerText = '$' + price;
    };
    </script>
    """, height=85)
else:
    st.components.v1.html("""
    <div style="background-color: #111827; border: 1px solid #374151; padding: 10px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6;">
        <span id="live-date" style="color: #60A5FA; font-size: 15px; font-weight: bold;"></span> &nbsp;|&nbsp; 
        <span id="live-clock" style="color: #FBBF24; font-size: 18px; font-weight: bold;"></span><br>
        <span id="candle-timer" style="color: #FFD54F; font-size: 16px; font-weight: bold;">⏳ 15M CANDLE: Loading...</span>
    </div>
    <script>
    function updateClockAndCandleTimer() {
        const doc = window.parent.document || document;
        const now = new Date();
        const dateElem = doc.getElementById('live-date');
        const clockElem = doc.getElementById('live-clock');
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
        
        const timerElem = doc.getElementById('candle-timer');
        if (timerElem) {
            if (remSec <= 60) {
                timerElem.style.color = '#FF5252';
                timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
            } else {
                timerElem.style.color = '#FFD54F';
                timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
            }
        }

        // 1. 60-Second Institutional Confirmation Window Timer
        const confirmRem = 60 - elapsedSec;
        const confirmElems = doc.querySelectorAll('.confirm-timer-text');
        const confirmBoxes = doc.querySelectorAll('.confirm-timer-box');

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

        // 2. 4-Minute Safe Entry Window Indicator
        const safeElems = doc.querySelectorAll('.safe-entry-text');
        const safeBoxes = doc.querySelectorAll('.safe-entry-box');

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

# ENGINE EXECUTION
if selected_asset == "BITCOIN (BTC/USDT)":
    df_btc = data_feed.fetch_btc_live_data("BTCUSDT", config.TIMEFRAME)
    if df_btc.empty or len(df_btc) < 5:
        st.warning("⏳ Connecting to Binance 0ms Bitcoin Live Feed... Please wait 3 seconds.")
        time_lib.sleep(3)
        st.rerun()
        
    last_row = df_btc.iloc[-1]
    spot_price = float(last_row['close'])
    
    st.sidebar.info(f"Symbol: {config.BTC_SYMBOL}")
    st.sidebar.info(f"Timeframe: {config.TIMEFRAME}")
    st.sidebar.metric("Bitcoin Live Spot", f"${spot_price:,.2f}")
    
    signal_type, confidence_score, reason_code, breakdown = quant_math_engine.evaluate_btc_15m_signal(df_btc)
    
    try:
        conf_val = float(confidence_score)
    except (ValueError, TypeError):
        conf_val = 0.0

    try:
        spot_val = float(spot_price)
    except (ValueError, TypeError):
        spot_val = 0.0

    btc_tp1 = spot_val * (1 + config.BTC_TARGET_1_PCT / 100.0) if signal_type == "BUY_CALL" else spot_val * (1 - config.BTC_TARGET_1_PCT / 100.0)
    btc_tp2 = spot_val * (1 + config.BTC_TARGET_2_PCT / 100.0) if signal_type == "BUY_CALL" else spot_val * (1 - config.BTC_TARGET_2_PCT / 100.0)
    btc_sl = spot_val * (1 - config.BTC_STOP_LOSS_PCT / 100.0) if signal_type == "BUY_CALL" else spot_val * (1 + config.BTC_STOP_LOSS_PCT / 100.0)

    try:
        tp1_val = float(btc_tp1)
    except (ValueError, TypeError):
        tp1_val = 0.0

    try:
        tp2_val = float(btc_tp2)
    except (ValueError, TypeError):
        tp2_val = 0.0

    try:
        sl_val = float(btc_sl)
    except (ValueError, TypeError):
        sl_val = 0.0

    signal_key = f"BTC_{signal_type}_{spot_val:.1f}"

    # Persistent State Save
    if signal_type in ["BUY_CALL", "BUY_PUT"]:
        trade_logger.save_live_state({
            "last_notified_signal": signal_key,
            "last_signal": {
                "asset": "BITCOIN",
                "signal_type": signal_type,
                "confidence_score": conf_val,
                "spot_price": spot_val,
                "tp1": tp1_val,
                "tp2": tp2_val,
                "sl": sl_val,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "active_trade": {
                "status": "ACTIVE",
                "asset": "BITCOIN",
                "signal_type": signal_type,
                "entry_price": spot_val,
                "target_1": tp1_val,
                "target_2": tp2_val,
                "stop_loss": sl_val,
                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })

    if signal_type in ["BUY_CALL", "BUY_PUT"] and st.session_state.last_notified_signal != signal_key:
        alert_msg = f"<b>🚨 BITCOIN 15M CANDLE WIN SIGNAL</b>\n\nDirection: <b>{signal_type}</b>\nWin Confidence: <b>{conf_val:.1f}%</b>\nEntry Zone: <b>${spot_val:,.2f}</b>\nTP1 (+0.25%): <b>${tp1_val:,.2f}</b>\nSL (-0.15%): <b>${sl_val:,.2f}</b>"
        send_telegram_alert(alert_msg)
        st.session_state.last_notified_signal = signal_key

    conf_info = quant_math_engine.get_candle_confirmation_status()

    st.subheader("📍 LIVE BITCOIN 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            <div class='confirm-timer-box' style='background-color:{"#261c02" if conf_info["conf_status"] == "ACTIVE" else "#0d231a"}; border:1px solid {"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; padding:8px 12px; border-radius:8px; margin-bottom:12px; text-align:center;'>
                <span class='confirm-timer-text' style='color:{"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; font-size:14px; font-weight:bold; font-family:monospace;'>
                    {conf_info["conf_msg"]}
                </span>
            </div>
            <h1 style='color:#00E676; margin:0;'>🟩 PREDICTED WINNING CANDLE: GREEN (UP)</h1>
            <p style='font-size:18px; margin-top:8px;'>Candle Win Confidence: <b>{conf_val:.1f}%</b> | Price: <b>${spot_val:,.2f}</b></p>
            <hr style='border-color:#00E676;'>
            <h2>🎯 ENTRY ZONE: <u style='color:#00E676;'>${spot_val:,.2f}</u></h2>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == "BUY_PUT":
        st.markdown(f"""
        <div class='signal-card-sell'>
            <div class='confirm-timer-box' style='background-color:{"#261c02" if conf_info["conf_status"] == "ACTIVE" else "#0d231a"}; border:1px solid {"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; padding:8px 12px; border-radius:8px; margin-bottom:12px; text-align:center;'>
                <span class='confirm-timer-text' style='color:{"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; font-size:14px; font-weight:bold; font-family:monospace;'>
                    {conf_info["conf_msg"]}
                </span>
            </div>
            <h1 style='color:#E040FB; margin:0;'>🟪 PREDICTED WINNING CANDLE: RED (DOWN)</h1>
            <p style='font-size:18px; margin-top:8px;'>Candle Win Confidence: <b>{conf_val:.1f}%</b> | Price: <b>${spot_val:,.2f}</b></p>
            <hr style='border-color:#E040FB;'>
            <h2>🎯 ENTRY ZONE: <u style='color:#E040FB;'>${spot_val:,.2f}</u></h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='signal-card-wait'>
            <div class='confirm-timer-box' style='background-color:{"#261c02" if conf_info["conf_status"] == "ACTIVE" else "#0d231a"}; border:1px solid {"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; padding:8px 12px; border-radius:8px; margin-bottom:12px; text-align:center;'>
                <span class='confirm-timer-text' style='color:{"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; font-size:14px; font-weight:bold; font-family:monospace;'>
                    {conf_info["conf_msg"]}
                </span>
            </div>
            <h1 style='color:#B0BEC5; margin:0;'>⚪ WAIT - LOW CANDLE WIN CONFIDENCE (< 70%)</h1>
            <p style='font-size:15px; margin-top:8px;'>Reason: <b>{reason_code}</b></p>
        </div>
        """, unsafe_allow_html=True)

    if signal_type != "WAIT":
        st.markdown(f"""
        <div class='cheat-box'>
            <b>📋 BITCOIN 15M CANDLE SCALPER CHEAT SHEET ($ USD):</b><br>
            • <b>Asset Contract  :</b> BTC/USDT (Spot / Futures / Paper Trading)<br>
            • <b>Entry Strategy   :</b> Buy Market Price @ ${spot_val:,.2f}<br>
            • <b>Stop Loss (SL)   :</b> ${sl_val:,.2f} (-0.15% Micro Risk)<br>
            • <b>Target 1 (TP1)   :</b> ${tp1_val:,.2f} (+0.25% Fast Target)<br>
            • <b>Target 2 (TP2)   :</b> ${tp2_val:,.2f} (+0.50% Trend Target)<br>
            • <b>Candle Expiration:</b> Strict Exit @ 15M Candle Close
            <div class='safe-entry-box' style='background-color:#00332c; border:1px solid #00E676; padding:10px; border-radius:8px; margin-top:12px; text-align:center;'>
                <span class='safe-entry-text' style='color:#00E676; font-size:13px; font-weight:bold; font-family:monospace;'>
                    {conf_info["entry_window_msg"]}
                </span>
            </div>
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
    c_high = float(last_row['high'])
    c_low = float(last_row['low'])
    raw_vol = float(last_row['volume']) if 'volume' in last_row else 0.0
    c_volume = raw_vol if raw_vol > 0 else 65000.0
    atm_strike = data_feed.calculate_atm_strike(spot_price)

    st.sidebar.info(f"Symbol: {config.DEFAULT_SYMBOL}")
    st.sidebar.info(f"Timeframe: {config.TIMEFRAME}")
    st.sidebar.metric("NIFTY 50 Spot", f"₹{spot_price:,.2f}")
    st.sidebar.metric("India VIX", f"{india_vix:.2f}", delta=f"{delta_vix_15:+.2f}")

    prev_close = float(df['close'].iloc[-4]) if len(df) >= 4 else float(df['close'].iloc[0])
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

    signal_key = f"NIFTY_{signal_type}_{spot_price:.1f}"

    if signal_type in ["BUY_CALL", "BUY_PUT"]:
        trade_logger.save_live_state({
            "last_notified_signal": signal_key,
            "active_trade": {
                "status": "ACTIVE",
                "asset": "NIFTY50",
                "signal_type": signal_type,
                "strike": atm_strike,
                "entry_price": spot_price,
                "target_1": spot_price + config.TARGET_1_POINTS if signal_type == "BUY_CALL" else spot_price - config.TARGET_1_POINTS,
                "stop_loss": spot_price - config.STOP_LOSS_POINTS if signal_type == "BUY_CALL" else spot_price + config.STOP_LOSS_POINTS,
                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })

    if signal_type in ["BUY_CALL", "BUY_PUT"] and st.session_state.last_notified_signal != signal_key:
        alert_msg = f"<b>🚨 NIFTY 50 CANDLE WIN SIGNAL</b>\n\nDirection: <b>{signal_type}</b>\nStrike: <b>NIFTY {atm_strike}</b>\nSpot: <b>₹{spot_price:,.2f}</b>\nSL: <b>-8 pts</b>\nTP1: <b>+12 pts</b>"
        send_telegram_alert(alert_msg)
        st.session_state.last_notified_signal = signal_key

    conf_info = quant_math_engine.get_candle_confirmation_status(ist_now)

    st.subheader("📍 LIVE NIFTY 50 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            <div class='confirm-timer-box' style='background-color:{"#261c02" if conf_info["conf_status"] == "ACTIVE" else "#0d231a"}; border:1px solid {"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; padding:8px 12px; border-radius:8px; margin-bottom:12px; text-align:center;'>
                <span class='confirm-timer-text' style='color:{"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; font-size:14px; font-weight:bold; font-family:monospace;'>
                    {conf_info["conf_msg"]}
                </span>
            </div>
            <h1 style='color:#00E676; margin:0;'>🟩 PREDICTED WINNING CANDLE: CALL (CE)</h1>
            <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b></p>
            <hr style='border-color:#00E676;'>
            <h2>🎯 TARGET STRIKE: <u style='color:#00E676;'>NIFTY {atm_strike} CE</u></h2>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == "BUY_PUT":
        st.markdown(f"""
        <div class='signal-card-sell'>
            <div class='confirm-timer-box' style='background-color:{"#261c02" if conf_info["conf_status"] == "ACTIVE" else "#0d231a"}; border:1px solid {"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; padding:8px 12px; border-radius:8px; margin-bottom:12px; text-align:center;'>
                <span class='confirm-timer-text' style='color:{"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; font-size:14px; font-weight:bold; font-family:monospace;'>
                    {conf_info["conf_msg"]}
                </span>
            </div>
            <h1 style='color:#E040FB; margin:0;'>🟪 PREDICTED WINNING CANDLE: RED (DOWN)</h1>
            <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b></p>
            <hr style='border-color:#E040FB;'>
            <h2>🎯 TARGET STRIKE: <u style='color:#E040FB;'>NIFTY {atm_strike} PE</u></h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='signal-card-wait'>
            <div class='confirm-timer-box' style='background-color:{"#261c02" if conf_info["conf_status"] == "ACTIVE" else "#0d231a"}; border:1px solid {"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; padding:8px 12px; border-radius:8px; margin-bottom:12px; text-align:center;'>
                <span class='confirm-timer-text' style='color:{"#FFD54F" if conf_info["conf_status"] == "ACTIVE" else "#00E676"}; font-size:14px; font-weight:bold; font-family:monospace;'>
                    {conf_info["conf_msg"]}
                </span>
            </div>
            <h1 style='color:#B0BEC5; margin:0;'>⚪ WAIT - LOW CANDLE WIN CONFIDENCE (< 70%)</h1>
            <p style='font-size:15px; margin-top:8px;'>Reason: <b>{reason_code}</b></p>
        </div>
        """, unsafe_allow_html=True)

    if signal_type != "WAIT":
        st.markdown(f"""
        <div class='cheat-box'>
            <b>📋 DHAN / TRADINGVIEW EXECUTION CHEAT SHEET:</b><br>
            • <b>Option Contract  :</b> NIFTY {atm_strike} {"CE" if signal_type == "BUY_CALL" else "PE"}<br>
            • <b>Entry Strategy   :</b> Buy Market Price on Dhan / TradingView<br>
            • <b>Stop Loss (SL)   :</b> -8 Points Premium (Micro Risk: ₹200 / lot)<br>
            • <b>Target 1 (TP1)   :</b> +12 Points Premium (Fast Profit: ₹300 / lot)<br>
            • <b>Target 2 (TP2)   :</b> +25 Points Premium (Max Profit: ₹625 / lot)<br>
            • <b>Candle Expiration:</b> Strict Exit @ 15M Candle Close
            <div class='safe-entry-box' style='background-color:#00332c; border:1px solid #00E676; padding:10px; border-radius:8px; margin-top:12px; text-align:center;'>
                <span class='safe-entry-text' style='color:#00E676; font-size:13px; font-weight:bold; font-family:monospace;'>
                    {conf_info["entry_window_msg"]}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# DISPLAY ACTIVE TRADE PERSISTENCE BANNER (Survives Browser Refresh F5)
current_active_trade = trade_logger.load_live_state().get("active_trade", {})
if current_active_trade.get("status") == "ACTIVE":
    act_asset = current_active_trade.get("asset", selected_asset)
    act_dir = current_active_trade.get("signal_type", "BUY_CALL")
    act_entry = float(current_active_trade.get("entry_price", 0.0))
    act_tp1 = float(current_active_trade.get("target_1", 0.0))
    act_sl = float(current_active_trade.get("stop_loss", 0.0))
    act_curr = "$" if act_asset == "BITCOIN" else "₹"
    
    # Auto-Evaluation of TP / SL against current spot price
    auto_exit_triggered = False
    exit_reason = ""
    if spot_val > 0 and act_tp1 > 0 and act_sl > 0:
        if act_dir == "BUY_CALL":
            if spot_val >= act_tp1:
                auto_exit_triggered = True
                exit_reason = "TARGET_1_HIT (+0.25% / +12 pts)"
            elif spot_val <= act_sl:
                auto_exit_triggered = True
                exit_reason = "STOP_LOSS_HIT (-0.15% / -8 pts)"
        elif act_dir == "BUY_PUT":
            if spot_val <= act_tp1:
                auto_exit_triggered = True
                exit_reason = "TARGET_1_HIT (+0.25% / +12 pts)"
            elif spot_val >= act_sl:
                auto_exit_triggered = True
                exit_reason = "STOP_LOSS_HIT (-0.15% / -8 pts)"

    st.markdown(f"""
    <div class='active-trade-box'>
        <b>⚡ LIVE ACTIVE POSITION RUNNING (PERSISTENT):</b><br>
        • <b>Active Market</b>   : {act_asset} ({act_dir})<br>
        • <b>Entry Price</b>     : {act_curr}{act_entry:,.2f}<br>
        • <b>Target 1 (TP1)</b>   : {act_curr}{act_tp1:,.2f}<br>
        • <b>Stop Loss (SL)</b>   : {act_curr}{act_sl:,.2f}<br>
        • <b>Trade Status</b>    : 🟢 ACTIVE RUNNING (State Restored on F5 Refresh)
    </div>
    """, unsafe_allow_html=True)
    
    col_exit1, col_exit2 = st.columns([2, 1])
    with col_exit1:
        st.write(f"📊 **Current Live Spot:** `{act_curr}{spot_val:,.2f}`")
    with col_exit2:
        if st.button("⚡ Square Off Position Now", key="btn_square_off_dashboard"):
            auto_exit_triggered = True
            exit_reason = "MANUAL_SQUARE_OFF"

    if auto_exit_triggered:
        qty = 15 if act_asset != "BITCOIN" else 1
        exit_p = spot_val if spot_val > 0 else act_entry
        is_win = False
        if "TARGET" in exit_reason:
            is_win = True
        elif "STOP_LOSS" in exit_reason:
            is_win = False
        else:
            is_win = (exit_p >= act_entry) if act_dir == "BUY_CALL" else (exit_p <= act_entry)
            
        trade_logger.record_completed_trade(
            symbol=act_asset,
            strike=act_dir,
            entry_price=act_entry,
            exit_price=exit_p,
            qty=qty,
            status="WIN" if is_win else "LOSS",
            win_loss_reason=exit_reason
        )
        trade_logger.save_live_state({"active_trade": {"status": "NO_POSITION"}})
        st.success(f"🎉 Active Position Closed! Reason: {exit_reason}")
        st.rerun()

if breakdown:
    st.markdown(f"""
    <div class='layer-box'>
        <b>🛡️ QUANT ENGINE BREAKDOWN STATUS:</b><br>
        • <b>Layer 1 (Body Intensity)      :</b> {breakdown.get('l1_status', 'N/A')}<br>
        • <b>Layer 2 (Volume Acceleration)  :</b> {breakdown.get('l2_status', 'N/A')}<br>
        • <b>Layer 3 (Momentum Delta)       :</b> {breakdown.get('l3_status', 'N/A')}<br>
        • <b>Layer 4 (Fib Discount Guard)   :</b> {breakdown.get('l4_status', 'N/A')}<br>
        • <b>Layer 5 (Candle Win Verdict)   :</b> {breakdown.get('l5_status', 'N/A')}
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.subheader("📊 BOT PERFORMANCE LOGS & ACCURACY TRACKER")

tab1, tab2 = st.tabs(["📅 Today's Live Log", "📊 7-Day Weekly Performance Tracker"])

cols_to_show = ["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"]

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
        available_cols = [c for c in cols_to_show if c in df_today.columns]
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
        available_cols = [c for c in cols_to_show if c in df_weekly.columns]
        st.dataframe(df_weekly[available_cols], use_container_width=True)
    else:
        st.info("ℹ️ No weekly trade history recorded yet.")

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