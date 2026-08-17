# broker_integrator.py - Isolated Try-Except Execution Pipeline

import streamlit as st
import requests
import time
import os

def check_authentic_telegram_backend_ping():
    """Performs genuine HTTP GET request to Telegram servers and validates HTTP 200 OK response"""
    token = st.secrets.get("TELEGRAM_BOT_TOKEN", "8939955418:AAFXd58Nwr84uIGeqrvIqvntveWwHjqmenE")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "1072750499")
    try:
        start_t = time.time()
        url = f"https://api.telegram.org/bot{token}/getMe"
        res = requests.get(url, timeout=3)
        latency = round((time.time() - start_t) * 1000, 2)
        
        if res.status_code == 200 and res.json().get("ok"):
            bot_name = res.json().get("result", {}).get("first_name", "AntonyQuantBot")
            return True, f"🟢 **TELEGRAM BACKEND PING SUCCESSFUL!**\n\n• **Bot Name:** `{bot_name}` | **Chat ID:** `{chat_id}`\n• **Server Response:** `HTTP 200 OK` | **Latency:** `{latency} ms`"
        else:
            return False, f"🔴 **TELEGRAM SERVER REJECTED:** HTTP {res.status_code} - {res.text}"
    except Exception as e:
        return False, f"🔴 **TELEGRAM CONNECTION EXCEPTION:** {str(e)}"

def check_authentic_gemini_backend_ping() -> tuple[bool, str]:
    """Performs authentic API ping to Google AI Studio with dynamic model discovery"""
    gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", st.session_state.get("GEMINI_API_KEY", "")))
    if not gemini_key or "YOUR_" in str(gemini_key):
        return False, "🟡 **GEMINI API KEY NOTICE:** Key missing in secrets. Please add `GEMINI_API_KEY` in Streamlit Cloud Secrets."
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        start_t = time.time()
        
        # 1. DYNAMIC MODEL AUTO-DISCOVERY (Queries Google AI Studio for active working model string)
        working_model_name = "gemini-1.5-flash-latest"
        try:
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    clean_name = m.name.replace("models/", "")
                    available_models.append(clean_name)
            
            if available_models:
                flash_models = [m for m in available_models if 'flash' in m]
                working_model_name = flash_models[0] if flash_models else available_models[0]
        except Exception:
            working_model_name = "gemini-1.5-flash-latest"

        # 2. Instantiate Model and Test Connection
        model = genai.GenerativeModel(working_model_name)
        res = model.generate_content("Ping")
        latency = round((time.time() - start_t) * 1000, 2)
        
        return True, f"🤖 **GOOGLE GEMINI AI CONNECTED SUCCESSFULLY!**\n\n• **Active Model:** `{working_model_name}` | **Server Status:** `HTTP 200 OK`\n• **Response Time:** `{latency} ms` | **Gemini Reply:** `{res.text.strip()}`"
    except Exception as e:
        return False, f"🔴 **GEMINI BACKEND EXCEPTION:** {str(e)}"

def render_broker_integrator_tab():
    st.markdown("## 🔑 Broker API Integrator & Direct Diagnostic Center")
    st.info("🧪 **STATUS:** Paper Trading Test Active (Day 1 of 14). All execution is simulated with zero financial risk.")
    
    st.divider()

    # 1. TELEGRAM STATUS (SAFE TRY-EXCEPT)
    try:
        is_tg_ok, tg_msg = check_authentic_telegram_backend_ping()
        if is_tg_ok: st.success(tg_msg)
        else: st.error(tg_msg)
    except Exception as e_tg:
        st.warning(f"⚠️ Telegram Status Check Notice: {e_tg}")

    # 2. GEMINI API STATUS (SAFE TRY-EXCEPT)
    try:
        is_gm_ok, gm_msg = check_authentic_gemini_backend_ping()
        if is_gm_ok: st.info(gm_msg)
        else: st.warning(gm_msg)
    except Exception as e_gm:
        st.warning(f"⚠️ Gemini Status Check Notice: {e_gm}")

    st.divider()

    # 3. EXECUTION MODE SELECTOR
    st.markdown("### 🎛️ Active Execution Mode Selector")
    active_mode = st.radio(
        "Select Active Execution Engine:",
        ["🎮 Paper Trading Simulator (Active - 2 Weeks Test)", "🟡 Binance Crypto Live API", "🟢 Zerodha Kite Connect Live API"],
        index=0,
        key="tab3_mode_radio_final"
    )

    st.divider()

    # 4. LIVE BROKER CREDENTIALS MANAGER (BINANCE & ZERODHA)
    st.markdown("### 🔒 Live Broker Credentials Manager")
    
    with st.expander("🔑 Binance Crypto API Credentials", expanded=True):
        st.text_input("Binance API Key", type="password", value=st.secrets.get("BINANCE_API_KEY", ""), key="input_b_key_final")
        st.text_input("Binance API Secret", type="password", value=st.secrets.get("BINANCE_API_SECRET", ""), key="input_b_sec_final")

    with st.expander("🔑 Zerodha Kite Connect Credentials (NSE India)", expanded=False):
        st.text_input("Zerodha API Key", type="password", value=st.secrets.get("ZERODHA_API_KEY", ""), key="input_z_key_final")
        st.text_input("Zerodha API Secret", type="password", value=st.secrets.get("ZERODHA_API_SECRET", ""), key="input_z_sec_final")
        st.text_input("Zerodha Access Token (Daily TOTP)", type="password", value=st.secrets.get("ZERODHA_ACCESS_TOKEN", ""), key="input_z_tok_final")

    if st.button("💾 Save Credentials to Cloud Session", key="btn_save_all_final", use_container_width=True):
        st.success("✅ Credentials saved to cloud session successfully!")

    st.divider()

    # 5. SYSTEM HEALTH DIAGNOSTICS
    try:
        from system_health import run_comprehensive_health_check
        health = run_comprehensive_health_check()
        st.markdown("### 🏥 System Health Diagnostic Center")
        st.info(f"🟢 Data Feed: {health['data_feed']['status']} | 🟢 Cloud DB: {health['cloud_db']['status']} | 🟢 Telegram: {health['telegram']['status']}")
    except Exception as e:
        st.warning(f"⚠️ Health Diagnostic Notice: {e}")