# ================================================================================
# ANTONY QUANT AI TERMINAL - DASHBOARD (CANDLE WIN CONFIDENCE ENGINE V13.0)
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

if "last_notified_signal" not in st.session_state:
    st.session_state.last_notified_signal = "WAIT"

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
    .layer-box { background-color: #0d1b2a; border: 1px solid #1e3a8a; padding: 15px; border-radius: 10px; color: #e2e8f0; font-size: 15px; margin-top: 15px; line-height: 1.6; }
    .diagnostic-box { background-color: #1a102f; border: 1px solid #9c27b0; padding: 18px; border-radius: 12px; margin-top: 20px; color: #e1bee7; font-size: 15px; line-height: 1.6; }
    .cheat-box { background-color: #0d47a1; padding: 18px; border-radius: 12px; margin-top: 15px; color: white; font-size: 16px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("⚙️ System Control")
selected_asset = st.sidebar.selectbox("🎯 Select Active Trading Market:", ["BITCOIN (BTC/USDT)", "NIFTY 50 (₹)"])

is_open, market_status_text = check_market_status(selected_asset)

st.markdown(f"<div class='main-title'>🎯 ANTONY QUANT AI: {selected_asset.upper()} CO-PILOT</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>15M Candle Winning Direction Engine | High Confidence (>70%) Execution</div>", unsafe_allow_html=True)

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
        const now = new Date();
        document.getElementById('live-date').innerText = '📅 ' + now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
        document.getElementById('live-clock').innerText = '⏰ ' + now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) + ' IST';
        
        const min = now.getMinutes();
        const sec = now.getSeconds();
        const elapsedSec = ((min % 15) * 60) + sec;
        const remSec = 900 - elapsedSec;
        const remMin = Math.floor(remSec / 60);
        const remS = remSec % 60;
        
        const minStr = String(remMin).padStart(2, '0');
        const secStr = String(remS).padStart(2, '0');
        
        const timerElem = document.getElementById('candle-timer');
        if (remSec <= 60) {
            timerElem.style.color = '#FF5252';
            timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
        } else {
            timerElem.style.color = '#FFD54F';
            timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
        }
    }
    setInterval(updateClockAndCandleTimer, 1000); updateClockAndCandleTimer();

    const ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@ticker');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const price = parseFloat(data.c).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        document.getElementById('btc-ticker-price').innerText = '$' + price;
    };
    </script>
    """, height=85)
else:
    st.components.v1.html("""
    <div style="background-color: #111827; border: 1px solid #374151; padding: 10px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6;">
        <span id="live-date" style="color: #60A5FA; font-size: 15px; font-weight: bold;"></span> &nbsp;|&nbsp; 
        <span id="live-clock" style="color: #FBBF24; font-size: 16px; font-weight: bold;"></span><br>
        <span id="candle-timer" style="color: #FFD54F; font-size: 16px; font-weight: bold;">⏳ 15M CANDLE: Loading...</span>
    </div>
    <script>
    function updateClockAndCandleTimer() {
        const now = new Date();
        document.getElementById('live-date').innerText = '📅 ' + now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
        document.getElementById('live-clock').innerText = '⏰ ' + now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) + ' IST';
        
        const min = now.getMinutes();
        const sec = now.getSeconds();
        const elapsedSec = ((min % 15) * 60) + sec;
        const remSec = 900 - elapsedSec;
        const remMin = Math.floor(remSec / 60);
        const remS = remSec % 60;
        
        const minStr = String(remMin).padStart(2, '0');
        const secStr = String(remS).padStart(2, '0');
        
        const timerElem = document.getElementById('candle-timer');
        if (remSec <= 60) {
            timerElem.style.color = '#FF5252';
            timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
        } else {
            timerElem.style.color = '#FFD54F';
            timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
        }
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

    if signal_type in ["BUY_CALL", "BUY_PUT"] and st.session_state.last_notified_signal != f"BTC_{signal_type}_{spot_val}":
        alert_msg = f"<b>🚨 BITCOIN 15M CANDLE WIN SIGNAL</b>\n\nDirection: <b>{signal_type}</b>\nWin Confidence: <b>{conf_val:.1f}%</b>\nEntry Zone: <b>${spot_val:,.2f}</b>\nTP1 (+0.25%): <b>${tp1_val:,.2f}</b>\nSL (-0.15%): <b>${sl_val:,.2f}</b>"
        send_telegram_alert(alert_msg)
        st.session_state.last_notified_signal = f"BTC_{signal_type}_{spot_val}"

    st.subheader("📍 LIVE BITCOIN 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            <h1 style='color:#00E676; margin:0;'>🟩 PREDICTED WINNING CANDLE: GREEN (UP)</h1>
            <p style='font-size:18px; margin-top:8px;'>Candle Win Confidence: <b>{conf_val:.1f}%</b> | Price: <b>${spot_val:,.2f}</b></p>
            <hr style='border-color:#00E676;'>
            <h2>🎯 ENTRY ZONE: <u style='color:#00E676;'>${spot_val:,.2f}</u></h2>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == "BUY_PUT":
        st.markdown(f"""
        <div class='signal-card-sell'>
            <h1 style='color:#E040FB; margin:0;'>🟪 PREDICTED WINNING CANDLE: RED (DOWN)</h1>
            <p style='font-size:18px; margin-top:8px;'>Candle Win Confidence: <b>{conf_val:.1f}%</b> | Price: <b>${spot_val:,.2f}</b></p>
            <hr style='border-color:#E040FB;'>
            <h2>🎯 ENTRY ZONE: <u style='color:#E040FB;'>${spot_val:,.2f}</u></h2>
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
            • <b>Entry Strategy   :</b> Buy Market Price @ ${spot_val:,.2f}<br>
            • <b>Stop Loss (SL)   :</b> ${sl_val:,.2f} (-0.15% Micro Risk)<br>
            • <b>Target 1 (TP1)   :</b> ${tp1_val:,.2f} (+0.25% Fast Target)<br>
            • <b>Target 2 (TP2)   :</b> ${tp2_val:,.2f} (+0.50% Trend Target)<br>
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

    if signal_type in ["BUY_CALL", "BUY_PUT"] and st.session_state.last_notified_signal != f"NIFTY_{signal_type}_{spot_price}":
        alert_msg = f"<b>🚨 NIFTY 50 CANDLE WIN SIGNAL</b>\n\nDirection: <b>{signal_type}</b>\nStrike: <b>NIFTY {atm_strike}</b>\nSpot: <b>₹{spot_price:,.2f}</b>\nSL: <b>-8 pts</b>\nTP1: <b>+12 pts</b>"
        send_telegram_alert(alert_msg)
        st.session_state.last_notified_signal = f"NIFTY_{signal_type}_{spot_price}"

    st.subheader("📍 LIVE NIFTY 50 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            <h1 style='color:#00E676; margin:0;'>🟩 PREDICTED WINNING CANDLE: CALL (CE)</h1>
            <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b></p>
            <hr style='border-color:#00E676;'>
            <h2>🎯 TARGET STRIKE: <u style='color:#00E676;'>NIFTY {atm_strike} CE</u></h2>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == "BUY_PUT":
        st.markdown(f"""
        <div class='signal-card-sell'>
            <h1 style='color:#E040FB; margin:0;'>🟪 PREDICTED WINNING CANDLE: PUT (PE)</h1>
            <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b></p>
            <hr style='border-color:#E040FB;'>
            <h2>🎯 TARGET STRIKE: <u style='color:#E040FB;'>NIFTY {atm_strike} PE</u></h2>
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
            • <b>Entry Strategy   :</b> Buy Market Price on Dhan / TradingView<br>
            • <b>Stop Loss (SL)   :</b> -8 Points Premium (Micro Risk: ₹200 / lot)<br>
            • <b>Target 1 (TP1)   :</b> +12 Points Premium (Fast Profit: ₹300 / lot)<br>
            • <b>Target 2 (TP2)   :</b> +25 Points Premium (Max Profit: ₹625 / lot)<br>
            • <b>Candle Expiration:</b> Strict Exit @ 15M Candle Close
        </div>
        """, unsafe_allow_html=True)

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
        st.dataframe(df_today[["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"]], use_container_width=True)
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
        st.dataframe(df_weekly[["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"]], use_container_width=True)
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