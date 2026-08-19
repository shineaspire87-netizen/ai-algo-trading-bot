# ================================================================================
# ANTONY QUANT AI TERMINAL - DASHBOARD (CHAMPION EDITION V10.0)
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

# Page Setup
st.set_page_config(
    page_title="ANTONY Quant AI - NIFTY 50 Co-Pilot",
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

def check_market_status():
    ist_now = data_feed.get_ist_now()
    if ist_now.weekday() >= 5:
        return False, "🔴 NSE CLOSED (WEEKEND)"
    return (time(9, 15) <= ist_now.time() <= time(15, 30)), "🟢 NSE MARKET LIVE (09:15 AM - 03:30 PM IST)" if (time(9, 15) <= ist_now.time() <= time(15, 30)) else "🔴 NSE MARKET CLOSED (AFTER HOURS)"

is_open, market_status_text = check_market_status()

# Custom Styling
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

st.markdown("<div class='main-title'>🎯 ANTONY QUANT AI: NIFTY 50 SIGNAL CO-PILOT</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Champion Edition | Fib Golden Pocket & Volume Cutoff Engine</div>", unsafe_allow_html=True)

# Live Ticking Javascript Clock
st.components.v1.html("""
<div style="background-color: #111827; border: 1px solid #374151; padding: 10px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6;">
    <span id="live-date" style="color: #60A5FA; font-size: 15px; font-weight: bold;"></span> &nbsp;|&nbsp; 
    <span id="live-clock" style="color: #FBBF24; font-size: 18px; font-weight: bold;"></span>
</div>
<script>
function updateClock() {
    const now = new Date();
    document.getElementById('live-date').innerText = '📅 ' + now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
    document.getElementById('live-clock').innerText = '⏰ ' + now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) + ' IST';
}
setInterval(updateClock, 1000); updateClock();
</script>
""", height=65)

# Market Status Indicator
if is_open:
    st.markdown(f"<div class='market-badge-open'>{market_status_text}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='market-badge-closed'>{market_status_text} — LAST CLOSE DATA SHOWN</div>", unsafe_allow_html=True)

# Fetch NIFTY Live Data & VIX
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

# Index tickers on Yahoo Finance have volume=0, fallback to 65k default when volume is 0 or missing
raw_vol = float(last_row['volume']) if 'volume' in last_row else 0.0
c_volume = raw_vol if raw_vol > 0 else 65000.0

atm_strike = data_feed.calculate_atm_strike(spot_price)

# Proxies for PCR & OI Walls
prev_close = float(df['close'].iloc[-4]) if len(df) >= 4 else float(df['close'].iloc[0])
nifty_dir = "UP" if spot_price > prev_close else ("DOWN" if spot_price < prev_close else "FLAT")

heavy_k = 4 if nifty_dir != "FLAT" else 2
heavy_a = 0.82
pcr_val = 1.18 if nifty_dir == "UP" else (0.82 if nifty_dir == "DOWN" else 1.0)
delta_pcr = +0.03 if nifty_dir == "UP" else (-0.03 if nifty_dir == "DOWN" else 0.0)
ce_wall = atm_strike + 200
pe_wall = atm_strike - 200

ist_now = data_feed.get_ist_now()

# Execute Champion Engine with Fib & Volume Cutoff
signal_type, reason_code, pos_multiplier, breakdown = quant_math_engine.master_institutional_decision_engine(
    nifty_direction=nifty_dir,
    heavyweight_k=heavy_k,
    heavyweight_a=heavy_a,
    india_vix=india_vix,
    delta_vix_15=delta_vix_15,
    pcr_oi=pcr_val,
    delta_pcr_15=delta_pcr,
    nifty_spot=spot_price,
    nearest_ce_wall=ce_wall,
    nearest_pe_wall=pe_wall,
    volume_15m=c_volume,
    candle_high=c_high,
    candle_low=c_low,
    ist_time=ist_now.time(),
    nifty_target=config.UNDERLYING_TARGET_NIFTY
)

# Render Signal Card
st.subheader("📍 LIVE NIFTY 50 SIGNAL CARD")

if signal_type == "BUY_CALL":
    st.markdown(f"""
    <div class='signal-card-buy'>
        <h1 style='color:#00E676; margin:0;'>🟩 BUY CALL OPTION (CE)</h1>
        <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b> | Position Size: <b>{int(pos_multiplier*100)}%</b></p>
        <hr style='border-color:#00E676;'>
        <h2>🎯 TARGET STRIKE: <u style='color:#00E676;'>NIFTY {atm_strike} CE</u></h2>
    </div>
    """, unsafe_allow_html=True)

elif signal_type == "BUY_PUT":
    st.markdown(f"""
    <div class='signal-card-sell'>
        <h1 style='color:#E040FB; margin:0;'>🟪 BUY PUT OPTION (PE)</h1>
        <p style='font-size:18px; margin-top:8px;'>NIFTY 50 Spot: <b>₹{spot_price:,.2f}</b> | Position Size: <b>{int(pos_multiplier*100)}%</b></p>
        <hr style='border-color:#E040FB;'>
        <h2>🎯 TARGET STRIKE: <u style='color:#E040FB;'>NIFTY {atm_strike} PE</u></h2>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown(f"""
    <div class='signal-card-wait'>
        <h1 style='color:#B0BEC5; margin:0;'>⚪ WAIT - REJECTED BY 5-LAYER FILTER</h1>
        <p style='font-size:15px; margin-top:8px;'>Reason: <b>{reason_code}</b></p>
    </div>
    """, unsafe_allow_html=True)

# Render 5-Layer Breakdown Box
st.markdown(f"""
<div class='layer-box'>
    <b>🛡️ INSTITUTIONAL 5-LAYER FILTER STATUS:</b><br>
    • <b>Layer 1 (Heavyweights K/A) :</b> {breakdown['l1_heavyweights']}<br>
    • <b>Layer 2 (India VIX & ΔVIX) :</b> {breakdown['l2_vix']}<br>
    • <b>Layer 3 (PCR & ΔPCR 15M)  :</b> {breakdown['l3_pcr']}<br>
    • <b>Layer 4 (OI Clear Runway) :</b> {breakdown['l4_runway']}<br>
    • <b>Layer 5 (Engine Verdict)   :</b> {breakdown['l5_status']}
</div>
""", unsafe_allow_html=True)

# Render Cheat Sheet Numbers
if signal_type != "WAIT":
    st.markdown(f"""
    <div class='cheat-box'>
        <b>📋 DHAN / TRADINGVIEW EXECUTION CHEAT SHEET:</b><br>
        • <b>Option Contract  :</b> NIFTY {atm_strike} {"CE" if signal_type == "BUY_CALL" else "PE"}<br>
        • <b>Entry Strategy   :</b> Buy Market Price on Dhan / TradingView<br>
        • <b>Stop Loss (SL)   :</b> -15 Points Premium (Strict Risk: ₹375 / lot)<br>
        • <b>Target 1 (TP1)   :</b> +20 Points Premium (Profit: ₹500 / lot)<br>
        • <b>Target 2 (TP2)   :</b> +45 Points Premium (Profit: ₹1,125 / lot)
    </div>
    """, unsafe_allow_html=True)

# --- TRADE PERFORMANCE LOGS ---
st.divider()
st.subheader("📊 BOT PERFORMANCE LOGS & ACCURACY TRACKER")

tab1, tab2 = st.tabs(["📅 Today's Live Log", "📊 7-Day Weekly Performance Tracker"])

with tab1:
    today_summary = trade_logger.get_today_summary()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today's Trades", f"{today_summary['total_trades']} / 3")
    col2.metric("Win Rate", f"{today_summary['win_rate']}%")
    col3.metric("Wins / Losses", f"{today_summary['wins']} W / {today_summary['losses']} L")
    col4.metric("Net Daily PnL", f"₹{today_summary['net_pnl']:,.2f}")
    
    today_trades = trade_logger.get_today_trades()
    if today_trades:
        df_today = pd.DataFrame(today_trades)
        st.dataframe(
            df_today[["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"]],
            use_container_width=True
        )
        st.subheader("🔍 Today's AI Post-Mortem Analysis")
        for t in today_trades:
            st.markdown(ai_analyst.generate_trade_post_mortem(t["result"], t["layers"], t["net_pnl"]))
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
        st.dataframe(
            df_weekly[["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"]],
            use_container_width=True
        )
    else:
        st.info("ℹ️ No weekly trade history recorded yet. New live signals will accumulate here over the 7-day test period.")

# --- END-OF-DAY AI SELF-DIAGNOSTIC REPORT ---
st.divider()
today_trades = trade_logger.get_today_trades()
eod_report = ai_analyst.generate_eod_bot_diagnostic(today_trades, india_vix, pcr_val)
st.markdown(f"<div class='diagnostic-box'>{eod_report}</div>", unsafe_allow_html=True)

# Sidebar System Control
st.sidebar.title("⚙️ System Control")
st.sidebar.info(f"Symbol: {config.DEFAULT_SYMBOL}")
st.sidebar.info(f"Timeframe: {config.TIMEFRAME}")
st.sidebar.metric("NIFTY 50 Spot", f"₹{spot_price:,.2f}")
st.sidebar.metric("India VIX", f"{india_vix:.2f}", delta=f"{delta_vix_15:+.2f}")

if st.sidebar.button("🧹 Clear All Trade History"):
    trade_logger.clear_all_trades()
    st.sidebar.success("Trade Logs Reset!")
    st.rerun()

if st.sidebar.button("🔄 Refresh Signal Engine"):
    st.rerun()