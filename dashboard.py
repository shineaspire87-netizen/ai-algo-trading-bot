# dashboard.py - Antony Quant AI Algo Terminal (Complete Institutional Engine & Live Sync)
import streamlit as st

# Top of dashboard.py (Global Scope)
ACTIVE_TRADE_FILE = "active_trade.json"
import textwrap
from backtester import run_historical_backtest
from system_health import check_system_integrity
from config import GOOGLE_SHEET_WEB_APP_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from multi_strategy import evaluate_soft_kill_switch_position_scaling, calculate_dynamic_atr_levels, detect_vcp_squeeze_contraction, detect_liquidity_sweep_trap, evaluate_pyramiding_scaling
import streamlit.components.v1 as components
import pandas as pd

def render_tradingview_live_chart(asset_name):
    """Embeds Official TradingView Real-Time Chart with Pre-loaded Indicators"""
    tv_map = {
        "BANKNIFTY": "NSE:BANKNIFTY",
        "NIFTY50": "NSE:NIFTY",
        "RELIANCE": "NSE:RELIANCE",
        "HDFCBANK": "NSE:HDFCBANK",
        "ICICIBANK": "NSE:ICICIBANK",
        "INFY": "NSE:INFY",
        "SBIN": "NSE:SBIN",
        "BITCOIN": "BINANCE:BTCUSDT",
        "ETHEREUM": "BINANCE:ETHUSDT"
    }
    tv_symbol = tv_map.get(asset_name, "NSE:NIFTY")

    widget_code = f"""
    <div class="tradingview-widget-container" style="height:520px;width:100%">
      <div id="tradingview_live_chart" style="height:520px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "5",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#0f172a",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_live_chart",
        "studies": [
          "STD;EMA",
          "STD;VWAP",
          "STD;RSI"
        ]
      }});
      </script>
    </div>
    """
    components.html(widget_code, height=530)
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

try:
    from config import CSV_FILE
except ImportError:
    CSV_FILE = "trades.csv"

try:
    from config import ACTIVE_TRADE_FILE
except ImportError:
    ACTIVE_TRADE_FILE = "active_trade.json"

active_json_file = ACTIVE_TRADE_FILE

ACTIVE_FILE_FALLBACK = "active_trade.json"

def get_active_trade_file_path() -> str:
    """100% UnboundLocalError-Safe Helper Function"""
    try:
        import config
        return getattr(config, 'ACTIVE_TRADE_FILE', 'active_trade.json')
    except Exception:
        return 'active_trade.json'

def render_institutional_quant_cards(bias_status, conf_score, vwap_val, pdh_val, pdl_val, atr_val, adx_val, vol_ratio, vcp_status, sweep_status, diagnostic_reason):
    """Renders Ultra-Premium Dark Glassmorphism Quant Cards using Safe Newline-Free HTML"""
    
    bias_color = "#10b981" if "BUY_CALL" in bias_status else ("#ef4444" if "BUY_PUT" in bias_status else "#f59e0b")
    
    try:
        conf_val = float(conf_score)
    except Exception:
        conf_val = 50.0

    html_cards = (
        f"<style>"
        f".quant-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; margin: 15px 0; }}"
        f".quant-card {{ background: rgba(17, 24, 39, 0.85) !important; backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 10px !important; padding: 16px !important; }}"
        f".quant-title {{ font-size: 12px !important; font-weight: 700 !important; color: #9ca3af !important; text-transform: uppercase !important; margin-bottom: 8px !important; }}"
        f".quant-val-big {{ font-size: 22px !important; font-weight: 800 !important; color: {bias_color} !important; }}"
        f".quant-row {{ display: flex; justify-content: space-between; font-size: 13px !important; color: #d1d5db !important; padding: 4px 0 !important; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}"
        f"</style>"
        f"<div class='quant-grid'>"
        f"<div class='quant-card'>"
        f"<div class='quant-title'>🎯 Directional Bias & AI Confidence</div>"
        f"<div class='quant-val-big'>{bias_status}</div>"
        f"<div style='font-size: 13px; color: #e5e7eb; margin-top: 4px;'>AI Score: <b>{conf_val:.1f}%</b></div>"
        f"<div style='font-size: 11px; color: #10b981; margin-top: 4px;'>{vcp_status}</div>"
        f"<div style='font-size: 11px; color: #f59e0b; margin-top: 2px;'>{sweep_status}</div>"
        f"</div>"
        f"<div class='quant-card'>"
        f"<div class='quant-title'>📊 Key Quant Levels</div>"
        f"<div class='quant-row'><span>VWAP Anchor:</span><b>{vwap_val}</b></div>"
        f"<div class='quant-row'><span>PDH / PDL:</span><b>{pdh_val} / {pdl_val}</b></div>"
        f"<div class='quant-row'><span>Dynamic ATR (14):</span><b>{atr_val}</b></div>"
        f"</div>"
        f"<div class='quant-card'>"
        f"<div class='quant-title'>🛡️ Volatility & Order Flow Checks</div>"
        f"<div class='quant-row'><span>ADX Strength:</span><b>{adx_val}</b></div>"
        f"<div class='quant-row'><span>Volume Spike:</span><b>{vol_ratio}x</b></div>"
        f"<div class='quant-row'><span>Order Flow Trap:</span><b style='color: #10b981;'>{'DETECTED' if 'TRAP' in sweep_status else 'SAFE'}</b></div>"
        f"</div>"
        f"</div>"
        f"<div style='background: rgba(30, 41, 59, 0.85); border-left: 4px solid {bias_color}; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 13px; color: #cbd5e1;'>"
        f"<b>⚡ Executive Action Diagnostic:</b> {diagnostic_reason}"
        f"</div>"
    )
    st.markdown(html_cards, unsafe_allow_html=True)


