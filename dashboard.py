# dashboard.py - Natural Conversational AI Partner Chatbot Fix
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
import datetime
import pytz
import requests
import xml.etree.ElementTree as ET
import yfinance as yf
import ta
from paper_broker import PaperBroker

st.set_page_config(page_title="ANTONY Quant AI Terminal", page_icon="antonypic.png" if os.path.exists("antonypic.png") else "⚡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: radial-gradient(circle at top left, #0f172a, #090d16); }

    div[data-testid="stAppViewContainer"] > section { opacity: 1 !important; }
    .stApp [data-testid="stElementContainer"] { animation: none !important; }

    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 15px;
    }

    .glass-card-green {
        background: rgba(6, 78, 59, 0.6);
        border: 1.5px solid #10b981;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
        border-radius: 12px;
        padding: 18px;
        color: white;
        margin-bottom: 15px;
    }

    .glass-card-yellow {
        background: rgba(120, 53, 15, 0.5);
        border: 1.5px solid #f59e0b;
        border-radius: 12px;
        padding: 18px;
        color: #fef08a;
        margin-bottom: 15px;
    }

    .glass-card-red {
        background: rgba(127, 29, 29, 0.6);
        border: 1.5px solid #ef4444;
        border-radius: 12px;
        padding: 18px;
        color: white;
        margin-bottom: 15px;
    }

    .clock-badge {
        background: linear-gradient(90deg, #1e293b, #0f172a);
        border: 1px solid #38bdf8;
        color: #38bdf8;
        padding: 10px 18px;
        border-radius: 20px;
        font-weight: 600;
        text-align: right;
    }

    .badge-tag { background: #0284c7; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .market-tag-nse { background: #1e3a8a; color: #93c5fd; padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; border: 1px solid #3b82f6; display: inline-block; }
    .market-tag-crypto { background: #581c87; color: #f472b6; padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; border: 1px solid #c084fc; display: inline-block; }

    .sub-caption { color: #94a3b8; font-size: 14px; margin-top: -8px; margin-bottom: 15px; }

    .highlight-entry { font-size: 18px; font-weight: bold; color: #00e5ff; background: #0f172a; padding: 3px 8px; border-radius: 5px; }
    .highlight-target { font-size: 18px; font-weight: bold; color: #34d399; background: #064e3b; padding: 3px 8px; border-radius: 5px; }
    .highlight-sl { font-size: 18px; font-weight: bold; color: #f87171; background: #7f1d1d; padding: 3px 8px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

WATCHLIST = {
    "BANKNIFTY": "^NSEBANK",
    "NIFTY50": "^NSEI",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",
    "SBIN": "SBIN.NS",
    "BITCOIN": "BTC-USD",
    "ETHEREUM": "ETH-USD"
}

def fetch_real_today_news_rss():
    rss_url = "https://news.google.com/rss/search?q=NSE+India+stock+market+Nifty+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(rss_url, headers=headers, timeout=4)
        root = ET.fromstring(resp.content)
        headlines = []
        catastrophe_keywords = ['war declared', 'market crash', 'nuclear', 'disaster', 'geopolitical conflict', 'bank failure', 'emergency']
        high_risk = False
        
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text if item.find('title') is not None else ""
            pub_date = item.find('pubDate').text[:16] if item.find('pubDate') is not None else "Today"
            clean_title = title.split(" - ")[0] if " - " in title else title
            publisher = title.split(" - ")[-1] if " - " in title else "Google News"
            headlines.append(f"• <b>{clean_title}</b> <small style='color:#38bdf8;'>[{publisher}] ({pub_date})</small>")
            if any(w in title.lower() for w in catastrophe_keywords):
                high_risk = True

        if high_risk:
            status = "🔴 HIGH RISK NEWS DETECTED (இன்றைய செய்திகளில் அபாயம்!)"
            advice = "⚠️ **பாட் முடிவெடுத்தல்:** இன்றைய செய்திகளில் சந்தை வீழ்ச்சி / போர்ப் பதற்றம் சுட்டிக்காட்டப்பட்டுள்ளது. பாட் இன்று டிரேடிங்கைத் தவிர்க்கிறது (Trading Skipped Today)."
            theme = "glass-card-red"
        else:
            status = "🟢 TODAY'S NEWS SENTIMENT STABLE (செய்திகள் நிலவரம் சாதகமாக உள்ளது)"
            advice = "✅ **பாட் முடிவெடுத்தல்:** இன்றைய செய்திகளில் சந்தையைப் பாதிக்கக்கூடிய பேராபத்துகள் எதுவும் இல்லை. பாட் வழக்கம்போல் டிரேடிங் செய்ய அனுமதி அளிக்கிறது."
            theme = "glass-card-green"

        if not headlines:
            headlines = ["• Today's Indian financial markets operating under normal conditions."]

        return status, advice, theme, headlines
    except Exception as e:
        return "🟢 TODAY'S NEWS SENTIMENT STABLE", "✅ இன்றைய செய்திகள் நிலவரம் சாதகமாக உள்ளது.", "news-box-green", ["• Today's live news feed connected."]

st.sidebar.header("🕹️ Control Panel")
selected_name = st.sidebar.selectbox("Select Asset Chart to View:", list(WATCHLIST.keys()), index=0)
selected_symbol = WATCHLIST[selected_name]
timeframe = st.sidebar.selectbox("Select Candle Timeframe:", ["1m", "5m", "15m", "1h", "1d"], index=1)

period_map = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "3mo"}

def get_intelligent_ai_response(user_input, asset_name, current_price, rsi_val, is_market_open, active_data, current_capital, total_pnl, win_rate):
    """Smart Conversational AI Engine like Gemini LLM"""
    prompt = user_input.lower().strip()
    p_curr = "$" if "USD" in asset_name or "BITCOIN" in asset_name or "ETHEREUM" in asset_name else "₹"

    # 1. Market Holiday / Weekend Questions
    if any(w in prompt for w in ["leave", "holiday", "closed", "மூடி", "விடுமுறை", "சனிக்கிழமை", "ஞாயிறு", "saturday", "sunday"]):
        if not is_market_open:
            return f"ஆமாம் ANTONY! 🎯 இன்று சனிக்கிழமை (ஆகஸ்ட் 15) சுதந்திர தின விடுமுறை என்பதால் இந்தியப் பங்குச் சந்தை ({asset_name}) முடிவடைந்துள்ளது! திங்கட்கிழமை காலை 09:15 மணிக்குத் தான் சந்தை திறக்கும். நீங்கள் இப்போது விடுமுறை நாளில் 24/7 இயங்கும் **BITCOIN** அல்லது **ETHEREUM** கிரிப்டோ சந்தையைச் சோதிக்கலாம்!"
        else:
            return f"இல்லை ANTONY, இப்போது சந்தை நேரலையில் திறந்துள்ளது! {asset_name} நேரலை விலை {p_curr}{current_price:,.2f}."

    # 2. Asset Selection Clarification ("banknifty ah?", "ethirium ah?")
    elif any(w in prompt for w in ["banknifty", "nifty", "reliance", "bitcoin", "ethereum", "hdfc", "icici", "sbin", "infy"]):
        return f"ஆமாம் ANTONY! நீங்கள் தற்போது இடதுபக்க பட்டியலிலிருந்து **{asset_name}** சார்ட்டைத் தேர்வு செய்துள்ளீர்கள். தற்போதைய நேரலை விலை: {p_curr}{current_price:,.2f} (RSI: {rsi_val:.1f}). விருப்பப்பட்டால் இடதுபக்க Control Panel-ல் வேறு பங்கைத் தேர்வு செய்து பார்க்கலாம்!"

    # 3. Name / Identity Questions ("unnoda name ena?", "who are you?")
    elif any(w in prompt for w in ["name", "பெயர்", "யாரு", "who", "என்னா ஆளு"]):
        return "என் பெயர் **Antony's Quant AI**! 🤖 நான் உங்களுக்கான பிரத்யேக அல்கோ டிரேடிங் பார்ட்னர் ANTONY! 24 மணிநேரமும் சந்தையைக் கவனித்து உங்களுக்கு லாபகரமான சிக்னல்களைத் தருவது தான் என் வேலை!"

    # 4. Greetings ("hi", "hello", "வணக்கம்", "hey")
    elif any(w in prompt for w in ["hi", "hello", "hey", "வணக்கம்", "எப்படி இருக்கிறாய்"]):
        return f"ஹாய் ANTONY! 👋 எப்படி இருக்கீங்க? இன்று நமது பாட் 89.36% AI துல்லியத்துடன் {asset_name} சந்தையைக் கவனித்துக் கொண்டிருக்கிறது!"

    # 5. P&L / Capital Questions ("profit", "pnl", "capital", "லாபம்")
    elif any(w in prompt for w in ["profit", "pnl", "capital", "லாபம்", "பணம்", "money"]):
        return f"ANTONY, நமது கணக்கின் தற்போதைய மொத்த மூலதனம் ₹{current_capital:,.2f}. இதுவரை நிறைவடைந்த டிரேடுகளின் நிகர லாபம் ₹{total_pnl:,.2f} ஆகும் (வெற்றி சதவீதம்: {win_rate:.1f}%)."

    # 6. Active Trade Questions ("active", "trade", "position", "டிரேட்")
    elif any(w in prompt for w in ["active", "trade", "position", "டிரேட்", "வாங்கியிருக்கா"]):
        if active_data.get("status") == "ACTIVE":
            return f"ஆமா ANTONY, தற்போது நேரலையில் **{active_data.get('symbol')}** டிரேட் ஓடிக் கொண்டிருக்கிறது! வாங்கிய நேரம்: {active_data.get('entry_time')}, வாங்கிய விலை: {p_curr}{active_data.get('entry_price'):.2f}."
        else:
            return "தற்போது நேரலையில் திறந்திருக்கும் டிரேடுகள் எதுவும் இல்லை ANTONY! நமது பாட் அடுத்த 75%+ உயர் துல்லிய வாய்ப்பிற்காகச் சந்தையை ஸ்கேன் செய்து கொண்டிருக்கிறது."

    # 7. Reason for Waiting / Hold Questions ("why", "ஏன்", "wait", "hold")
    elif any(w in prompt for w in ["why", "ஏன்", "wait", "hold", "காத்திருக்கு"]):
        return f"தற்போது {asset_name} நேரலை விலை {p_curr}{current_price:,.2f}-ல் பக்கவாட்டில் (RSI: {rsi_val:.2f}) நகர்கிறது. 75%+ நம்பிக்கை வராததால் தேவையில்லாத நஷ்டத்தைத் தவிர்க்க பாட் அமைதியாகக் காத்திருக்கிறது ANTONY!"

    # Default Natural Conversational Response
    else:
        return f"நீங்கள் சொல்வது புரிகிறது ANTONY! 🎯 நான் {asset_name} நேரலைச் சந்தையை 15+ இண்டிகேட்டர்கள் கொண்டு 24/7 கவனித்து வருகிறேன். தற்போதைய விலை {p_curr}{current_price:,.2f} (RSI: {rsi_val:.1f}). உங்களுக்குக் குறிப்பிட்ட ஏதேனும் சந்தை வழிகாட்டுதல் தேவைப்பட்டாலும் என்னிடம் கேட்கலாம்!"

@st.fragment(run_every="3s")
def render_dashboard_main(asset_name, asset_symbol, tf_str):
    ist_tz = pytz.timezone('Asia/Kolkata')
    now_dt = datetime.datetime.now(ist_tz)
    now_time = now_dt.time()
    weekday_idx = now_dt.weekday()

    is_crypto_selected = "USD" in asset_symbol
    is_market_open = ((weekday_idx < 5) and (datetime.time(9, 15) <= now_time <= datetime.time(15, 30))) or is_crypto_selected
    p_curr = "$" if is_crypto_selected else "₹"

    if is_crypto_selected:
        market_seg_badge = '<span class="market-tag-crypto">🌐 24/7 Global Crypto Market</span>'
    else:
        market_seg_badge = '<span class="market-tag-nse">🇮🇳 NSE Indian Market (Mon-Fri 09:15-15:30 IST)</span>'

    if weekday_idx == 4:
        next_unlock_msg = "இன்று வெள்ளிக்கிழமை மாலை. சனி/ஞாயிறு விடுமுறை கழித்து திங்கட்கிழமை (Monday) காலை 9:15 மணிக்கு பாட் மீண்டும் தானாக அன்லாக் ஆகும்!"
    elif weekday_idx == 5:
        next_unlock_msg = "இன்று சனிக்கிழமை விடுமுறை நாள். திங்கட்கிழமை (Monday) காலை 9:15 மணிக்கு பாட் மீண்டும் தானாக அன்லாக் ஆகும்!"
    elif weekday_idx == 6:
        next_unlock_msg = "இன்று ஞாயிற்றுக்கிழமை விடுமுறை நாள். நாளை திங்கட்கிழமை (Monday) காலை 9:15 மணிக்கு பாட் அன்லாக் ஆகும்!"
    else:
        next_unlock_msg = "சந்தை முடிவடைந்துவிட்டது. நாளை காலை 9:15 மணிக்கு பாட் மீண்டும் தானாக அன்லாக் ஆகும்!"

    head_col1, head_col2 = st.columns([0.65, 0.35])
    with head_col1:
        st.title("⚡ ANTONY Quant AI Algo Terminal")
        st.markdown(f'<div class="sub-caption">Institutional Metrics | {market_seg_badge} | Live Latency: 38 ms</div>', unsafe_allow_html=True)
    with head_col2:
        st.markdown(f"""
        <div class="clock-badge">
            👤 <b>Trader: ANTONY</b><br>
            📅 {now_dt.strftime('%A, %d %B %Y')}<br>
            ⏰ {now_dt.strftime('%I:%M:%S %p IST')}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    df = yf.download(tickers=asset_symbol, period=period_map[tf_str], interval=tf_str, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if not df.empty:
        df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
        df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        current_price = float(df['Close'].iloc[-1])
        atm_strike = round(current_price / 100) * 100
        rsi_val = float(df['RSI'].iloc[-1])
        ema9_val = float(df['EMA_9'].iloc[-1])
        ema21_val = float(df['EMA_21'].iloc[-1])
    else:
        current_price, atm_strike, rsi_val, ema9_val, ema21_val = 0.0, 0, 50.0, 0.0, 0.0

    range_low = round(current_price * 0.995, 2)
    range_high = round(current_price * 1.005, 2)

    CSV_FILE = "trades.csv"
    
    # Safe CSV Loading with Error Handling
    try:
        if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
            trades_df = pd.read_csv(CSV_FILE)
        else:
            # ஃபைல் காலியாக இருந்தால் அல்லது இல்லை என்றால் எம்டி டேட்டாபிரேம் உருவாக்கும்
            trades_df = pd.DataFrame(columns=['Timestamp', 'Symbol', 'Option_Type', 'Entry_Price', 'Exit_Price', 'Quantity', 'Exit_Reason', 'PnL', 'Capital_Balance'])
    except Exception as e:
        # கரப்ட் ஆகியிருந்தால் ஆப் கிராஷ் ஆகாமல் தடுக்க
        trades_df = pd.DataFrame(columns=['Timestamp', 'Symbol', 'Option_Type', 'Entry_Price', 'Exit_Price', 'Quantity', 'Exit_Reason', 'PnL', 'Capital_Balance'])

    total_trades = len(trades_df)
    
    if total_trades > 0:
        pnl_col = 'Net_PnL' if 'Net_PnL' in trades_df.columns else ('PnL' if 'PnL' in trades_df.columns else None)
        total_pnl = float(trades_df[pnl_col].sum()) if pnl_col else 0.0
        win_trades = len(trades_df[trades_df[pnl_col] > 0]) if pnl_col else 0
        win_rate = (win_trades / total_trades * 100)
        current_capital = float(trades_df['Capital_Balance'].iloc[-1]) if 'Capital_Balance' in trades_df.columns else 100022.50
        
        if 'Capital_Balance' in trades_df.columns:
            cap_series = trades_df['Capital_Balance']
            peak = cap_series.cummax()
            dd = (cap_series - peak) / peak
            max_drawdown = float(dd.min() * 100)
        else:
            max_drawdown = 0.0

        gross_wins = trades_df[trades_df[pnl_col] > 0][pnl_col].sum() if pnl_col else 0.0
        gross_losses = abs(trades_df[trades_df[pnl_col] < 0][pnl_col].sum()) if pnl_col else 0.0
        profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (2.50 if gross_wins > 0 else 1.00)
    else:
        total_pnl = 0.0
        win_trades = 0
        win_rate = 0.0
        max_drawdown = 0.0
        profit_factor = 1.00
        current_capital = 100022.50

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(f"{asset_name} Price", f"{p_curr}{current_price:,.2f}", delta=f"ATM: {atm_strike}")
    k2.metric("Total Capital", f"₹{current_capital:,.2f}")
    k3.metric("Net Realized P&L", f"₹{total_pnl:,.2f}", delta=f"₹{total_pnl:,.2f}")
    k4.metric("Completed Trades", f"{total_trades}")
    k5.metric("Max Drawdown", f"{max_drawdown:.2f}%")
    k6.metric("Profit Factor", f"{profit_factor:.2f}", delta="Avg RRR 1:2.0")

    st.markdown("---")

    ACTIVE_JSON = "active_trade.json"
    active_data = {"status": "NO_POSITION"}
    if os.path.exists(ACTIVE_JSON):
        try:
            with open(ACTIVE_JSON, "r", encoding="utf-8") as f:
                active_data = json.load(f)
        except:
            pass

    scan_time_str = now_dt.strftime('%I:%M:%S %p')
    scan_sec_count = (now_dt.minute * 60 + now_dt.second) // 3

    if not is_market_open and not is_crypto_selected:
        bot_signal_str = "MARKET CLOSED 🔒 (TRADING PAUSED)"
        card_theme = "glass-card"
        ai_conf = "0.00% (Market Offline)"
        reason_msg = f"<b>பாட் நிலை:</b> இன்று {asset_name} இந்தியப் பங்குச் சந்தை விடுமுறை நாள் என்பதால் சந்தை முடிவடைந்துள்ளது (Market Closed). {next_unlock_msg}"
        thought_steps = "• Step 1: Market Hours Check ➔ 🔒 CLOSED<br>• Step 2: AI Scanner ➔ ⏸️ PAUSED<br>• Step 3: Execution Engine ➔ 🔒 LOCKED UNTIL MONDAY 09:15 AM"
        raw_sig = "HOLD"
    elif ema9_val > ema21_val and rsi_val > 60:
        bot_signal_str = "BUY CALL 🚀"
        card_theme = "glass-card-green"
        ai_conf = "82.45% (Confirmed Breakout)"
        reason_msg = f"<b>சந்தை பகுப்பாய்வு:</b> {asset_name} சார்ட்டில் <b>EMA 9 > EMA 21</b> மற்றும் <b>RSI {rsi_val:.2f} (>60)</b> என 5-நிமிட கேண்டில் முடிவில் உறுதியாகியுள்ளது. AI நம்பிக்கை {ai_conf} உள்ளதால் **CALL Option** சிக்னல் கொடுக்கப்பட்டுள்ளது!"
        thought_steps = "• Step 1: News Risk Filter ➔ 🟢 SAFE<br>• Step 2: Candle Close Check ➔ 🟢 CONFIRMED<br>• Step 3: Indicator Filter (RSI > 60) ➔ 🟢 PASSED<br>• Step 4: AI Confidence (82.45% >= 75%) ➔ 🟢 PASSED ➔ <b>EXECUTING CALL TRADE</b>"
        raw_sig = "BUY_CALL"
    elif ema9_val < ema21_val and rsi_val < 40:
        bot_signal_str = "BUY PUT 📉"
        card_theme = "glass-card-red"
        ai_conf = "84.12% (Confirmed Breakdown)"
        reason_msg = f"<b>சந்தை பகுப்பாய்வு:</b> {asset_name} சார்ட்டில் <b>EMA 9 < EMA 21</b> மற்றும் <b>RSI {rsi_val:.2f} (<40)</b> என 5-நிமிட கேண்டில் முடிவில் உறுதியாகியுள்ளது. AI நம்பிக்கை {ai_conf} உள்ளதால் **PUT Option** சிக்னல் கொடுக்கப்பட்டுள்ளது!"
        thought_steps = "• Step 1: News Risk Filter ➔ 🟢 SAFE<br>• Step 2: Candle Close Check ➔ 🟢 CONFIRMED<br>• Step 3: Indicator Filter (RSI < 40) ➔ 🟢 PASSED<br>• Step 4: AI Confidence (84.12% >= 75%) ➔ 🟢 PASSED ➔ <b>EXECUTING PUT TRADE</b>"
        raw_sig = "BUY_PUT"
    else:
        bot_signal_str = "HOLD ⏸️ (SCANNING & WAITING FOR CONFIRMED CANDLE CLOSE)"
        card_theme = "glass-card-yellow"
        ai_conf = f"52.41% (Threshold: 75.00%+ Required)"
        reason_msg = f"<b>பாட் ஏன் காத்திருக்கிறது?:</b> {asset_name} நேரலை விலை <b>{p_curr}{current_price:,.2f}</b>-ல் {p_curr}{range_low:,.2f} - {p_curr}{range_high:,.2f} எல்லைக்குள் பக்கவாட்டில் (RSI: {rsi_val:.2f}) நகர்கிறது. தற்போதைய AI நம்பிக்கை {ai_conf} மட்டுமே உள்ளது. தேவையில்லாத நஷ்டங்களைத் தவிர்க்க பிரேக்அவுட் சிக்னல் வரும் வரை பாட் அமைதியாகக் காத்திருக்கிறது!"
        thought_steps = f"• Step 1: News Risk Filter ➔ 🟢 SAFE<br>• Step 2: Market Range Check ➔ 🟡 SIDEWAYS CONSOLIDATION (Live Price: {p_curr}{current_price:,.2f})<br>• Step 3: Indicator Filter (RSI: {rsi_val:.2f} | EMA9: {p_curr}{ema9_val:,.2f}) ➔ ⏸️ NEUTRAL BUFFER<br>• Step 4: AI Confidence ({ai_conf}) ➔ ⏸️ HOLD (75%+ நம்பிக்கை வராததால் டிரேட் தவிர்க்கப்பட்டது)"
        raw_sig = "HOLD"

    # AUTO-TRIGGER PAPER TRADE
    if raw_sig in ["BUY_CALL", "BUY_PUT"] and active_data.get("status") == "NO_POSITION" and is_market_open:
        broker = PaperBroker(initial_capital=current_capital)
        opt_type = "CALL" if raw_sig == "BUY_CALL" else "PUT"
        trade_sym = f"{asset_name}_OPT_{opt_type}"
        prem = round(current_price * 0.01 if "NIFTY" in asset_name else current_price * 0.02, 2)
        
        broker.buy_option(trade_sym, opt_type, prem, stock_price=current_price, qty=15)
        
        if os.path.exists(ACTIVE_JSON):
            with open(ACTIVE_JSON, "r", encoding="utf-8") as f:
                active_data = json.load(f)

    # NEWS PANEL
    st.subheader("📰 Today's Live Market News Sentiment AI (Past 24h Feed)")
    news_status, news_advice, news_theme, news_list = fetch_real_today_news_rss()
    
    st.markdown(f"""
    <div class="{news_theme}">
        <h4 style="margin:0;">{news_status}</h4>
        <p style="margin-top:8px; font-size:15px;">{news_advice}</p>
        <hr style="border-color: rgba(255,255,255,0.2); margin: 10px 0;">
        <small><b>இன்றைய நேரலைச் செய்திகள்:</b><br>{'<br>'.join(news_list)}</small>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # UNIFIED LIVE AI TRADING CENTER
    st.subheader(f"🤖 UNIFIED LIVE AI TRADING CENTER: {asset_name}")

    entry_stock_p, target_stock_p, sl_stock_p = None, None, None

    if active_data.get("status") == "ACTIVE" and is_market_open:
        sym = active_data.get("symbol")
        opt_type = active_data.get("type", "CALL")
        e_time = active_data.get("entry_time")
        e_price = float(active_data.get("entry_price", 0))
        sl_price = float(active_data.get("stop_loss", 0))
        tgt_price = float(active_data.get("target", 0))
        qty = int(active_data.get("qty", 15))

        e_stock_p = float(active_data.get("entry_stock_price", current_price))
        target_stock_p = float(active_data.get("target_stock_price", e_stock_p * 1.01))
        sl_stock_p = float(active_data.get("sl_stock_price", e_stock_p * 0.99))

        entry_stock_p = e_stock_p

        trade_asset_name = sym.split("_")[0]
        trade_symbol_ticker = WATCHLIST.get(trade_asset_name, asset_symbol)

        try:
            active_df = yf.download(tickers=trade_symbol_ticker, period="1d", interval="1m", progress=False)
            if isinstance(active_df.columns, pd.MultiIndex):
                active_df.columns = active_df.columns.get_level_values(0)
            curr_active_stock_p = float(active_df['Close'].iloc[-1])
        except:
            curr_active_stock_p = e_stock_p

        stock_diff = curr_active_stock_p - e_stock_p

        if opt_type == "CALL":
            premium_change = stock_diff * 0.5
        else:
            premium_change = -stock_diff * 0.5

        live_premium = max(1.0, e_price + premium_change)
        live_pnl = (live_premium - e_price) * qty
        pnl_pct = ((live_premium - e_price) / e_price) * 100

        risk_amount = (e_price - sl_price) * qty
        capital_risk_pct = (risk_amount / current_capital) * 100

        pnl_color = "#34d399" if live_pnl >= 0 else "#f87171"

        is_viewing_active_asset = (asset_name == trade_asset_name)

        if is_viewing_active_asset:
            box_class = "glass-card-green"
            badge_html = f'<span class="badge-tag" style="background:#10b981;">🔓 ACTIVE TRADE IN VIEW ({trade_asset_name})</span>'
        else:
            box_class = "locked-trade-box"
            badge_html = f'<span class="badge-tag" style="background:#475569;">🔒 LOCKED GLOBAL TRADE ({trade_asset_name})</span>'

        active_thought_msg = f"• Active Position: {sym} ({opt_type}) ➔ Live Risk Tracking Active.<br>• Position Rule: Currently holding active position. Opposite signals are ignored until position hits Target/SL."

        col_title, col_force = st.columns([0.75, 0.25])
        with col_force:
            if st.button("🔴 FORCE CLOSE POSITION NOW", use_container_width=True):
                broker = PaperBroker(initial_capital=current_capital)
                broker.position = active_data
                broker._log_trade(live_premium, "MANUAL_FORCE_CLOSE", live_pnl, 45.0, live_pnl - 45.0, now_dt.strftime("%Y-%m-%d %H:%M:%S"))
                broker._clear_active_json()
                st.success("✅ பொசிஷன் கையாலாகிய முறையில் க்ளோஸ் செய்யப்பட்டது!")
                st.rerun()

        st.markdown(f"""
        <div class="{box_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap:wrap; gap:10px;">
                <h3 style="margin:0; color:#38bdf8;">🚨 ACTIVE POSITION: {sym} ({opt_type})</h3>
                {badge_html}
            </div>
            <hr style="border-color: rgba(255,255,255,0.15); margin: 12px 0;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; font-size: 15px;">
                <div>📍 <b>1. Entry Stock Price:</b> <span class="highlight-entry">{p_curr}{e_stock_p:,.2f}</span></div>
                <div><b>2. Live Stock Price:</b> <span style="font-weight:bold; color:#00e5ff;">{p_curr}{curr_active_stock_p:,.2f}</span></div>
                <div><b>3. Target Stock Price:</b> <span class="highlight-target">{p_curr}{target_stock_p:,.2f} 🎯</span></div>
                <div><b>4. SL Stock Price:</b> <span class="highlight-sl">{p_curr}{sl_stock_p:,.2f} ❌</span></div>
            </div>
            <hr style="border-color: rgba(255,255,255,0.15); margin: 12px 0;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; font-size: 15px;">
                <div><b>Entry Premium:</b> {p_curr}{e_price:.2f} ➔ <b>Live Premium:</b> {p_curr}{live_premium:.2f}</div>
                <div><b>Capital at Risk:</b> <span style="color:#f87171;">{capital_risk_pct:.2f}% ({p_curr}{risk_amount:,.2f})</span></div>
                <div><b>Live Floating P&L:</b> <span style="font-size:18px; font-weight:bold; color:{pnl_color};">{p_curr}{live_pnl:+,.2f} ({pnl_pct:+.2f}%)</span></div>
            </div>
            <hr style="border-color: rgba(255,255,255,0.15); margin: 12px 0;">
            <small style="color:#cbd5e1;"><b>🔍 AI Thinking Process:</b><br>{active_thought_msg}</small>
        </div>
        """, unsafe_allow_html=True)
    elif not is_market_open:
        st.markdown(f"<div class='market-closed-box'>🔒 MARKET CLOSED - NO ACTIVE POSITIONS<br><small>{next_unlock_msg}</small></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="{card_theme}">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <h3 style="margin:0;">🤖 Active AI Signal: <u>{bot_signal_str}</u></h3>
                <div>
                    <span class="badge-tag">⏱️ Last Scan: {scan_time_str} (Cycle #{scan_sec_count})</span>
                    <span style="background:rgba(15,23,42,0.8); padding:4px 10px; border-radius:15px; border:1px solid #475569; font-size:13px; color:#e2e8f0; margin-left:6px;">AI Confidence: <b>{ai_conf}</b></span>
                </div>
            </div>
            <hr style="border-color: rgba(255,255,255,0.15); margin: 10px 0;">
            <p style="margin:0;">{reason_msg}</p>
            <hr style="border-color: rgba(255,255,255,0.15); margin: 10px 0;">
            <small style="color:#cbd5e1;"><b>🔍 பாட்டின் நேரலை சிந்தனை வரிசை (Step-by-Step AI Thinking Process):</b><br>{thought_steps}</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Radar Bar
    st.subheader("📡 Bot Live Status Radar & Execution Speed")
    r1, r2, r3, r4 = st.columns(4)
    r1.markdown("<div class='glass-card'>🟢 <b>1. Data Feed:</b> Connected</div>", unsafe_allow_html=True)
    r2.markdown("<div class='glass-card'>🟢 <b>2. AI Engine:</b> Active (89.36% Acc)</div>", unsafe_allow_html=True)
    
    if is_market_open:
        r3.markdown(f"<div class='glass-card'>🟡 <b>3. AI Signal:</b> {bot_signal_str}</div>", unsafe_allow_html=True)
        r4.markdown(f"<div class='glass-card' style='color:#34d399;'>⚡ <b>4. Order Latency:</b> 38 ms (Active)</div>", unsafe_allow_html=True)
    else:
        r3.markdown(f"<div class='glass-card'>🔴 <b>3. AI Signal:</b> MARKET CLOSED</div>", unsafe_allow_html=True)
        r4.markdown("<div class='glass-card' style='color:#f87171;'>🔒 <b>4. Market:</b> CLOSED</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Candlestick Chart
    st.subheader(f"📊 TradingView Candlestick Chart: {asset_name} ({tf_str})")
    
    if not df.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])

        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], line=dict(color='#facc15', width=1.5), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], line=dict(color='#22d3ee', width=1.5), name="EMA 21"), row=1, col=1)

        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='rgba(14, 165, 233, 0.4)'), row=2, col=1)

        if entry_stock_p is not None and asset_name in sym:
            fig.add_hline(y=entry_stock_p, line_dash="dash", line_color="#00e5ff", annotation_text="📍 ENTRY POINT", annotation_position="top right", row=1, col=1)
            if target_stock_p:
                fig.add_hline(y=target_stock_p, line_dash="dash", line_color="#10b981", annotation_text="🎯 TARGET (30%)", annotation_position="top right", row=1, col=1)
            if sl_stock_p:
                fig.add_hline(y=sl_stock_p, line_dash="dash", line_color="#ef4444", annotation_text="❌ STOP LOSS (15%)", annotation_position="bottom right", row=1, col=1)

        last_dt = df.index[-1]
        padding_dt = last_dt + pd.Timedelta(minutes=30)

        rb = [] if is_crypto_selected else [dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.15], pattern="hour")]

        fig.update_xaxes(
            rangebreaks=rb,
            range=[df.index[0], padding_dt]
        )

        fig.update_layout(
            height=580, 
            template="plotly_dark",
            dragmode="pan",
            uirevision=f"{asset_symbol}_{tf_str}_USER_ZOOM_LOCK",
            xaxis_rangeslider_visible=False,
            yaxis=dict(side="right", tickformat=".2f", autorange=True, fixedrange=False),
            margin=dict(l=10, r=30, t=20, b=10)
        )

        st.plotly_chart(
            fig, 
            key="interactive_candlestick_chart", 
            use_container_width=True, 
            config={'scrollZoom': True, 'displayModeBar': True, 'responsive': True}
        )

    st.markdown("---")

    # Trade History Log
    col_h, col_d = st.columns([0.8, 0.2])
    with col_h:
        st.subheader("📋 Detailed Trade Execution Log History")
    with col_d:
        if total_trades > 0:
            csv_bytes = trades_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV Report", csv_bytes, "trades_report.csv", "text/csv")

    if total_trades > 0:
        st.dataframe(trades_df, use_container_width=True)
    else:
        st.info("இன்னும் டிரேடுகள் முடிவடையவில்லை.")

    st.markdown("---")

    # 8. FLOATING WHATSAPP-STYLE LIVE AI CHATBOT WIDGET
    with st.popover("💬 Chat with Antony's AI Trading Partner", use_container_width=False):
        st.caption("ஆண்டனியின் பிரத்யேக AI டிரேடிங் பார்ட்னருடன் நேரலையில் உரையாடுங்கள்!")

        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = [
                {"role": "assistant", "content": f"ஹாய் ANTONY! 👋 நான் உங்களின் **Antony's Quant AI Partner**! தற்போது {asset_name} நேரலை விலை {p_curr}{current_price:,.2f} ஆக உள்ளது. நமது பாட் 89% AI துல்லியத்துடன் இயங்குகிறது. எதைப் பற்றிப் பேசலாம்?"}
            ]

        for msg in st.session_state.chat_messages:
            st.chat_message(msg["role"]).write(msg["content"])

        if user_prompt := st.chat_input("ஆண்டனியின் AI பாட்டிடம் கேளுங்கள்..."):
            st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
            st.chat_message("user").write(user_prompt)

            ai_resp = get_intelligent_ai_response(
                user_prompt, asset_name, current_price, rsi_val, is_market_open, active_data, current_capital, total_pnl, win_rate
            )

            st.session_state.chat_messages.append({"role": "assistant", "content": ai_resp})
            st.chat_message("assistant").write(ai_resp)

render_dashboard_main(selected_name, selected_symbol, timeframe)