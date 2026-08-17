# broker_integrator.py - Complete Fail-Safe API Diagnostic & Credentials Engine

import streamlit as st
import requests
import time
import hmac
import hashlib
import os

def test_telegram_connection(bot_token: str, chat_id: str) -> dict:
    """Tests Telegram Bot API credentials directly"""
    if not bot_token or "YOUR_" in str(bot_token) or not chat_id or "YOUR_" in str(chat_id):
        return {"status": "ERROR", "msg": "❌ Telegram Bot Token or Chat ID is missing!"}
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🔔 <b>ANTONY Quant AI Algo Terminal</b>\n\n✅ Live Connection Test Successful!\n⏱️ Heartbeat: Active.",
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200 and res.json().get("ok"):
            return {"status": "SUCCESS", "msg": "🎉 TELEGRAM CONNECTED SUCCESSFULLY! Live test message delivered to your phone. Check your Telegram App now!"}
        else:
            return {"status": "ERROR", "msg": f"❌ Telegram API Rejected ({res.status_code}): {res.text}"}
    except Exception as e:
        return {"status": "ERROR", "msg": f"❌ Connection Exception: {str(e)}"}

def test_gemini_connection(api_key: str) -> dict:
    """Tests Google AI Studio (Gemini 1.5/2.5 Flash API) key directly"""
    if not api_key or "YOUR_" in str(api_key):
        return {"status": "ERROR", "msg": "❌ Gemini API Key is missing! Please paste your key in the text box above first."}
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        start_t = time.time()
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content("Respond in 1 short sentence confirming ANTONY Quant Terminal connection.")
        latency = round((time.time() - start_t) * 1000, 2)
        
        return {"status": "SUCCESS", "msg": f"🎉 GOOGLE GEMINI 1.5/2.5 FLASH API CONNECTED! (Latency: {latency} ms)\n\n🤖 Gemini Response: {res.text.strip()}"}
    except Exception as e:
        return {"status": "ERROR", "msg": f"❌ Gemini API Error: {str(e)}"}

def test_binance_connection(api_key: str, api_secret: str) -> dict:
    """Tests Binance API credentials and fetches live USDT account balance"""
    if not api_key or not api_secret:
        return {"status": "ERROR", "msg": "❌ Binance API Key or Secret is missing! Please paste both above first."}
        
    try:
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}"
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        
        url = f"https://api.binance.com/api/v3/account?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": api_key}
        
        res = requests.get(url, headers=headers, timeout=5)
        res_data = res.json()
        
        if res.status_code == 200 and 'canTrade' in res_data:
            can_trade = res_data.get('canTrade', False)
            usdt_bal = "0.00"
            for b in res_data.get('balances', []):
                if b.get('asset') == 'USDT':
                    usdt_bal = b.get('free', '0.00')
                    break
            return {
                "status": "SUCCESS",
                "msg": f"🎉 BINANCE API CONNECTED SUCCESSFULLY!\n\n• Trading Permission: {'✅ ENABLED' if can_trade else '❌ DISABLED'}\n• Live USDT Free Balance: ${float(usdt_bal):,.2f} USDT"
            }
        else:
            return {"status": "ERROR", "msg": f"❌ Binance API Error ({res.status_code}): {res_data.get('msg', res.text)}"}
    except Exception as e:
        return {"status": "ERROR", "msg": f"❌ Connection Exception: {str(e)}"}

