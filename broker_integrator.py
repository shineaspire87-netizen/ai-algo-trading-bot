# broker_integrator.py - Fail-Safe Diagnostic Console with on_click Callbacks

import streamlit as st
import requests
import time
import datetime
import hmac
import hashlib
import os

def append_diag_log(msg: str):
    """Appends timestamped log message to persistent diagnostic console"""
    ist_now = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime('%I:%M:%S %p IST')
    log_line = f"[{ist_now}] {msg}"
    
    if 'diagnostic_console_logs' not in st.session_state:
        st.session_state['diagnostic_console_logs'] = []
    
    st.session_state['diagnostic_console_logs'].append(log_line)

# -------------------------------------------------------------
# ON_CLICK CALLBACK HANDLERS (EXECUTIVE PRIOR TO RENDER)
# -------------------------------------------------------------
def callback_test_telegram():
    append_diag_log("Action Triggered: Telegram Connection Test")
    token = st.session_state.get('diag_tg_token', '8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE')
    chat = st.session_state.get('diag_tg_chat', '1072750499')
    append_diag_log(f"Token Length: {len(token)} | Chat ID: {chat}")
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat, "text": "🔔 <b>ANTONY Quant Terminal</b>\n\n✅ Live Connection Test Successful!", "parse_mode": "HTML"}
        append_diag_log("Sending HTTP POST to Telegram API...")
        res = requests.post(url, json=payload, timeout=5)
        append_diag_log(f"HTTP Response Code: {res.status_code}")
        
        if res.status_code == 200 and res.json().get("ok"):
            append_diag_log("🎉 SUCCESS: Telegram Alert Delivered to Phone!")
        else:
            append_diag_log(f"❌ API REJECTED: {res.text}")
    except Exception as e:
        append_diag_log(f"❌ EXCEPTION: {str(e)}")

def callback_test_gemini():
    append_diag_log("Action Triggered: Google Gemini API Test")
    gm_key = st.session_state.get('diag_gm_key', '')
    if not gm_key or "YOUR_" in str(gm_key):
        append_diag_log("❌ ERROR: Gemini API Key is missing in text box!")
    else:
        append_diag_log("Pinging Google AI Studio (Gemini 1.5 Flash)...")
        try:
            import google.generativeai as genai
            genai.configure(api_key=gm_key)
            start_t = time.time()
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content("Respond in 1 short sentence confirming ANTONY Quant Terminal connection.")
            latency = round((time.time() - start_t) * 1000, 2)
            append_diag_log(f"🎉 SUCCESS: Gemini Connected! Latency: {latency} ms")
            append_diag_log(f"🤖 Response: {res.text.strip()}")
        except Exception as e:
            append_diag_log(f"❌ GEMINI EXCEPTION: {str(e)}")

def callback_save_binance():
    append_diag_log("Action Triggered: Save Binance Keys")
    b_key = st.session_state.get('diag_b_key', '')
    b_sec = st.session_state.get('diag_b_sec', '')
    st.session_state['BINANCE_API_KEY'] = b_key
    st.session_state['BINANCE_API_SECRET'] = b_sec
    append_diag_log("✅ SUCCESS: Binance Keys saved to session state!")

def callback_test_binance():
    append_diag_log("Action Triggered: Binance API Connection Test")
    b_key = st.session_state.get('diag_b_key', '')
    b_sec = st.session_state.get('diag_b_sec', '')
    if not b_key or not b_sec:
        append_diag_log("❌ ERROR: Binance API Key or Secret Key is missing!")
    else:
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(b_sec.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            url = f"https://api.binance.com/api/v3/account?{query_string}&signature={signature}"
            headers = {"X-MBX-APIKEY": b_key}
            res = requests.get(url, headers=headers, timeout=5)
            append_diag_log(f"HTTP Response Code: {res.status_code}")
            res_data = res.json()
            if res.status_code == 200 and 'canTrade' in res_data:
                can_trade = res_data.get('canTrade', False)
                usdt_bal = "0.00"
                for b in res_data.get('balances', []):
                    if b.get('asset') == 'USDT':
                        usdt_bal = b.get('free', '0.00')
                        break
                append_diag_log(f"🎉 SUCCESS: Binance API Connected! Trading Permission: {'ENABLED' if can_trade else 'DISABLED'} | Live USDT Balance: ${float(usdt_bal):,.2f}")
            else:
                append_diag_log(f"❌ BINANCE REJECTED: {res_data.get('msg', res.text)}")
        except Exception as e:
            append_diag_log(f"❌ BINANCE EXCEPTION: {str(e)}")

# -------------------------------------------------------------
# MAIN TAB RENDERER
# -------------------------------------------------------------
def render_broker_integrator_tab():
    st.markdown("## 🔑 Broker API Integrator & Direct Diagnostic Center")
    st.info("🧪 **STATUS:** Paper Trading Test Active (Day 1 of 14). All execution is simulated with zero financial risk.")
    
    st.divider()

    # 1. TELEGRAM TESTER
    st.markdown("### 📲 Telegram Alert Bot Connection Tester")
    default_tg_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE")
    default_tg_chat = st.secrets.get("TELEGRAM_CHAT_ID", "1072750499")
    
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Telegram Bot Token", value=default_tg_token, type="password", key="diag_tg_token")
    with col2:
        st.text_input("Telegram Chat ID", value=default_tg_chat, key="diag_tg_chat")
    
    st.button("🚀 Test Telegram Connection & Send Live Message Now", on_click=callback_test_telegram, key="btn_run_tg_test", use_container_width=True)

    st.divider()

    # 2. GEMINI API TESTER
    st.markdown("### 🤖 Google AI Studio (Gemini 1.5/2.5 Flash API) Connection Tester")
    default_gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    st.text_input("Gemini API Key", value=default_gemini_key, type="password", key="diag_gm_key")
    
    st.button("🚀 Cross-Check Gemini API Key & Verify AI Connection", on_click=callback_test_gemini, key="btn_run_gm_test", use_container_width=True)

    st.divider()

    # 3. BINANCE API TESTER & SAVER
    st.markdown("### 🔒 Binance Crypto API Credentials & Live Connection Tester")
    st.text_input("Binance API Key", value=st.secrets.get("BINANCE_API_KEY", ""), type="password", key="diag_b_key")
    st.text_input("Binance API Secret", value=st.secrets.get("BINANCE_API_SECRET", ""), type="password", key="diag_b_sec")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.button("💾 Save Binance Keys", on_click=callback_save_binance, key="btn_run_b_save", use_container_width=True)
    with col_b2:
        st.button("🧪 Test Binance API Connection", on_click=callback_test_binance, key="btn_run_b_test", use_container_width=True)

    st.divider()

    # 4. REAL-TIME DIAGNOSTIC CONSOLE LOG BOX (ALWAYS VISIBLE!)
    st.markdown("### 🖥️ Real-Time Diagnostic Execution Console Log")
    
    logs_list = st.session_state.get('diagnostic_console_logs', ["Console initialized. Click any button above to see step-by-step live diagnostic logs."])
    logs_text = "\n".join(logs_list)
    st.code(logs_text, language="text")
    
    if st.button("🗑️ Clear Console Logs", key="btn_clear_diag_logs", use_container_width=True):
        st.session_state['diagnostic_console_logs'] = ["Console cleared. Ready for new test."]
        st.rerun()