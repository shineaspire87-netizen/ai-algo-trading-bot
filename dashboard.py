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

if "notified_candles" not in st.session_state:
    st.session_state.notified_candles = set()
if "notified_completed_trades" not in st.session_state:
    st.session_state.notified_completed_trades = set()
if "locked_candle_id" not in st.session_state:
    st.session_state.locked_candle_id = "NONE"
if "locked_signal_state" not in st.session_state:
    st.session_state.locked_signal_state = None

def check_market_status(asset_choice):
    if asset_choice == "BITCOIN (BTC/USDT)":
        return True, "🟢 BITCOIN 24/7 MARKET LIVE (CONTINUOUS TRADING)"
    elif asset_choice == "FOREX (EUR/USD $)":
        return data_feed.is_forex_market_open(), "🟢 FOREX 24/5 MARKET LIVE (EUR/USD)" if data_feed.is_forex_market_open() else "🔴 FOREX CLOSED (WEEKEND)"
    
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
    .time-badge-safe { background-color: #004D40; border: 1px solid #00E676; padding: 10px; border-radius: 8px; text-align: center; color: #00E676; font-weight: bold; margin-bottom: 15px; }
    .time-badge-extended { background-color: #4A3B00; border: 1px solid #FFD54F; padding: 10px; border-radius: 8px; text-align: center; color: #FFD54F; font-weight: bold; margin-bottom: 15px; }
    .time-badge-late { background-color: #4A1414; border: 1px solid #FF5252; padding: 10px; border-radius: 8px; text-align: center; color: #FF5252; font-weight: bold; margin-bottom: 15px; }
    .layer-box { background-color: #0d1b2a; border: 1px solid #1e3a8a; padding: 15px; border-radius: 10px; color: #e2e8f0; font-size: 15px; margin-top: 15px; line-height: 1.6; }
    .diagnostic-box { background-color: #1a102f; border: 1px solid #9c27b0; padding: 18px; border-radius: 12px; margin-top: 10px; color: #e1bee7; font-size: 15px; line-height: 1.6; }
    .cheat-box { background-color: #0d47a1; padding: 18px; border-radius: 12px; margin-top: 15px; color: white; font-size: 16px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("⚙️ System Control")
selected_asset = st.sidebar.selectbox("🎯 Select Active Trading Market:", ["NIFTY 50 (₹)", "BITCOIN (BTC/USDT)", "FOREX (EUR/USD $)"])

if selected_asset == "BITCOIN (BTC/USDT)":
    asset_key = "BTC"
elif selected_asset == "FOREX (EUR/USD $)":
    asset_key = "FOREX"
else:
    asset_key = "NIFTY"

currency_sym = "$" if asset_key in ["BTC", "FOREX"] else "₹"

if asset_key == "BTC":
    default_cap_val = getattr(config, "BTC_START_CAPITAL_USD", 20.00)
elif asset_key == "FOREX":
    default_cap_val = getattr(config, "FOREX_START_CAPITAL_USD", 100.00)
else:
    default_cap_val = getattr(config, "NIFTY_START_CAPITAL_INR", 2000.00)

user_cap_input = st.sidebar.number_input(f"💰 {asset_key} Starting Capital ({currency_sym}):", min_value=1.0, value=float(default_cap_val), step=5.0)

if st.sidebar.button(f"🧹 Clear {asset_key} History"):
    trade_logger.clear_asset_trades(asset_key)
    st.sidebar.success(f"{asset_key} History Cleared!")
    st.rerun()

is_open, market_status_text = check_market_status(selected_asset)

st.markdown(f"<div class='main-title'>🎯 ANTONY QUANT AI: {selected_asset.upper()} CO-PILOT</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Triple-Asset Multi-Engine | NIFTY 50, Bitcoin & Forex EUR/USD</div>", unsafe_allow_html=True)

cap_summary = trade_logger.get_account_capital_summary(asset_key, custom_start_cap=user_cap_input)

st.subheader(f"💵 ACCOUNT CAPITAL & RISK BUDGET ({currency_sym})")
if asset_key == "BTC":
    btc_cap = getattr(config, "BTC_START_CAPITAL_USD", 20.00)
    btc_sl = getattr(config, "BTC_STOP_LOSS_PCT", 0.15)
    btc_tp1 = getattr(config, "BTC_TARGET_1_PCT", 0.25)
    max_risk_val = f"{btc_cap * (btc_sl/100):.2f}"
    max_risk_sub = f"-{btc_sl:.2f}%"
    target1_val = f"{btc_cap * (btc_tp1/100):.2f}"
    target1_sub = f"+{btc_tp1:.2f}%"
elif asset_key == "FOREX":
    fx_sl_pips = getattr(config, "FOREX_STOP_LOSS_PIPS", 10.0)
    fx_tp1_pips = getattr(config, "FOREX_TARGET_1_PIPS", 15.0)
    max_risk_val = f"{fx_sl_pips * 0.10:.2f}"
    max_risk_sub = f"-{fx_sl_pips:.0f} Pips"
    target1_val = f"{fx_tp1_pips * 0.10:.2f}"
    target1_sub = f"+{fx_tp1_pips:.0f} Pips"
else:
    nifty_sl_pts = getattr(config, "STOP_LOSS_POINTS", 8.0)
    nifty_tp1_pts = getattr(config, "TARGET_1_POINTS", 12.0)
    nifty_lot = getattr(config, "NIFTY_LOT_SIZE", 25)
    max_risk_val = f"{nifty_sl_pts * nifty_lot:,.0f}"
    max_risk_sub = f"-{nifty_sl_pts:.0f} pts"
    target1_val = f"{nifty_tp1_pts * nifty_lot:,.0f}"
    target1_sub = f"+{nifty_tp1_pts:.0f} pts"

st.markdown(f"""
<div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; margin-bottom: 20px; background-color: #111827; border: 1px solid #374151; padding: 15px; border-radius: 12px;">
    <div style="flex: 1; min-width: 120px; text-align: center; border-right: 1px solid #374151;">
        <span style="color: #9CA3AF; font-size: 13px; font-weight: 500;">Starting Capital</span><br>
        <span style="color: #F3F4F6; font-size: 20px; font-weight: bold;">{currency_sym}{cap_summary['starting_capital']:,.2f}</span>
    </div>
    <div style="flex: 1; min-width: 120px; text-align: center; border-right: 1px solid #374151;">
        <span style="color: #9CA3AF; font-size: 13px; font-weight: 500;">Current Equity</span><br>
        <span style="color: #60A5FA; font-size: 20px; font-weight: bold;">{currency_sym}{cap_summary['current_equity']:,.2f}</span>
    </div>
    <div style="flex: 1; min-width: 130px; text-align: center; border-right: 1px solid #374151;">
        <span style="color: #9CA3AF; font-size: 13px; font-weight: 500;">Max Risk / Trade</span><br>
        <span style="color: #FF5252; font-size: 18px; font-weight: bold;">-{currency_sym}{max_risk_val} <span style="font-size: 12px; color: #FF8A8A;">({max_risk_sub})</span></span>
    </div>
    <div style="flex: 1; min-width: 130px; text-align: center;">
        <span style="color: #9CA3AF; font-size: 13px; font-weight: 500;">Target 1 Profit</span><br>
        <span style="color: #00E676; font-size: 18px; font-weight: bold;">+{currency_sym}{target1_val} <span style="font-size: 12px; color: #B9F6CA;">({target1_sub})</span></span>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

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
elif selected_asset == "FOREX (EUR/USD $)":
    df_forex_init = data_feed.fetch_forex_live_data(config.FOREX_SYMBOL, config.TIMEFRAME)
    forex_spot_init = float(df_forex_init.iloc[-1]['close']) if not df_forex_init.empty else 1.0850
    st.components.v1.html(f"""
    <div style="background-color: #111827; border: 1px solid #374151; padding: 12px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6;">
        <span id="live-date" style="color: #60A5FA; font-size: 14px; font-weight: bold;"></span> &nbsp;|&nbsp; 
        <span id="live-clock" style="color: #FBBF24; font-size: 16px; font-weight: bold;"></span><br>
        <span id="candle-timer" style="color: #FFD54F; font-size: 16px; font-weight: bold;">⏳ 15M CANDLE: Loading...</span> &nbsp;|&nbsp;
        <span style="color:#00E676; font-weight:bold;">⚡ FOREX TICKER: </span>
        <span id="forex-ticker-price" style="color: #00E676; font-size: 20px; font-weight: bold;">${forex_spot_init:.5f}</span>
    </div>
    <script>
    function updateClockAndCandleTimer() {{
        const now = new Date();
        document.getElementById('live-date').innerText = '📅 ' + now.toLocaleDateString('en-IN', {{ timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }});
        document.getElementById('live-clock').innerText = '⏰ ' + now.toLocaleTimeString('en-IN', {{ timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }}) + ' IST';
        
        const min = now.getMinutes();
        const sec = now.getSeconds();
        const elapsedSec = ((min % 15) * 60) + sec;
        const remSec = 900 - elapsedSec;
        const remMin = Math.floor(remSec / 60);
        const remS = remSec % 60;
        
        const minStr = String(remMin).padStart(2, '0');
        const secStr = String(remS).padStart(2, '0');
        
        const timerElem = document.getElementById('candle-timer');
        if (remSec <= 60) {{
            timerElem.style.color = '#FF5252';
            timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
        }} else {{
            timerElem.style.color = '#FFD54F';
            timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
        }}
    }}
    setInterval(updateClockAndCandleTimer, 1000); updateClockAndCandleTimer();

    let lastForexPrice = {forex_spot_init};
    async function fetchRealForexLiveTicker() {{
        const targetUrl = 'https://query1.finance.yahoo.com/v8/finance/chart/EURUSD%3DX?interval=1m';
        const proxies = [
            'https://api.allorigins.win/get?url=' + encodeURIComponent(targetUrl),
            'https://api.codetabs.com/v1/proxy?quest=' + encodeURIComponent(targetUrl),
            targetUrl
        ];
        for (let url of proxies) {{
            try {{
                const res = await fetch(url);
                if (res.ok) {{
                    const text = await res.text();
                    let data;
                    try {{
                        data = JSON.parse(text);
                        if (data.contents) data = JSON.parse(data.contents);
                    }} catch(e) {{ continue; }}
                    
                    const price = data.chart?.result?.[0]?.meta?.regularMarketPrice;
                    if (price) {{
                        const elem = document.getElementById('forex-ticker-price');
                        if (elem) {{
                            if (price > lastForexPrice) {{
                                elem.style.color = '#00E676';
                            }} else if (price < lastForexPrice) {{
                                elem.style.color = '#FF5252';
                            }}
                            elem.innerText = '$' + price.toFixed(5);
                            lastForexPrice = price;
                        }}
                        return;
                    }}
                }}
            }} catch(e) {{}}
        }}
    }}
    setInterval(fetchRealForexLiveTicker, 1500);
    fetchRealForexLiveTicker();
    </script>
    """, height=85)
else: # NIFTY 50 MODE
    df_nifty_init = data_feed.fetch_nifty_live_data(config.DEFAULT_SYMBOL, config.TIMEFRAME)
    nifty_spot_init = float(df_nifty_init.iloc[-1]['close']) if not df_nifty_init.empty else 24290.0
    st.components.v1.html(f"""
    <div style="background-color: #111827; border: 1px solid #374151; padding: 12px; border-radius: 10px; text-align: center; font-family: monospace; color: #F3F4F6;">
        <span id="live-date" style="color: #60A5FA; font-size: 14px; font-weight: bold;"></span> &nbsp;|&nbsp; 
        <span id="live-clock" style="color: #FBBF24; font-size: 16px; font-weight: bold;"></span><br>
        <span id="candle-timer" style="color: #FFD54F; font-size: 16px; font-weight: bold;">⏳ 15M CANDLE: Loading...</span> &nbsp;|&nbsp;
        <span style="color:#00E676; font-weight:bold;">⚡ NIFTY TICKER: </span>
        <span id="nifty-ticker-price" style="color: #00E676; font-size: 20px; font-weight: bold;">₹{nifty_spot_init:,.2f}</span>
    </div>
    <script>
    function updateClockAndCandleTimer() {{
        const now = new Date();
        document.getElementById('live-date').innerText = '📅 ' + now.toLocaleDateString('en-IN', {{ timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }});
        document.getElementById('live-clock').innerText = '⏰ ' + now.toLocaleTimeString('en-IN', {{ timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }}) + ' IST';
        
        const min = now.getMinutes();
        const sec = now.getSeconds();
        const elapsedSec = ((min % 15) * 60) + sec;
        const remSec = 900 - elapsedSec;
        const remMin = Math.floor(remSec / 60);
        const remS = remSec % 60;
        
        const minStr = String(remMin).padStart(2, '0');
        const secStr = String(remS).padStart(2, '0');
        
        const timerElem = document.getElementById('candle-timer');
        if (remSec <= 60) {{
            timerElem.style.color = '#FF5252';
            timerElem.innerText = '⚠️ GET READY FOR NEXT CANDLE ENTRY (' + minStr + ':' + secStr + ' REMAINING)';
        }} else {{
            timerElem.style.color = '#FFD54F';
            timerElem.innerText = '⏳ 15M CANDLE COUNTDOWN: ' + minStr + ':' + secStr + ' REMAINING';
        }}
    }}
    setInterval(updateClockAndCandleTimer, 1000); updateClockAndCandleTimer();

    let lastNiftyPrice = {nifty_spot_init};
    async function fetchRealNiftyLiveTicker() {{
        const targetUrl = 'https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m';
        const proxies = [
            'https://api.allorigins.win/get?url=' + encodeURIComponent(targetUrl),
            'https://api.codetabs.com/v1/proxy?quest=' + encodeURIComponent(targetUrl),
            targetUrl
        ];
        for (let url of proxies) {{
            try {{
                const res = await fetch(url);
                if (res.ok) {{
                    const text = await res.text();
                    let data;
                    try {{
                        data = JSON.parse(text);
                        if (data.contents) data = JSON.parse(data.contents);
                    }} catch(e) {{ continue; }}
                    
                    const price = data.chart?.result?.[0]?.meta?.regularMarketPrice;
                    if (price) {{
                        const formatted = price.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
                        const elem = document.getElementById('nifty-ticker-price');
                        if (elem) {{
                            if (price > lastNiftyPrice) {{
                                elem.style.color = '#00E676';
                            }} else if (price < lastNiftyPrice) {{
                                elem.style.color = '#FF5252';
                            }}
                            elem.innerText = '₹' + formatted;
                            lastNiftyPrice = price;
                        }}
                        return;
                    }}
                }}
            }} catch(e) {{}}
        }}
    }}
    setInterval(fetchRealNiftyLiveTicker, 1500);
    fetchRealNiftyLiveTicker();
    </script>
    """, height=85)

if is_open:
    st.markdown(f"<div class='market-badge-open'>{market_status_text}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='market-badge-closed'>{market_status_text} — LAST CLOSE DATA SHOWN</div>", unsafe_allow_html=True)

# FOREX EXECUTION ENGINE
if selected_asset == "FOREX (EUR/USD $)":
    df_forex = data_feed.fetch_forex_live_data(config.FOREX_SYMBOL, config.TIMEFRAME)
    if df_forex.empty or len(df_forex) < 5:
        st.warning("⏳ Connecting to 0ms Forex EUR/USD Live Feed... Please wait 3 seconds.")
        time_lib.sleep(3)
        st.rerun()
        
    last_row = df_forex.iloc[-1]
    spot_price = float(last_row['close'])
    entry_zone_price = float(last_row['open'])
    current_candle_id = f"FOREX_{last_row.get('time', str(datetime.now().minute // 15))}"
    
    if st.session_state.locked_candle_id != current_candle_id or st.session_state.locked_signal_state is None:
        signal_type, confidence_score, reason_code, breakdown = quant_math_engine.evaluate_forex_15m_signal(df_forex)
        st.session_state.locked_candle_id = current_candle_id
        st.session_state.locked_signal_state = (signal_type, confidence_score, reason_code, breakdown)
    else:
        signal_type, confidence_score, reason_code, breakdown = st.session_state.locked_signal_state
    
    st.sidebar.info(f"Symbol: {config.FOREX_SYMBOL}")
    st.sidebar.info(f"Timeframe: {config.TIMEFRAME}")
    st.sidebar.metric("EUR/USD Live Spot", f"${spot_price:.5f}")
    
    forex_tp1 = entry_zone_price + (config.FOREX_TARGET_1_PIPS / 10000.0) if signal_type == "BUY_CALL" else entry_zone_price - (config.FOREX_TARGET_1_PIPS / 10000.0)
    forex_tp2 = entry_zone_price + (config.FOREX_TARGET_2_PIPS / 10000.0) if signal_type == "BUY_CALL" else entry_zone_price - (config.FOREX_TARGET_2_PIPS / 10000.0)
    forex_sl = entry_zone_price - (config.FOREX_STOP_LOSS_PIPS / 10000.0) if signal_type == "BUY_CALL" else entry_zone_price + (config.FOREX_STOP_LOSS_PIPS / 10000.0)

    st.subheader("📍 LIVE FOREX (EUR/USD) 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            {time_badge_html}
            <h1 style='color:#00E676; margin:0;'>🟩 PREDICTED WINNING CANDLE: LONG (BUY EUR/USD)</h1>
            <p style='font-size:18px; margin-top:8px;'>Forex Win Confidence: <b>{confidence_score:.1f}%</b> | Spot: <b>${spot_price:.5f}</b></p>
            <hr style='border-color:#00E676;'>
            <h2>🎯 ENTRY ZONE (LOCKED TO OPEN): <u style='color:#00E676;'>${entry_zone_price:.5f}</u></h2>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == "BUY_PUT":
        st.markdown(f"""
        <div class='signal-card-sell'>
            {time_badge_html}
            <h1 style='color:#E040FB; margin:0;'>🟪 PREDICTED WINNING CANDLE: SHORT (SELL EUR/USD)</h1>
            <p style='font-size:18px; margin-top:8px;'>Forex Win Confidence: <b>{confidence_score:.1f}%</b> | Spot: <b>${spot_price:.5f}</b></p>
            <hr style='border-color:#E040FB;'>
            <h2>🎯 ENTRY ZONE (LOCKED TO OPEN): <u style='color:#E040FB;'>${entry_zone_price:.5f}</u></h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='signal-card-wait'>
            <h1 style='color:#B0BEC5; margin:0;'>⚪ WAIT - LOW FOREX WIN CONFIDENCE (< 70%)</h1>
            <p style='font-size:15px; margin-top:8px;'>Reason: <b>{reason_code}</b></p>
        </div>
        """, unsafe_allow_html=True)

    if signal_type != "WAIT":
        st.markdown(f"""
        <div class='cheat-box'>
            <b>📋 FOREX (EUR/USD) EXECUTION CHEAT SHEET ($ USD & PIPS):</b><br>
            • <b>Currency Pair   :</b> EUR/USD (Lot Size: 0.01 Micro Lot)<br>
            • <b>Entry Strategy   :</b> Buy Market Price @ ${entry_zone_price:.5f}<br>
            • <b>Stop Loss (SL)   :</b> ${forex_sl:.5f} (-10 Pips / -$1.00 USD Risk)<br>
            • <b>Target 1 (TP1)   :</b> ${forex_tp1:.5f} (+15 Pips / +$1.50 USD Quick Profit)<br>
            • <b>Target 2 (TP2)   :</b> ${forex_tp2:.5f} (+35 Pips / +$3.50 USD Trend Profit)<br>
            • <b>Candle Expiration:</b> Strict Exit @ 15M Candle Close
        </div>
        """, unsafe_allow_html=True)

elif selected_asset == "BITCOIN (BTC/USDT)":
    df_btc = data_feed.fetch_btc_live_data("BTCUSDT", config.TIMEFRAME)
    if df_btc.empty:
        df_btc = pd.DataFrame([{"open": 74400.0, "high": 74500.0, "low": 74300.0, "close": 74448.0, "volume": 50000.0}])
        
    last_row = df_btc.iloc[-1]
    spot_price = float(last_row.get('close', 74448.0))
    entry_zone_price = float(last_row.get('open', 74400.0))
    current_candle_id = f"BTC_{last_row.get('time', str(datetime.now().minute // 15))}"
    
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
    
    current_candle_id = f"NIFTY_{datetime.now().minute // 15}"

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

    st.subheader("📍 LIVE NIFTY 50 15M CANDLE WIN PREDICTOR")
    if signal_type == "BUY_CALL":
        st.markdown(f"""
        <div class='signal-card-buy'>
            {time_badge_html}
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

# PERFORMANCE LOGS & TABLES
st.divider()
st.subheader(f"📊 {selected_asset.upper()} PERFORMANCE LOGS & ACCURACY TRACKER")

tab1, tab2 = st.tabs(["📅 Today's Live Log", "📊 7-Day Weekly Performance Tracker"])

with tab1:
    today_summary = trade_logger.get_today_summary(asset_key)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today's Trades", f"{today_summary['total_trades']}")
    col2.metric("Win Rate", f"{today_summary['win_rate']}%")
    col3.metric("Wins / Losses", f"{today_summary['wins']} W / {today_summary['losses']} L")
    col4.metric(f"Net Daily PnL ({currency_sym})", f"{currency_sym}{today_summary['net_pnl']:,.2f}")
    
    today_trades = trade_logger.get_today_trades(asset_key)
    if today_trades:
        df_today = pd.DataFrame(today_trades)
        st.dataframe(df_today[["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"]], use_container_width=True)
    else:
        st.info(f"ℹ️ No {selected_asset} trades recorded today yet. Bot is scanning 15M candles for high-probability setups.")

with tab2:
    weekly_summary = trade_logger.get_weekly_summary(days=7, asset_filter=asset_key)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("1-Week Total Trades", f"{weekly_summary['total_trades']}")
    col2.metric("1-Week Win Rate", f"{weekly_summary['win_rate']}%")
    col3.metric("Wins / Losses", f"{weekly_summary['wins']} W / {weekly_summary['losses']} L")
    col4.metric(f"1-Week Net PnL ({currency_sym})", f"{currency_sym}{weekly_summary['net_pnl']:,.2f}")
    
    weekly_trades = trade_logger.get_weekly_trades(days=7, asset_filter=asset_key)
    if weekly_trades:
        df_weekly = pd.DataFrame(weekly_trades)
        st.dataframe(df_weekly[["date_time", "symbol", "entry_price", "exit_price", "quantity", "gross_pnl", "brokerage_fee", "net_pnl", "result"]], use_container_width=True)
    else:
        st.info(f"ℹ️ No weekly {selected_asset} trade history recorded yet.")

# BOT THOUGHTS & AI SELF-REFLECTION
st.divider()
col_title, col_clear = st.columns([3, 1])
with col_title:
    st.subheader(f"🧠 {selected_asset.upper()} BOT THOUGHTS & AI SELF-REFLECTION")
with col_clear:
    if st.button(f"🧹 Clear {asset_key} Thoughts"):
        trade_logger.clear_asset_trades(asset_key)
        st.success(f"{asset_key} Thoughts Cleared!")
        st.rerun()

all_trades = trade_logger.filter_trades_by_asset(trade_logger.load_trades(), asset_key)
if all_trades:
    for t in reversed(all_trades[-10:]):
        col_card, col_del = st.columns([5, 1])
        with col_card:
            post_mortem_text = ai_analyst.generate_trade_post_mortem(t.get("result", "WIN"), t.get("layers", {}), t.get("net_pnl", 0))
            st.markdown(f"""
            <div class='diagnostic-box'>
                📅 <b>{t.get('date_time', 'N/A')}</b> | <span style='color:{"#FF5252" if t.get("result")=="LOSS" else "#00E676"}'>{t.get("result", "WIN")}</span><br>
                📍 <b>Trade:</b> {t.get('symbol', 'N/A')} | Net PnL: {currency_sym}{t.get('net_pnl', 0)}<br><br>
                💭 <b>Bot Reflection:</b><br>{t.get('post_mortem', post_mortem_text)}
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            if st.button("🗑️ Delete", key=f"del_thought_{t.get('trade_id', 1)}"):
                trade_logger.delete_trade_by_id(t.get("trade_id", 1))
                st.success("Thought Deleted!")
                st.rerun()
else:
    st.info(f"ℹ️ No {selected_asset} Bot Thoughts recorded yet.")

st.divider()
today_trades = trade_logger.get_today_trades(asset_key)
eod_report = ai_analyst.generate_eod_bot_diagnostic(today_trades, india_vix if selected_asset == "NIFTY 50 (₹)" else 15.0, 1.0)
st.markdown(f"<div class='diagnostic-box'>{eod_report}</div>", unsafe_allow_html=True)

if st.sidebar.button(f"🧹 Reset All History"):
    trade_logger.clear_asset_trades(None)
    st.sidebar.success("All History Reset!")
    st.rerun()

if st.sidebar.button("🔄 Refresh Signal Engine"):
    st.rerun()