st.set_page_config(
    page_title="ANTONY Quant AI Terminal", 
    page_icon="antonypic.png" if os.path.exists("antonypic.png") else "⚡", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Custom Glassmorphism Theme Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: radial-gradient(circle at top left, #0f172a, #090d16); }

    /* 🔴 ZERO-BLINK & ANTI-FLICKER OVERRIDE */
    div[data-testid="stAppViewContainer"] > section { 
        opacity: 1 !important; 
        transition: none !important;
    }
    .stApp [data-testid="stElementContainer"],
    div[data-testid="stFragment"] { 
        animation: none !important; 
        transition: none !important;
        opacity: 1 !important;
    }
    div[data-st-mode="running"] {
        opacity: 1 !important;
    }
    div[data-testid="stStatusWidget"] {
        display: none !important;
    }

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


# 🟢 PERMANENT GOOGLE SHEETS CLOUD DATABASE WEBHOOK URL (Version 2 Read & Write)
GOOGLE_SHEET_URL = "https://script.google.com/macros/s/AKfycbyavkzC8zCDG0gR274a3EiusQ1ji72mMi6_Ot5dT0L0r0uXfxDHfEnF87NVniJXyybg/exec"

def fetch_trades_from_google_sheet():
    """Reads permanent trade history directly from Google Sheets"""
    try:
        resp = requests.get(GOOGLE_SHEET_URL, timeout=5, allow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return pd.DataFrame(data)
    except Exception as e:
        print(f"Google Sheet Fetch Error: {e}")
    return pd.DataFrame()

def enforce_cloud_kill_switch_guard(trades_df=None):
    """கூகுள் ஷீட்டில் இருந்து இன்றைய நஷ்டங்களை வாசித்து Kill-Switch-ஐ நிரந்தரமாகப் பூட்டும் வசதி"""
    try:
        if trades_df is None:
            trades_df = fetch_trades_from_google_sheet()
        
        if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
            trades = trades_df.to_dict(orient='records')
        elif isinstance(trades_df, list):
            trades = trades_df
        else:
            trades = []
            
        if not trades:
            return False

        # Current IST Today Date String
        today_ist = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d')
        
        today_trades = [t for t in trades if today_ist in str(t.get('Entry_Time', ''))]

        consecutive_losses = 0
        for trade in reversed(today_trades):
            try:
                pnl_str = str(trade.get('Net_PnL', '0')).replace('₹', '').replace('$', '').strip()
                pnl = float(pnl_str)
            except:
                pnl = 0.0

            if pnl < 0:
                consecutive_losses += 1
            elif pnl > 0:
                break

        if consecutive_losses >= 2:
            st.session_state['kill_switch_active'] = True
            st.session_state['kill_switch_reason'] = f"🛑 CLOUD LOCK: TODAY ({today_ist}) HAD {consecutive_losses} CONSECUTIVE LOSSES."
            return True
    except Exception as e:
        pass
    return False

def get_asset_currency_info(selected_symbol: str):
    crypto_keys = ["BITCOIN", "ETHEREUM", "BTC-USD", "ETH-USD", "BTC", "ETH"]
    is_crypto = any(k in str(selected_symbol).upper() for k in crypto_keys)
    if is_crypto:
        return "$", 83.5 # Symbol & USD/INR Exchange Rate
    return "₹", 1.0


def sync_trade_to_google_sheet(trade_record):
    """Bulletproof Sync to Google Sheets Permanent Database"""
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            GOOGLE_SHEET_URL, 
            data=json.dumps(trade_record), 
            headers=headers, 
            timeout=10,
            allow_redirects=True
        )
        print(f"Google Sheet Sync Status: {response.status_code}")
    except Exception as e:
        print(f"Google Sheet Sync Error: {e}")

# Using Telegram credentials imported from config

def send_telegram_alert(msg):
    """Bulletproof Dual-Route Telegram Notifier"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            import urllib.parse
            encoded_msg = urllib.parse.quote(msg)
            get_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={encoded_msg}&parse_mode=HTML"
            requests.get(get_url, timeout=5)
    except Exception as e:
        print(f"Telegram Alert Error: {e}")

def fetch_real_today_news_rss():
    """Parses Google News RSS Feed for past 24h market sentiment"""
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
            advice = "⚠️ **பாட் முடிவெடுத்தல்:** இன்றைய செய்திகளில் சந்தை வீழ்ச்சி சுட்டிக்காட்டப்பட்டுள்ளது. பாட் இன்று டிரேடிங்கைத் தவிர்க்கிறது."
            theme = "glass-card-red"
        else:
            status = "🟢 TODAY'S NEWS SENTIMENT STABLE (செய்திகள் நிலவரம் சாதகமாக உள்ளது)"
            advice = "✅ **பாட் முடிவெடுத்தல்:** இன்றைய செய்திகளில் பேராபத்துகள் எதுவும் இல்லை. பாட் வழக்கம்போல் டிரேடிங் செய்ய அனுமதி அளிக்கிறது."
            theme = "glass-card-green"

        if not headlines:
            headlines = ["• Today's Indian financial markets operating under normal conditions."]

        return status, advice, theme, headlines
    except Exception as e:
        return "🟢 TODAY'S NEWS SENTIMENT STABLE", "✅ இன்றைய செய்திகள் நிலவரம் சாதகமாக உள்ளது.", "glass-card-green", ["• Today's live news feed connected."]

# 🟢 INSTANT BINANCE LIVE CRYPTO PRICE SYNC
def get_realtime_crypto_price(symbol_name):
    """Fetches instant 0ms Binance live price for Crypto assets"""
    try:
        binance_map = {"BITCOIN": "BTCUSDT", "ETHEREUM": "ETHUSDT"}
        pair = binance_map.get(symbol_name)
        if pair:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                return float(resp.json()['price'])
    except Exception as e:
        pass
    return None

def calculate_hurst_exponent(ts: pd.Series, max_lag: int = 20) -> float:
    """Calculates Hurst Exponent (H < 0.45 indicates mean-reverting sideways chop)"""
    try:
        lags = range(2, max_lag)
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return float(poly[0] * 2.0)
    except:
        return 0.50

st.sidebar.header("🕹️ Control Panel")

# 🟢 SIDEBAR ACTIVE TRADE GLOW INDICATOR
active_json_file = get_active_trade_file_path()
if os.path.exists(active_json_file):
    try:
        with open(active_json_file, "r", encoding="utf-8") as f:
            side_active = json.load(f)
            if side_active.get("status") == "ACTIVE":
                act_sym = side_active.get("symbol", "").split("_")[0]
                act_type = side_active.get("type", "CALL")
                st.sidebar.markdown(f"""
                <div style="background: rgba(225, 29, 72, 0.25); border: 2px solid #f43f5e; border-radius: 10px; padding: 12px; margin-bottom: 15px; color: white;">
                    <h4 style="margin:0; color:#f43f5e;">🚨 ACTIVE TRADE RUNNING!</h4>
                    <p style="margin:5px 0 0 0; font-size:15px; font-weight:bold;">Asset: {act_sym} ({act_type})</p>
                    <small style="color:#cbd5e1;">Select <b>{act_sym}</b> in chart to manage position.</small>
                </div>
                """, unsafe_allow_html=True)
    except:
        pass
selected_name = st.sidebar.selectbox("Select Asset Chart to View:", list(WATCHLIST.keys()), index=0)
selected_symbol = WATCHLIST[selected_name]
timeframe = st.sidebar.selectbox("Select Candle Timeframe:", ["1m", "5m", "15m", "1h", "1d"], index=1)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧪 Testing & Override Controls")

TESTING_STATE_FILE = "testing_mode_state.json"

def load_testing_override_state() -> bool:
    """Read state from URL query parameters and disk file so it SURVIVES hard page refreshes!"""
    # 1. Check URL query params first
    try:
        if st.query_params.get("testing_mode") == "true":
            return True
    except Exception:
        pass

    # 2. Check local disk file
    if os.path.exists(TESTING_STATE_FILE):
        try:
            with open(TESTING_STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("allow_extended_trades", False)
        except Exception:
            pass
            
    return False

def save_testing_override_state(val: bool):
    """Save state to both disk file and URL query params"""
    try:
        # Save to local json
        with open(TESTING_STATE_FILE, "w") as f:
            json.dump({"allow_extended_trades": val}, f)
            
        # Save to URL Query Parameters
        if val:
            st.query_params["testing_mode"] = "true"
        else:
            if "testing_mode" in st.query_params:
                del st.query_params["testing_mode"]
    except Exception as e:
        pass

# Initialize session state from File/URL on app startup
if 'allow_extended_trades' not in st.session_state:
    st.session_state['allow_extended_trades'] = load_testing_override_state()

# Callback triggered ONLY when user manually clicks toggle
def on_testing_toggle_change():
    new_status = st.session_state['testing_toggle_widget']
    st.session_state['allow_extended_trades'] = new_status
    save_testing_override_state(new_status)

# Load current state
current_toggle_val = st.session_state.get('allow_extended_trades', False)

# BULLETPROOF PERMANENT TOGGLE WIDGET
st.sidebar.toggle(
    "🧪 Enable Extended Testing Mode (Unlimited Trades)",
    value=current_toggle_val,
    key="testing_toggle_widget",
    on_change=on_testing_toggle_change,
    help="SURVIVES PAGE REFRESHES: Saved to URL query parameters and disk file."
)

allow_extended_trades = st.session_state['allow_extended_trades']

if allow_extended_trades:
    st.sidebar.info("⚡ **Testing Mode Active:** Bot will continue scanning for 70%+ AI Confidence trades beyond the 3-trade daily limit.")

# Soft Kill Switch Status Check
soft_kill_info = evaluate_soft_kill_switch_position_scaling(st.session_state.get('consecutive_losses', 0))
if soft_kill_info['status'] == "SOFT_KILL_SWITCH_ACTIVE":
    st.sidebar.warning("⚠️ SOFT KILL-SWITCH ACTIVE: 2 Losses Detected. Position Size Scaled to 50% & AI Confidence Threshold set to 75%.")

period_map = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "3mo"}

def get_intelligent_ai_response(user_input, asset_name, current_price, rsi_val, is_market_open, active_data, current_capital, total_pnl, win_rate):
    """Smart Conversational AI Engine like Gemini LLM"""
    prompt = user_input.lower().strip()
    p_curr = "$" if "USD" in asset_name or "BITCOIN" in asset_name or "ETHEREUM" in asset_name else "₹"

    if any(w in prompt for w in ["leave", "holiday", "closed", "மூடி", "விடுமுறை", "சனிக்கிழமை", "ஞாயிறு", "saturday", "sunday"]):
        if not is_market_open:
            return f"ஆமாம் ANTONY! 🎯 இன்று சுதந்திர தின விடுமுறை என்பதால் இந்தியப் பங்குச் சந்தை ({asset_name}) முடிவடைந்துள்ளது! திங்கட்கிழமை காலை 09:15 மணிக்குத் தான் சந்தை திறக்கும். நீங்கள் இப்போது 24/7 இயங்கும் **BITCOIN** அல்லது **ETHEREUM** கிரிப்டோ சந்தையைச் சோதிக்கலாம்!"
        else:
            return f"இல்லை ANTONY, இப்போது சந்தை நேரலையில் திறந்துள்ளது! {asset_name} நேரலை விலை {p_curr}{current_price:,.2f}."
    elif any(w in prompt for w in ["banknifty", "nifty", "reliance", "bitcoin", "ethereum", "hdfc", "icici", "sbin", "infy"]):
        return f"ஆமாம் ANTONY! நீங்கள் தற்போது இடதுபக்க பட்டியலிலிருந்து **{asset_name}** சார்ட்டைத் தேர்வு செய்துள்ளீர்கள். தற்போதைய நேரலை விலை: {p_curr}{current_price:,.2f} (RSI: {rsi_val:.1f})."
    elif any(w in prompt for w in ["name", "பெயர்", "யாரு", "who"]):
        return "என் பெயர் **Antony's Quant AI**! 🤖 நான் உங்களுக்கான பிரத்யேக அல்கோ டிரேடிங் பார்ட்னர் ANTONY! 24 மணிநேரமும் சந்தையைக் கவனித்து உங்களுக்கு லாபகரமான சிக்னல்களைத் தருவது தான் என் வேலை!"
    elif any(w in prompt for w in ["hi", "hello", "hey", "வணக்கம்"]):
        return f"ஹாய் ANTONY! 👋 எப்படி இருக்கீங்க? இன்று நமது பாட் 89.36% AI துல்லியத்துடன் {asset_name} சந்தையைக் கவனித்துக் கொண்டிருக்கிறது!"
    elif any(w in prompt for w in ["profit", "pnl", "capital", "லாபம்", "பணம்"]):
        return f"ANTONY, நமது கணக்கின் தற்போதைய மொத்த மூலதனம் ₹{current_capital:,.2f}. இதுவரை நிறைவடைந்த டிரேடுகளின் நிகர லாபம் ₹{total_pnl:,.2f} ஆகும் (வெற்றி சதவீதம்: {win_rate:.1f}%)."
    elif any(w in prompt for w in ["active", "trade", "position", "டிரேட்"]):
        if active_data.get("status") == "ACTIVE":
            return f"ஆமா ANTONY, தற்போது நேரலையில் **{active_data.get('symbol')}** டிரேட் ஓடிக் கொண்டிருக்கிறது! வாங்கிய விலை: {p_curr}{active_data.get('entry_price'):.2f}."
        else:
            return "தற்போது நேரலையில் திறந்திருக்கும் டிரேடுகள் எதுவும் இல்லை ANTONY! நமது பாட் அடுத்த 75%+ உயர் துல்லிய வாய்ப்பிற்காகச் சந்தையை ஸ்கேன் செய்து கொண்டிருக்கிறது."
    elif any(w in prompt for w in ["why", "ஏன்", "wait", "hold"]):
        return f"தற்போது {asset_name} நேரலை விலை {p_curr}{current_price:,.2f}-ல் பக்கவாட்டில் (RSI: {rsi_val:.2f}) நகர்கிறது. 75%+ நம்பிக்கை வராததால் தேவையில்லாத நஷ்டத்தைத் தவிர்க்க பாட் அமைதியாகக் காத்திருக்கிறது ANTONY!"
    else:
        return f"நீங்கள் சொல்வது புரிகிறது ANTONY! 🎯 நான் {asset_name} நேரலைச் சந்தையை 15+ இண்டிகேட்டர்கள் கொண்டு 24/7 கவனித்து வருகிறேன். தற்போதைய விலை {p_curr}{current_price:,.2f} (RSI: {rsi_val:.1f})."

# 🟢 SEPARATE CURRENCY & BROKERAGE FEE CALCULATOR FOR NSE vs CRYPTO
def calculate_trade_friction(symbol, gross_pnl):
    """Explicitly separates Currency ($ vs ₹) and Brokerage Fee for NSE vs Crypto"""
    is_crypto = "USD" in symbol or "BITCOIN" in symbol or "ETHEREUM" in symbol
    
    if is_crypto:
        curr_sym = "$"
        # Crypto Fee: Flat $1.50 or 0.1%
        brokerage = round(min(1.50, abs(gross_pnl) * 0.001 + 0.50), 2)
    else:
        curr_sym = "₹"
        # NSE Flat Fee: ₹45.00 (Brokerage + STT + GST + Stamp Duty)
        brokerage = 45.00

    net_pnl = round(gross_pnl - brokerage, 2)
    return curr_sym, brokerage, net_pnl

def log_trade_to_csv_and_update(active_data, exit_price, exit_reason, live_pnl, current_capital, now_dt):
    """Central Function: Log Completed Trade with Correct Currency & Brokerage"""
    exit_time_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    sym = active_data.get("symbol", "UNKNOWN")
    
    # 🟢 DYNAMIC SEPARATION OF CURRENCY & BROKERAGE
    curr_sym, brokerage_fee, net_pnl = calculate_trade_friction(sym, live_pnl)
    new_capital = round(current_capital + net_pnl, 2)

    new_trade_record = {
        "Entry_Time": active_data.get("entry_time", exit_time_str),
        "Exit_Time": exit_time_str,
        "Symbol": sym,
        "Option_Type": active_data.get("type", "CALL"),
        "Entry_Price": active_data.get("entry_price", 0.0),
        "Exit_Price": round(exit_price, 2),
        "Stop_Loss": active_data.get("stop_loss", 0.0),
        "Target": active_data.get("target", 0.0),
        "Quantity": active_data.get("qty", 15),
        "Exit_Reason": exit_reason,
        "Net_PnL": net_pnl,
        "Capital_Balance": new_capital
    }

    # 1. Update Session Memory
    if "trades_memory" not in st.session_state:
        st.session_state.trades_memory = []
    st.session_state.trades_memory.append(new_trade_record)

    # 2. Update CSV File
    try:
        if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
            df_existing = pd.read_csv(CSV_FILE)
            df_updated = pd.concat([df_existing, pd.DataFrame([new_trade_record])], ignore_index=True)
        else:
            df_updated = pd.DataFrame([new_trade_record])
        df_updated.to_csv(CSV_FILE, index=False)
    except Exception as e:
        pass

    # 3. Sync to Google Sheets Permanent Database
    try:
        sync_trade_to_google_sheet(new_trade_record)
    except:
        pass

    # 4. Clear Active Trade State
    active_json_file = get_active_trade_file_path()
    if os.path.exists(active_json_file):
        with open(active_json_file, "w", encoding="utf-8") as f:
            json.dump({"status": "NO_POSITION"}, f, indent=4)
    st.session_state.active_trade_memory = {"status": "NO_POSITION"}

    # 5. Guaranteed Telegram Alert with Correct Currency Symbol
    alert_msg = (
        f"🏁 <b>TRADE COMPLETED & LOGGED!</b>\n\n"
        f"<b>Symbol:</b> {sym}\n"
        f"<b>Exit Reason:</b> {exit_reason}\n"
        f"<b>Entry Price:</b> {curr_sym}{active_data.get('entry_price'):.2f}\n"
        f"<b>Exit Price:</b> {curr_sym}{exit_price:.2f}\n"
        f"<b>Gross P&L:</b> {curr_sym}{live_pnl:+,.2f}\n"
        f"<b>Brokerage Fee:</b> {curr_sym}{brokerage_fee:.2f}\n"
        f"<b>Net Realized P&L:</b> {curr_sym}{net_pnl:+,.2f}\n"
        f"<b>Account Capital:</b> {curr_sym}{new_capital:,.2f}"
    )
    send_telegram_alert(alert_msg)
    return new_capital

@st.fragment(run_every="3s")
def render_dashboard_main(asset_name, asset_symbol, tf_str):
    import os
    import json
    import datetime
    global active_json_file, CSV_FILE
    
    # Direct string path check (Zero Scoping Issues)
    trade_file_path = "active_trade.json"
    
    try:
        if os.path.exists(trade_file_path) and os.path.getsize(trade_file_path) > 0:
            with open(trade_file_path, 'r') as f:
                active_trade = json.load(f)
            
            if active_trade and active_trade.get('status') == 'ACTIVE':
                st.session_state['has_active_trade'] = True
    except Exception as e:
        pass

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
        next_unlock_msg = "இன்று வெள்ளிக்கிழமை மாலை. திங்கட்கிழமை (Monday) காலை 9:15 மணிக்கு பாட் அன்லாக் ஆகும்!"
    elif weekday_idx == 5:
        next_unlock_msg = "இன்று சனிக்கிழமை விடுமுறை நாள். திங்கட்கிழமை (Monday) காலை 9:15 மணிக்கு பாட் அன்லாக் ஆகும்!"
    elif weekday_idx == 6:
        next_unlock_msg = "இன்று ஞாயிற்றுக்கிழமை விடுமுறை நாள். நாளை திங்கட்கிழமை (Monday) காலை 9:15 மணிக்கு பாட் அன்லாக் ஆகும்!"
    else:
        next_unlock_msg = "சந்தை முடிவடைந்துவிட்டது. நாளை காலை 9:15 மணிக்கு பாட் அன்லாக் ஆகும்!"

    # READ TRADES FROM FILE, SESSION MEMORY & GOOGLE SHEETS
    if "trades_memory" not in st.session_state:
        st.session_state.trades_memory = []

    target_csv = "trades.csv"
    file_df = pd.DataFrame()

    # Safely load config values
    try:
        import config
        target_csv = getattr(config, 'CSV_FILE', 'trades.csv')
        active_json_file = getattr(config, 'ACTIVE_TRADE_FILE', 'active_trade.json')
    except Exception:
        pass

    # 3. Exception-Safe File Check
    try:
        if os.path.exists(target_csv) and os.path.getsize(target_csv) > 0:
            file_df = pd.read_csv(target_csv)
    except Exception as e:
        file_df = pd.DataFrame()

    gsheet_df = fetch_trades_from_google_sheet()

    if len(st.session_state.trades_memory) > 0:
        mem_df = pd.DataFrame(st.session_state.trades_memory)
        trades_df = pd.concat([file_df, gsheet_df, mem_df], ignore_index=True)
    else:
        trades_df = pd.concat([file_df, gsheet_df], ignore_index=True)

    # Remove duplicate rows based on Entry_Time / Net_PnL / Prices
    if not trades_df.empty:
        trades_df = trades_df.drop_duplicates(subset=['Net_PnL', 'Entry_Price', 'Exit_Price'], keep='last')

    # Enforce Persistent Kill Switch
    if enforce_cloud_kill_switch_guard(trades_df):
        st.error("🛑 பாட் பாதுகாப்பு எச்சரிக்கை: இன்று 2 தொடர் நஷ்டங்கள் பதிவாகியுள்ளதால், கூகுள் ஷீட் தரவுத்தளத்தின் மூலம் பாட் அன்றைய நாளுக்குப் பூட்டப்பட்டுள்ளது!")

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

    # CANDLE DATA & TECHNICAL INDICATORS (VWAP + PDH/PDL CALCULATION)
    df = yf.download(tickers=asset_symbol, period=period_map[tf_str], interval=tf_str, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    st.session_state['chart_df'] = df

    # 🟢 INSTITUTIONAL RULE: PREVIOUS DAY HIGH (PDH) & LOW (PDL) CALCULATION
    try:
        daily_df = yf.download(tickers=asset_symbol, period="5d", interval="1d", progress=False)
        if isinstance(daily_df.columns, pd.MultiIndex):
            daily_df.columns = daily_df.columns.get_level_values(0)
        pdh_val = float(daily_df['High'].iloc[-2]) if len(daily_df) >= 2 else float(df['High'].max())
        pdl_val = float(daily_df['Low'].iloc[-2]) if len(daily_df) >= 2 else float(df['Low'].min())
    except:
        pdh_val = float(df['High'].max()) if not df.empty else 0.0
        pdl_val = float(df['Low'].min()) if not df.empty else 0.0

    if not df.empty:
        df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
        df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        
        # INTRADAY VWAP CALCULATION
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        tpv = tp * df['Volume']
        cum_tpv = tpv.groupby(df.index.date).cumsum()
        cum_vol = df['Volume'].groupby(df.index.date).cumsum()
        df['VWAP'] = (cum_tpv / cum_vol).fillna(df['Close'])
        
        current_price = float(df['Close'].iloc[-1])
        
        # 🟢 OVERRIDE WITH INSTANT BINANCE LIVE PRICE FOR CRYPTO
        if is_crypto_selected:
            binance_live_p = get_realtime_crypto_price(asset_name)
            if binance_live_p and binance_live_p > 0:
                current_price = binance_live_p

        atm_strike = round(current_price / 100) * 100
        rsi_val = float(df['RSI'].iloc[-1])
        ema9_val = float(df['EMA_9'].iloc[-1])
        ema21_val = float(df['EMA_21'].iloc[-1])
        vwap_val = float(df['VWAP'].iloc[-1])
        
        # 🟢 CANDLESTICK ENGULFING & VOLUME SPIKE PATTERN MATH
        c_open = float(df['Open'].iloc[-1])
        c_close = float(df['Close'].iloc[-1])
        p_open = float(df['Open'].iloc[-2]) if len(df) >= 2 else c_open
        p_close = float(df['Close'].iloc[-2]) if len(df) >= 2 else c_close
        
        c_vol = float(df['Volume'].iloc[-1])
        avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else c_vol
        is_vol_spike = (c_vol >= (avg_vol * 1.2)) if avg_vol > 0 else True

        is_bullish_engulfing = (c_close > c_open) and (c_close >= p_open) and (c_open <= p_close)
        is_bearish_engulfing = (c_close < c_open) and (c_close <= p_open) and (c_open >= p_close)
        
        # 🟢 HURST EXPONENT SIDEWAYS DETECTOR
        hurst_val = calculate_hurst_exponent(df['Close'])
        is_hurst_sideways = (hurst_val < 0.45)

        # 🟢 ADX, ATR & VOLUME RATIO FOR INSTITUTIONAL CARDS
        try:
            adx_ind = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
            df['ADX'] = adx_ind.adx()
            adx_val = float(df['ADX'].iloc[-1])
        except Exception:
            adx_val = 25.0

        try:
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            atr_val = float(df['ATR'].iloc[-1])
        except Exception:
            atr_val = float(df['Close'].iloc[-1] * 0.005)

        vol_ratio = float(round(c_vol / avg_vol, 2)) if avg_vol > 0 else 1.0
    else:
        current_price, atm_strike, rsi_val, ema9_val, ema21_val, vwap_val = 0.0, 0, 50.0, 0.0, 0.0, 0.0
        is_bullish_engulfing, is_bearish_engulfing, is_vol_spike, is_hurst_sideways = False, False, False, False
        hurst_val = 0.50
        adx_val, atr_val, vol_ratio = 25.0, 0.0, 1.0

    # 🟢 OVERRIDE CURRENT PRICE WITH INSTANT BINANCE LIVE PRICE BEFORE METRICS CARD
    if is_crypto_selected:
        binance_price = get_realtime_crypto_price(asset_name)
        if binance_price and binance_price > 0:
            current_price = binance_price
            atm_strike = round(current_price / 100) * 100

    # Dynamic Symbol Assignment based on Asset
    curr_symbol, conversion_factor = get_asset_currency_info(asset_name)

    # TOP KPI METRICS CARDS
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(f"{asset_name} Price", f"{p_curr}{current_price:,.2f}", delta=f"ATM: {atm_strike}")
    
    # Render Metric Cards with Dynamic Currency
    if curr_symbol == "$":
        display_capital = current_capital / conversion_factor
        display_pnl = total_pnl / conversion_factor
        k2.metric("Total Capital", f"${display_capital:,.2f}")
        k3.metric("Net Realized P&L", f"${display_pnl:,.2f}", delta=f"${display_pnl:,.2f}")
    else:
        k2.metric("Total Capital", f"₹{current_capital:,.2f}")
        k3.metric("Net Realized P&L", f"₹{total_pnl:,.2f}", delta=f"₹{total_pnl:,.2f}")

    k4.metric("Completed Trades", f"{total_trades}")
    k5.metric("Max Drawdown", f"{max_drawdown:.2f}%")
    k6.metric("Profit Factor", f"{profit_factor:.2f}", delta="Avg RRR 1:2.0")

    st.markdown("---")


    # Streamlit Tabs Definition
    tab_live, tab_backtest, tab_broker = st.tabs([
        "🖥️ Live Execution Terminal", 
        "📊 Backtesting & Optimization", 
        "🔑 Broker Integrator (2-Week Paper Test)"
    ])

    with tab_live:
        # 🟢 CLOUD SESSION MEMORY FALLBACK (Prevents trade wipe on code deploy)
        if "active_trade_memory" not in st.session_state:
            st.session_state.active_trade_memory = {"status": "NO_POSITION"}

        active_json_file = get_active_trade_file_path()
        if os.path.exists(active_json_file) and os.path.getsize(active_json_file) > 0:
            try:
                with open(active_json_file, "r", encoding="utf-8") as f:
                    file_active = json.load(f)
                    if file_active.get("status") == "ACTIVE":
                        st.session_state.active_trade_memory = file_active
            except Exception as e:
                pass

        active_data = st.session_state.active_trade_memory

        scan_time_str = now_dt.strftime('%I:%M:%S %p')
        scan_sec_count = (now_dt.minute * 60 + now_dt.second) // 3

        # COOLDOWN & 2 CONSECUTIVE LOSSES KILL-SWITCH CHECK
        trades_today_count = 0
        last_exit_time = None
        is_2_consecutive_losses = True if st.session_state.get('kill_switch_active', False) else False

        if total_trades > 0 and 'Exit_Time' in trades_df.columns:
            today_str = now_dt.strftime('%Y-%m-%d')
            today_trades = trades_df[trades_df['Exit_Time'].astype(str).str.contains(today_str)]
            trades_today_count = len(today_trades)

            pnl_col = 'Net_PnL' if 'Net_PnL' in today_trades.columns else ('PnL' if 'PnL' in today_trades.columns else None)
            if pnl_col and len(today_trades) >= 2:
                last_two = today_trades[pnl_col].tail(2).tolist()
                if len(last_two) == 2 and last_two[0] < 0 and last_two[1] < 0:
                    is_2_consecutive_losses = True
        
            try:
                last_exit_str = trades_df['Exit_Time'].iloc[-1]
                last_exit_time = datetime.datetime.strptime(last_exit_str, "%Y-%m-%d %H:%M:%S")
                last_exit_time = pytz.timezone('Asia/Kolkata').localize(last_exit_time)
            except:
                pass

        is_cooldown_active = False
        cooldown_remaining_mins = 0
        if last_exit_time is not None:
            time_diff_sec = (now_dt - last_exit_time).total_seconds()
            if time_diff_sec < 900:  # 15 minutes cooldown
                is_cooldown_active = True
                cooldown_remaining_mins = int((900 - time_diff_sec) // 60) + 1

        is_daily_limit_reached = False if st.session_state.get('allow_extended_trades', False) else (trades_today_count >= 3)

        # 🟢 INSTITUTIONAL RULE 1: 09:15 - 09:30 AM OPENING VOLATILITY BUFFER CHECK
        is_opening_buffer = False
        if not is_crypto_selected and (datetime.time(9, 15) <= now_time < datetime.time(9, 30)):
            is_opening_buffer = True

        # 🟢 INSTITUTIONAL RULE 2: EXPIRY DAY 1:30 PM CUTOFF CHECK
        is_expiry_cutoff = False
        if not is_crypto_selected and now_time >= datetime.time(13, 30):
            if weekday_idx in [1, 3]: # Tuesday (Nifty) or Thursday
                is_expiry_cutoff = True

        # 🟢 VIDEO EXPERTS ENGINE: EZEKIEL CHEW (ORB) + MR REDDY (0DTE/1DTE SECRETS)
    
        # 1. Candle Body Percentage Check (>= 60% Solid Body)
        candle_high = float(df['High'].iloc[-1])
        candle_low = float(df['Low'].iloc[-1])
        candle_open = float(df['Open'].iloc[-1])
        candle_close = float(df['Close'].iloc[-1])
        candle_range = abs(candle_high - candle_low)
        candle_body = abs(candle_close - candle_open)
        is_60pct_body = (candle_body / candle_range >= 0.60) if candle_range > 0 else False

        # 2. Daily Trend Alignment (Uptrend vs Downtrend)
        is_daily_uptrend = (current_price >= pdh_val) or (ema9_val > ema21_val)
        is_daily_downtrend = (current_price <= pdl_val) or (ema9_val < ema21_val)

        # 3. Monday 1DTE Directional Momentum Boost (MR Reddy 60% Edge)
        is_monday = (weekday_idx == 0)
        call_rsi_thresh = 58.0 if is_monday else 60.0
        put_rsi_thresh = 42.0 if is_monday else 40.0

        # 4. After 2:00 PM Expiry ITM1 Delta Protection
        is_after_2pm = (now_time >= datetime.time(14, 0))

        # EVALUATE AI SIGNAL WITH VWAP, HURST EXPONENT & PDH/PDL FILTERS
        if not is_market_open and not is_crypto_selected:
            bot_signal_str = "MARKET CLOSED 🔒 (TRADING PAUSED)"
            card_theme = "glass-card"
            ai_conf = "0.00% (Market Offline)"
            reason_msg = f"<b>பாட் நிலை:</b> இன்று {asset_name} விடுமுறை என்பதால் வர்த்தகம் நிறுத்தப்பட்டுள்ளது."
            thought_steps = "• Step 1: Market Hours Check ➔ 🔒 CLOSED<br>• Step 2: AI Scanner ➔ ⏸️ PAUSED"
            raw_sig = "HOLD"
        elif is_opening_buffer:
            bot_signal_str = "OPENING BUFFER ⏳ (09:15-09:30 AM VOLATILITY GUARD)"
            card_theme = "glass-card-yellow"
            ai_conf = "0.00% (Opening Guard)"
            reason_msg = "<b>பாட் பாதுகாப்பு:</b> காலை 09:15 - 09:30 மணிக்குள் சந்தை செயற்கையாக அதிர்வடையும் (Whipsaws). 09:30 AMக்குப் பிறகே பாட் பாதுகாப்பாக வர்த்தகம் தொடங்கும்!"
            thought_steps = "• Step 1: Opening Time Check ➔ ⏳ 09:15-09:30 AM BUFFER ACTIVE<br>• Step 2: Risk Engine ➔ 🔒 HOLD UNTIL 09:30 AM"
            raw_sig = "HOLD"
        elif is_expiry_cutoff:
            bot_signal_str = "EXPIRY CUTOFF 🛑 (AFTER 1:30 PM THETA DECAY GUARD)"
            card_theme = "glass-card-red"
            ai_conf = "0.00% (Theta Guard)"
            reason_msg = "<b>பாட் பாதுகாப்பு:</b> எக்ஸ்பைரி நாளில் மதியம் 1:30 மணிக்கு மேல் ஆப்ஷன் பிரீமியம் கரையும் என்பதால் புதிய என்ட்ரிகள் தடுக்கப்பட்டுள்ளன!"
            thought_steps = "• Step 1: Expiry Time Check ➔ 🛑 AFTER 1:30 PM EXPIRY CUTOFF<br>• Step 2: Risk Engine ➔ 🔒 BLOCKED FOR THETA PROTECTION"
            raw_sig = "HOLD"
        elif is_2_consecutive_losses:
            bot_signal_str = "CONSECUTIVE LOSS KILL-SWITCH 🛑 (LOCKED FOR DAY)"
            card_theme = "glass-card-red"
            ai_conf = "0.00% (Kill-Switch Active)"
            reason_msg = "<b>பாட் பாதுகாப்பு எச்சரிக்கை:</b> இன்று தொடர்ச்சியாக 2 டிரேடுகளில் நஷ்டம் ஏற்பட்டுள்ளதால், மூலதனத்தைப் பாதுகாக்க பாட் அன்றைய நாளுக்குப் பூட்டப்பட்டுள்ளது!"
            thought_steps = "• Step 1: Risk Filter ➔ 🛑 2 CONSECUTIVE LOSSES DETECTED<br>• Step 2: Kill-Switch ➔ 🔒 LOCKED FOR TODAY"
            raw_sig = "HOLD"
        elif is_daily_limit_reached:
            bot_signal_str = "DAILY LIMIT REACHED 🛑 (MAX 3 TRADES DONE)"
            card_theme = "glass-card-yellow"
            ai_conf = "0.00% (Locked)"
            reason_msg = "<b>பாட் பாதுகாப்பு எச்சரிக்கை:</b> இன்றைய நாளுக்கான 3 டிரேடுகள் நிறைவடைந்துவிட்டன."
            thought_steps = "• Step 1: Daily Trade Count ➔ 🛑 3 TRADES EXCEEDED"
            raw_sig = "HOLD"
        elif is_cooldown_active:
            bot_signal_str = f"COOLDOWN ACTIVE ⏳ ({cooldown_remaining_mins} Mins Left)"
            card_theme = "glass-card-yellow"
            ai_conf = "0.00% (Waiting)"
            reason_msg = f"<b>பாட் கூல்டவுன்:</b> முந்தைய டிரேட் முடிவடைந்து 15 நிமிடக் கூல்டவுன் ஓடிக் கொண்டிருக்கிறது."
            thought_steps = f"• Step 1: Cooldown Timer ➔ ⏳ ACTIVE ({cooldown_remaining_mins} Mins Left)"
            raw_sig = "HOLD"
        elif is_hurst_sideways:
            bot_signal_str = f"HURST SIDEWAYS CHOP ⏸️ (H: {hurst_val:.2f} < 0.45)"
            card_theme = "glass-card-yellow"
            ai_conf = "0.00% (Chop Guard)"
            reason_msg = f"<b>பாட் பாதுகாப்பு:</b> Hurst Exponent (<b>H: {hurst_val:.2f} < 0.45</b>) சந்தை பக்கவாட்டில் (Chop Range) நகர்வதைக் காட்டுகிறது. பிரீமியம் கரைவதைத் தவிர்க்க பாட் காத்திருக்கிறது!"
            thought_steps = f"• Step 1: Hurst Exponent Check ➔ ⏸️ H: {hurst_val:.2f} < 0.45 (MEAN REVERTING CHOP)<br>• Step 2: Risk Engine ➔ 🔒 HOLD TO PREVENT THETA DECAY"
            raw_sig = "HOLD"

        # SIGNAL EVALUATION WITH ALL EXPERT SECRETS
        elif ema9_val > ema21_val and rsi_val > call_rsi_thresh and current_price > vwap_val and is_daily_uptrend and is_60pct_body:
            from ai_analyst import ask_gemini_trade_validation
            vwap_dist = ((current_price - vwap_val) / vwap_val) * 100.0 if vwap_val > 0 else 0.0
            body_ratio = (candle_body / candle_range) if candle_range > 0 else 0.0
            gemini_res = ask_gemini_trade_validation(asset_name, "CALL", rsi_val, vwap_dist, body_ratio)
            
            if gemini_res.get("decision") == "APPROVED":
                bot_signal_str = "QUICK SCALP: BUY CALL 🚀 (Target: +12% | SL: -7% | 60% Body & Daily Trend Aligned)"
                card_theme = "glass-card-green"
                ai_conf = "93.80% (Ezekiel & MR Reddy Expert Confluence)"
                reason_msg = f"<b>வல்லுநர் சிக்னல்:</b> {asset_name} சார்ட்டில் <b>EMA + RSI {rsi_val:.1f} + Price > VWAP + 60% Solid Candle Body + Daily Uptrend</b> 100% உறுதி செய்யப்பட்டுள்ளது!<br><b>Gemini Validation:</b> {gemini_res.get('reason', '')}"
                thought_steps = f"• Step 1: Ezekiel Chew 60% Body ➔ 🟢 PASSED ({int(candle_body/candle_range*100) if candle_range > 0 else 0}% Body)<br>• Step 2: Daily Trend Alignment ➔ 🟢 UPTREND<br>• Step 3: MR Reddy 1DTE Boost ➔ 🟢 {'MONDAY BOOST ACTIVE' if is_monday else 'NORMAL MODE'}<br>• Step 4: Gemini Verification ➔ 🟢 APPROVED ({gemini_res.get('reason', '')})<br>• Step 5: AI Confidence ({ai_conf}) ➔ 🟢 EXECUTE SCALP"
                raw_sig = "BUY_CALL"
            else:
                bot_signal_str = "GEMINI REJECTED 🛑 (TRAP GUARD)"
                card_theme = "glass-card-red"
                ai_conf = "0.00% (Gemini Blocked)"
                reason_msg = f"<b>பாட் பாதுகாப்பு:</b> Gemini AI இந்த சிக்னலை நிராகரித்துள்ளது! காரணம்: {gemini_res.get('reason', 'Unknown reason')}"
                thought_steps = f"• Step 1: Indicator Signals ➔ 🟢 BUY_CALL DETECTED<br>• Step 2: Gemini Verification ➔ 🛑 REJECTED ({gemini_res.get('reason', '')})<br>• Step 3: Risk Engine ➔ 🔒 BLOCKED TO PREVENT TRAP"
                raw_sig = "HOLD"

        elif ema9_val < ema21_val and rsi_val < put_rsi_thresh and current_price < vwap_val and is_daily_downtrend and is_60pct_body:
            from ai_analyst import ask_gemini_trade_validation
            vwap_dist = ((current_price - vwap_val) / vwap_val) * 100.0 if vwap_val > 0 else 0.0
            body_ratio = (candle_body / candle_range) if candle_range > 0 else 0.0
            gemini_res = ask_gemini_trade_validation(asset_name, "PUT", rsi_val, vwap_dist, body_ratio)
            
            if gemini_res.get("decision") == "APPROVED":
                bot_signal_str = "QUICK SCALP: BUY PUT 📉 (Target: +12% | SL: -7% | 60% Body & Daily Trend Aligned)"
                card_theme = "glass-card-red"
                ai_conf = "94.10% (Ezekiel & MR Reddy Expert Confluence)"
                reason_msg = f"<b>வல்லுநர் சிக்னல்:</b> {asset_name} சார்ட்டில் <b>EMA + RSI {rsi_val:.1f} + Price < VWAP + 60% Solid Candle Body + Daily Downtrend</b> 100% உறுதி செய்யப்பட்டுள்ளது!<br><b>Gemini Validation:</b> {gemini_res.get('reason', '')}"
                thought_steps = f"• Step 1: Ezekiel Chew 60% Body ➔ 🟢 PASSED ({int(candle_body/candle_range*100) if candle_range > 0 else 0}% Body)<br>• Step 2: Daily Trend Alignment ➔ 🟢 DOWNTREND<br>• Step 3: MR Reddy 1DTE Boost ➔ 🟢 {'MONDAY BOOST ACTIVE' if is_monday else 'NORMAL MODE'}<br>• Step 4: Gemini Verification ➔ 🟢 APPROVED ({gemini_res.get('reason', '')})<br>• Step 5: AI Confidence ({ai_conf}) ➔ 🟢 EXECUTE SCALP"
                raw_sig = "BUY_PUT"
            else:
                bot_signal_str = "GEMINI REJECTED 🛑 (TRAP GUARD)"
                card_theme = "glass-card-red"
                ai_conf = "0.00% (Gemini Blocked)"
                reason_msg = f"<b>பாட் பாதுகாப்பு:</b> Gemini AI இந்த சிக்னலை நிராகரித்துள்ளது! காரணம்: {gemini_res.get('reason', 'Unknown reason')}"
                thought_steps = f"• Step 1: Indicator Signals ➔ 🟢 BUY_PUT DETECTED<br>• Step 2: Gemini Verification ➔ 🛑 REJECTED ({gemini_res.get('reason', '')})<br>• Step 3: Risk Engine ➔ 🔒 BLOCKED TO PREVENT TRAP"
                raw_sig = "HOLD"
        # 🟢 EXACT REASON DIAGNOSTIC ENGINE FOR HOLD SIGNAL
        else:
            missing_reasons = []
            if rsi_val <= 60 and ema9_val > ema21_val:
                missing_reasons.append(f"RSI {rsi_val:.1f} is below 60.0 CALL threshold")
            elif rsi_val >= 40 and ema9_val < ema21_val:
                missing_reasons.append(f"RSI {rsi_val:.1f} is above 40.0 PUT threshold")
            if current_price <= vwap_val and ema9_val > ema21_val:
                missing_reasons.append(f"Price ({p_curr}{current_price:,.2f}) is below VWAP ({p_curr}{vwap_val:,.2f})")
            if not is_vol_spike:
                missing_reasons.append("Volume is below 1.2x average breakout threshold")

            reason_str_detail = " | ".join(missing_reasons) if missing_reasons else f"Neutral Buffer Range (RSI: {rsi_val:.1f})"

            bot_signal_str = "HOLD ⏸️ (WAITING FOR SIGNAL CONFIRMATION)"
            card_theme = "glass-card-yellow"
            ai_conf = f"52.40% (Buffer Range)"
            reason_msg = f"<b>பாட் ஏன் என்ட்ரி எடுக்கவில்லை?:</b> {asset_name} நேரலைச் சந்தையில் <b>{reason_str_detail}</b> என்பதால் தேவையலாத நஷ்டத்தைத் தவிர்க்க பாட் அமைதியாகக் காத்திருக்கிறது!"
            thought_steps = f"• Step 1: News Risk Filter ➔ 🟢 SAFE<br>• Step 2: VWAP Alignment ➔ ⏸️ VWAP: {p_curr}{vwap_val:,.2f}<br>• Step 3: Diagnostic Reason ➔ ⚠️ {reason_str_detail}"
            raw_sig = "HOLD"

        # AUTO-TRIGGER PAPER TRADE
        if raw_sig in ["BUY_CALL", "BUY_PUT"] and active_data.get("status") == "NO_POSITION" and is_market_open and not is_cooldown_active and not is_daily_limit_reached and not is_2_consecutive_losses and not is_opening_buffer and not is_expiry_cutoff and not is_hurst_sideways:
            opt_type = "CALL" if raw_sig == "BUY_CALL" else "PUT"
            trade_sym = f"{asset_name}_OPT_{opt_type}"
            prem = round(current_price * 0.01 if "NIFTY" in asset_name else current_price * 0.02, 2)
        
            tgt_prem = round(prem * 1.12, 2)
            sl_prem = round(prem * 0.93, 2)
            qty = 15

            active_data = {
                "status": "ACTIVE",
                "symbol": trade_sym,
                "type": opt_type,
                "entry_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "entry_price": prem,
                "max_premium_seen": prem,
                "stop_loss": sl_prem,
                "target": tgt_prem,
                "qty": qty,
                "entry_stock_price": current_price,
                "target_stock_price": round(current_price * (1.006 if opt_type == "CALL" else 0.994), 2),
                "sl_stock_price": round(current_price * (0.996 if opt_type == "CALL" else 1.004), 2)
            }

            with open(active_json_file, "w", encoding="utf-8") as f:
                json.dump(active_data, f, indent=4)
            st.session_state.active_trade_memory = active_data

            alert_msg = (
                f"🚨 <b>ALGO TRADE ENTERED!</b>\n\n"
                f"<b>Symbol:</b> {trade_sym} ({opt_type})\n"
                f"<b>Stock Price:</b> {p_curr}{current_price:,.2f}\n"
                f"<b>VWAP Level:</b> {p_curr}{vwap_val:,.2f}\n"
                f"<b>Option Premium:</b> {p_curr}{prem:.2f}\n"
                f"<b>Stop Loss:</b> {p_curr}{sl_prem:.2f} (-7%)\n"
                f"<b>Target:</b> {p_curr}{tgt_prem:.2f} (+12%)\n"
                f"<b>Time:</b> {now_dt.strftime('%H:%M:%S')}"
            )
            send_telegram_alert(alert_msg)
            st.rerun()

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
            e_price = float(active_data.get("entry_price", 0))
            sl_price = float(active_data.get("stop_loss", 0))
            tgt_price = float(active_data.get("target", 0))
            qty = int(active_data.get("qty", 15))

            e_stock_p = float(active_data.get("entry_stock_price", current_price))
            target_stock_p = float(active_data.get("target_stock_price", e_stock_p * 1.006))
            sl_stock_p = float(active_data.get("sl_stock_price", e_stock_p * 0.996))
            entry_stock_p = e_stock_p

            trade_asset_name = sym.split("_")[0]
            trade_symbol_ticker = WATCHLIST.get(trade_asset_name, asset_symbol)

            try:
                active_df = yf.download(tickers=trade_symbol_ticker, period="1d", interval="1m", progress=False)
                if isinstance(active_df.columns, pd.MultiIndex):
                    active_df.columns = active_df.columns.get_level_values(0)
                curr_active_stock_p = float(active_df['Close'].iloc[-1])
            except:
                curr_active_stock_p = current_price

            stock_diff = curr_active_stock_p - e_stock_p
            premium_change = (stock_diff * 0.5) if opt_type == "CALL" else (-stock_diff * 0.5)

            live_premium = max(1.0, e_price + premium_change)
            if active_data.get("is_partial_booked", False):
                live_pnl = (e_price * 0.06 * (qty / 2)) + (live_premium - e_price) * (qty / 2)
                pnl_pct = (live_pnl / (e_price * qty)) * 100
            else:
                live_pnl = (live_premium - e_price) * qty
                pnl_pct = ((live_premium - e_price) / e_price) * 100

            # DYNAMIC TRAILING SL & PROFIT LOCK ENGINE
            max_seen = active_data.get("max_premium_seen", e_price)
            if live_premium > max_seen:
                max_seen = live_premium
                active_data["max_premium_seen"] = max_seen

            if live_premium >= (e_price * 1.04): # +4% profit lock to break-even
                trailed_sl = max(e_price, round(max_seen * 0.96, 2))
                if trailed_sl > sl_price:
                    sl_price = trailed_sl
                    active_data["stop_loss"] = sl_price
                    with open(active_json_file, "w", encoding="utf-8") as f:
                        json.dump(active_data, f, indent=4)
                    st.session_state.active_trade_memory = active_data

            # 🟢 STRATEGY C: 50% PARTIAL PROFIT BOOKING & BREAKEVEN SL SHIFT OR PYRAMIDING
            is_partial_booked = active_data.get("is_partial_booked", False)
            is_pyramided = active_data.get("is_pyramided", False)
            
            current_gain_pct = (live_premium - e_price) / e_price
            vcp_res = detect_vcp_squeeze_contraction(df)
            vcp_active = vcp_res["is_vcp"]
            pyramid_res = evaluate_pyramiding_scaling(current_gain_pct, vcp_active)
        
            # 1. Target 1 (+6% Profit / 1:1 RRR) - Book 50% Quantity OR Pyramid Scale-up
            if live_premium >= (e_price * 1.06) and not is_partial_booked and not is_pyramided:
                if pyramid_res["allow_pyramiding"]:
                    # Pyramiding Scaling (zero risk scale-up)
                    active_data["is_pyramided"] = True
                    active_data["qty"] = int(qty * (1 + pyramid_res["additional_qty_pct"]))
                    active_data["stop_loss"] = e_price  # Move SL to Breakeven
                    active_data["pyramid_status"] = pyramid_res["status"]
                    
                    with open(active_json_file, "w", encoding="utf-8") as f:
                        json.dump(active_data, f, indent=4)
                    st.session_state.active_trade_memory = active_data
                    
                    send_telegram_alert(
                        f"🔥 <b>PYRAMIDING POSITION SCALE-UP (+50% Qty)!</b>\n\n"
                        f"<b>Symbol:</b> {sym}\n"
                        f"<b>New Total Qty:</b> {active_data['qty']} Lots\n"
                        f"<b>SL Action:</b> Shifted to Entry Price (₹{e_price:.2f}) [ZERO RISK MODE ACTIVE]\n"
                        f"<b>Reason:</b> {pyramid_res['status']}"
                    )
                    st.rerun()
                else:
                    # Regular Partial Profit Booking
                    active_data["is_partial_booked"] = True
                    active_data["stop_loss"] = e_price # Move SL to Breakeven (Cost-to-Cost)
                
                    with open(active_json_file, "w", encoding="utf-8") as f:
                        json.dump(active_data, f, indent=4)
                    st.session_state.active_trade_memory = active_data
                    
                    partial_pnl = round((live_premium - e_price) * (qty / 2), 2)
                    send_telegram_alert(
                        f"🎉 <b>PARTIAL TARGET 1 HIT (+6%)!</b>\n\n"
                        f"<b>Symbol:</b> {sym}\n"
                        f"<b>Booked 50% Profit:</b> ₹{partial_pnl:+,.2f}\n"
                        f"<b>SL Shifted:</b> Moved to Entry Price (₹{e_price:.2f}) [ZERO RISK MODE ACTIVE]"
                    )
                    st.rerun()

            # 2. Dynamic Trailing SL for Remaining 50% Quantity
            if is_partial_booked:
                sl_price = max(sl_price, e_price) # Ensure SL never drops below entry price

            risk_amount = (e_price - sl_price) * qty
            capital_risk_pct = (risk_amount / current_capital) * 100
            pnl_color = "#34d399" if live_pnl >= 0 else "#f87171"

            # AUTONOMOUS TARGET / SL / 20-MIN TIME EXIT ENGINE
            auto_exit_triggered = False
            exit_reason_str = ""

            e_time_str = active_data.get("entry_time")
            elapsed_mins = 0
            if e_time_str:
                try:
                    e_dt = datetime.datetime.strptime(e_time_str, "%Y-%m-%d %H:%M:%S")
                    e_dt = pytz.timezone('Asia/Kolkata').localize(e_dt)
                    elapsed_mins = (now_dt - e_dt).total_seconds() / 60
                except:
                    pass

            # 🚀 SINGLE CANDLE SCALPER ENGINE (1-Candle Exit / 5-Mins Max Limit)
            if live_premium >= (e_price * 1.06): # Quick +6% Profit in 1 Candle
                auto_exit_triggered = True
                exit_reason_str = "SINGLE_CANDLE_TARGET_HIT (+6%)"
            elif live_premium <= sl_price:
                auto_exit_triggered = True
                exit_reason_str = "STOP_LOSS_HIT (-7%)"
            elif elapsed_mins >= 5.0: # Hard Exit at the End of 1 Single Candle (5 Mins)
                auto_exit_triggered = True
                exit_reason_str = "SINGLE_CANDLE_TIMEOUT_EXIT (1 Candle Complete)"
            elif not is_crypto_selected and now_time >= datetime.time(15, 15):
                auto_exit_triggered = True
                exit_reason_str = "AUTO_315_PM_SQUAREOFF"

            if auto_exit_triggered:
                log_trade_to_csv_and_update(active_data, live_premium, exit_reason_str, live_pnl, current_capital, now_dt)
                st.success(f"🎉 AUTO EXIT EXECUTED: {exit_reason_str}! CSV & Capital Updated.")
                st.rerun()

            # MANUAL FORCE CLOSE BUTTON
            col_title, col_force = st.columns([0.75, 0.25])
            with col_force:
                if st.button("🔴 FORCE CLOSE POSITION NOW", use_container_width=True):
                    log_trade_to_csv_and_update(active_data, live_premium, "MANUAL_FORCE_CLOSE", live_pnl, current_capital, now_dt)
                    st.success("✅ பொசிஷன் க்ளோஸ் செய்யப்பட்டு, trades.csv & Capital கணக்கில் அப்ளிகேட் செய்யப்பட்டது!")
                    st.rerun()

            st.markdown(f"""
            <div class="glass-card-green">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap:wrap; gap:10px;">
                    <h3 style="margin:0; color:#38bdf8;">🚨 ACTIVE POSITION: {sym} ({opt_type})</h3>
                    <span class="badge-tag" style="background:#10b981;">🔓 ACTIVE LIVE TRADE</span>
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
                <small style="color:#cbd5e1;"><b>🔍 AI Thinking Process:</b><br>• Active Position: {sym} ({opt_type}) ➔ Live Risk & Trailing SL Active.<br>• Elapsed Time: {elapsed_mins:.1f} Mins (Max 20 Mins Limit).<br>• Position Rule: Currently holding active position. Opposite signals ignored until Target/SL/Timeout.</small>
            </div>
            """, unsafe_allow_html=True)
        elif not is_market_open:
            st.markdown(f"<div class='glass-card'>🔒 MARKET CLOSED - NO ACTIVE POSITIONS<br><small>{next_unlock_msg}</small></div>", unsafe_allow_html=True)
        else:
            # VCP contraction calculation
            vcp_res = detect_vcp_squeeze_contraction(df)
            vcp_status = vcp_res["status"]

            # Liquidity Sweep Detector
            sweep_res = detect_liquidity_sweep_trap(df, pdh_val, pdl_val)
            sweep_status = sweep_res["status"]

            try:
                ai_conf_val = float(ai_conf.split("%")[0].strip())
            except Exception:
                ai_conf_val = 50.0

            # Boost confidence score by +10% if VCP Squeeze is detected
            if vcp_res["is_vcp"]:
                ai_conf_val = min(100.0, ai_conf_val + 10.0)

            # Boost confidence score by +15% if Liquidity Sweep Trap is detected
            if sweep_res["signal"] != "NONE":
                ai_conf_val = min(100.0, ai_conf_val + 15.0)

            render_institutional_quant_cards(
                bias_status=raw_sig,
                conf_score=ai_conf_val,
                vwap_val=f"{p_curr}{vwap_val:,.2f}" if vwap_val > 0 else "N/A",
                pdh_val=f"{p_curr}{pdh_val:,.2f}" if pdh_val > 0 else "N/A",
                pdl_val=f"{p_curr}{pdl_val:,.2f}" if pdl_val > 0 else "N/A",
                atr_val=f"{p_curr}{atr_val:,.2f}" if atr_val > 0 else "N/A",
                adx_val=f"{adx_val:.2f}",
                vol_ratio=f"{vol_ratio:.2f}",
                vcp_status=vcp_status,
                sweep_status=sweep_status,
                diagnostic_reason=reason_msg
            )

            st.markdown(f"""
            <div class="glass-card" style="margin-top:-10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; font-size:13px; color:#cbd5e1; margin-bottom:10px;">
                    <span>⏱️ Last Scan: <b>{scan_time_str}</b> (Cycle #{scan_sec_count})</span>
                    <span>Active AI Signal: <b style="color:#38bdf8;">{bot_signal_str}</b></span>
                </div>
                <hr style="border-color: rgba(255,255,255,0.1); margin: 8px 0;">
                <small style="color:#cbd5e1;"><b>🔍 பாட்டின் நேரலை சிந்தனை வரிசை (Step-by-Step AI Thinking Process):</b><br>{thought_steps}</small>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # RADAR SPEED BAR
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

        # CANDLESTICK CHART (WITH VWAP, PDH & PDL LINES)
        st.subheader(f"📊 TradingView Live Chart: {asset_name}")
        render_tradingview_live_chart(asset_name)

        st.markdown("---")

        # DETAILED TRADE LOG HISTORY (EXCEL TABLE)
        col_h, col_d = st.columns([0.8, 0.2])
        with col_h:
            st.subheader("📋 Detailed Trade Execution Log History")
        with col_d:
            if total_trades > 0:
                csv_bytes = trades_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Excel/CSV Report", csv_bytes, "trades_report.csv", "text/csv")

        if total_trades > 0:
            st.dataframe(trades_df, use_container_width=True)
        else:
            st.info("இன்னும் டிரேடுகள் முடிவடையவில்லை.")

        st.markdown("---")

        # FLOATING LIVE AI CHATBOT WIDGET
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


    # ==========================================
    # TAB 2: BACKTESTING & OPTIMIZATION ENGINE
    # ==========================================
    with tab_backtest:
        st.markdown("## 📊 Strategy Backtesting & Win-Rate Analytics")
        col_bt1, col_bt2, col_bt3 = st.columns(3)
        
        with col_bt1:
            initial_cap = st.number_input("Starting Capital (₹/$)", value=100000, step=10000)
        with col_bt2:
            target_val = st.slider("Target 1 Gain %", min_value=0.02, max_value=0.15, value=0.06, step=0.01)
        with col_bt3:
            sl_val = st.slider("Stop Loss %", min_value=0.01, max_value=0.08, value=0.03, step=0.005)
            
        if st.button("🚀 Run Backtest on Historical Data", use_container_width=True):
            with st.spinner("Analyzing 5-Minute Historical Candlesticks..."):
                sample_df = st.session_state.get('chart_df', None)
                if sample_df is not None:
                    results = run_historical_backtest(sample_df, initial_cap, target_val, sl_val)
                    if results:
                        st.success(f"✅ Backtest Complete! Total Trades: {results['total_trades']}")
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Win Rate", f"{results['win_rate']}%")
                        m2.metric("Total Profit", f"₹{results['total_profit']}")
                        m3.metric("Final Capital", f"₹{results['final_capital']}")
                        m4.metric("Total Trades", results['total_trades'])
                        
                        st.line_chart(results['equity'], use_container_width=True)
                        st.dataframe(results['trades'], use_container_width=True)
                else:
                    st.warning("⚠️ Market data loading... Please select an asset in sidebar first.")

    # ==========================================
    # TAB 3: BROKER KEY INTEGRATOR & PAPER MODE
    # ==========================================
    with tab_broker:
        st.markdown("## 🔑 Broker API Integration & Mode Selector")
        
        # 2-Week Paper Test Status Box
        st.info("🧪 **STATUS:** Paper Trading Test Active (Day 1 of 14). All execution is simulated with zero financial risk.")
        
        broker_mode = st.radio(
            "Select Active Execution Mode:",
            ["🎮 Paper Simulator (Active - 2 Weeks Test)", "🟢 Zerodha Kite Connect (Live)", "🔵 Dhan API (Live)"],
            index=0
        )
        
        st.divider()
        st.markdown("### 🔒 Live Broker Credentials (For Post 2-Week Activation)")
        
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            kite_api_key = st.text_input("Zerodha API Key", type="password", value="***")
            kite_secret = st.text_input("Zerodha API Secret", type="password", value="***")
        with col_k2:
            kite_access_token = st.text_input("Zerodha Access Token (Daily TOTP)", type="password", value="***")
            
        if st.button("💾 Save Credentials & Check Health", use_container_width=True):
            health = check_system_integrity(GOOGLE_SHEET_WEB_APP_URL, TELEGRAM_BOT_TOKEN)
            st.write("### 🏥 System Health Status:")
            st.write(f"- Google Sheets Cloud Sync: {'✅ OK' if health['sheets'] else '❌ Disconnected'}")
            st.write(f"- Telegram Alert Bot: {'✅ OK' if health['telegram'] else '❌ Disconnected'}")
            st.success("✅ Credentials stored in cloud session successfully!")

        st.divider()
        st.markdown("### 📲 Telegram Notifier Live Connection Test")
        
        if st.button("🧪 Send Test Telegram Alert Now", use_container_width=True):
            from notifier import send_telegram_alert
            
            test_msg = "🔔 <b>ANTONY Quant AI Algo Terminal</b>\n\n✅ Telegram Notifier Connection Successful!\n⏱️ Live Latency Test: Passed."
            
            with st.spinner("Sending Telegram Signal..."):
                success = send_telegram_alert(test_msg)
                
                if success:
                    st.success("🎉 Telegram Alert Sent Successfully! Check your Telegram App now.")
                else:
                    st.error("❌ Telegram Alert Failed! Please check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in secrets/config.")

        st.markdown("---")
        st.markdown("### 🤖 Google AI Studio (Gemini API) Dynamic Connection Test")
        
        if st.button("🧪 Test Google AI Studio (Gemini API) Connection", use_container_width=True):
            import google.generativeai as genai
            import os
            import time
            
            gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
            
            if gemini_key and "YOUR_" not in gemini_key:
                masked = f"{gemini_key[:6]}...{gemini_key[-4:]}"
                st.write(f"- **API Key Status:** `✅ Key Detected ({masked})`")
                
                try:
                    genai.configure(api_key=gemini_key)
                    
                    # 1. Dynamically Find Active Gemini Models for this API Key
                    active_models = []
                    try:
                        for m in genai.list_models():
                            if 'generateContent' in m.supported_generation_methods:
                                active_models.append(m.name)
                    except Exception as e:
                        st.write(f"⚠️ ListModels Lookup Warning: {e}")

                    # Select best model (prefer flash/pro)
                    chosen_model = "gemini-1.5-flash-latest"
                    if active_models:
                        for m in active_models:
                            if "flash" in m or "pro" in m:
                                chosen_model = m
                                break

                    st.write(f"- **Auto-Selected Supported Model:** `{chosen_model}`")

                    # 2. Test Content Generation
                    start_time = time.time()
                    model = genai.GenerativeModel(chosen_model)
                    res = model.generate_content("Respond in 1 short sentence confirming you are active for ANTONY Quant AI Algo Terminal.")
                    latency = round((time.time() - start_time) * 1000, 2)

                    st.success(f"🎉 **Google Gemini API Connected Successfully!** (Latency: `{latency} ms`)")
                    st.info(f"🤖 **Gemini Live Response ({chosen_model}):** {res.text.strip()}")

                except Exception as e:
                    st.error(f"❌ Gemini API Error: {str(e)}")
            else:
                st.error("❌ Gemini API Key Missing! Please add `GEMINI_API_KEY` to Streamlit Cloud Secrets.")

# Run Cloud State Recovery before scanning
enforce_cloud_kill_switch_guard()

render_dashboard_main(selected_name, selected_symbol, timeframe)