def render_broker_integrator_tab():
    """Renders Complete Broker Integrator Tab with Form Submission & Session State Persistence"""
    st.markdown("## 🔑 Broker API Integrator & Direct Diagnostic Center")
    st.info("🧪 **STATUS:** Paper Trading Test Active (Day 1 of 14). All execution is simulated with zero financial risk.")
    
    st.divider()

    # 1. TELEGRAM TESTER FORM
    st.markdown("### 📲 Telegram Alert Bot Connection Tester")
    with st.form(key="form_tg_integrator_v10"):
        col1, col2 = st.columns(2)
        with col1:
            default_tg_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE")
            tg_token = st.text_input("Telegram Bot Token", value=default_tg_token, type="password", key="input_tg_token_v10")
        with col2:
            default_tg_chat = st.secrets.get("TELEGRAM_CHAT_ID", "1072750499")
            tg_chat = st.text_input("Telegram Chat ID", value=default_tg_chat, key="input_tg_chat_v10")
        
        sub_tg = st.form_submit_button("🚀 Test Telegram Connection & Send Live Message Now", use_container_width=True)

    if sub_tg:
        with st.spinner("Pinging Telegram API & delivering live message..."):
            res = test_telegram_connection(tg_token, tg_chat)
            st.session_state['tg_persist_res'] = res

    if 'tg_persist_res' in st.session_state:
        res = st.session_state['tg_persist_res']
        if res['status'] == "SUCCESS":
            st.success(res['msg'])
        else:
            st.error(res['msg'])

    st.divider()

    # 2. GEMINI API TESTER FORM
    st.markdown("### 🤖 Google AI Studio (Gemini 1.5/2.5 Flash API) Connection Tester")
    with st.form(key="form_gemini_integrator_v10"):
        default_gemini_key = st.secrets.get("GEMINI_API_KEY", "")
        gm_key = st.text_input("Gemini API Key", value=default_gemini_key, type="password", key="input_gm_key_v10")
        sub_gm = st.form_submit_button("🚀 Cross-Check Gemini API Key & Verify AI Connection", use_container_width=True)

    if sub_gm:
        with st.spinner("Pinging Google AI Studio (Gemini 1.5/2.5 Flash API)..."):
            res = test_gemini_connection(gm_key)
            st.session_state['gm_persist_res'] = res

    if 'gm_persist_res' in st.session_state:
        res = st.session_state['gm_persist_res']
        if res['status'] == "SUCCESS":
            st.success(res['msg'])
        else:
            st.error(res['msg'])

    st.divider()

    # 3. BINANCE API CREDENTIALS & TESTER FORM
    st.markdown("### 🔒 Binance Crypto API Credentials & Live Connection Tester")
    with st.form(key="form_binance_integrator_v10"):
        b_key = st.text_input("Binance API Key", value=st.secrets.get("BINANCE_API_KEY", ""), type="password", key="input_b_key_v10")
        b_sec = st.text_input("Binance API Secret", value=st.secrets.get("BINANCE_API_SECRET", ""), type="password", key="input_b_sec_v10")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            save_b = st.form_submit_button("💾 Save Binance Keys", use_container_width=True)
        with col_b2:
            test_b = st.form_submit_button("🧪 Test Binance API Connection", use_container_width=True)

    if save_b:
        st.session_state['BINANCE_API_KEY'] = b_key
        st.session_state['BINANCE_API_SECRET'] = b_sec
        st.session_state['b_persist_res'] = {"status": "SUCCESS", "msg": "✅ Binance Keys saved to current session successfully!"}

    if test_b:
        with st.spinner("Authenticating with Binance API & fetching live account balance..."):
            res = test_binance_connection(b_key, b_sec)
            st.session_state['b_persist_res'] = res

    if 'b_persist_res' in st.session_state:
        res = st.session_state['b_persist_res']
        if res['status'] == "SUCCESS":
            st.success(res['msg'])
        else:
            st.error(res['msg'])

    st.divider()

    # 4. ZERODHA KITE CONNECT CREDENTIALS
    with st.expander("🔑 Zerodha Kite Connect Credentials (NSE India)", expanded=False):
        st.text_input("Zerodha API Key", type="password", value=st.secrets.get("ZERODHA_API_KEY", ""), key="input_z_key_v10")
        st.text_input("Zerodha API Secret", type="password", value=st.secrets.get("ZERODHA_API_SECRET", ""), key="input_z_sec_v10")
        st.text_input("Zerodha Access Token (Daily TOTP)", type="password", value=st.secrets.get("ZERODHA_ACCESS_TOKEN", ""), key="input_z_tok_v10")

    st.divider()

    # 5. SYSTEM HEALTH DIAGNOSTICS
    try:
        from system_health import run_comprehensive_health_check
        health = run_comprehensive_health_check()
        st.markdown("### 🏥 System Health Diagnostic Center")
        st.info(f"🟢 Data Feed: {health['data_feed']['status']} | 🟢 Cloud DB: {health['cloud_db']['status']} | 🟢 Telegram: {health['telegram']['status']}")
    except Exception as e:
        st.warning(f"⚠️ Health Diagnostic Notice: {e}")
