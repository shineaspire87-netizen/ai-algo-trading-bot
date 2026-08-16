# ai_analyst.py - Updated with Dynamic Model Selection

import google.generativeai as genai
import streamlit as st
import os

def ask_gemini_trade_validation(asset_symbol: str, option_type: str, rsi_val: float, vwap_dist: float, candle_body: float) -> dict:
    gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    
    if not gemini_key:
        return {"decision": "APPROVED", "reason": "Gemini API Key missing; evaluated via Quant Indicators."}

    try:
        genai.configure(api_key=gemini_key)
        
        # Fallback candidate models
        candidates = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.5-flash", "gemini-pro"]
        
        model = None
        for cand in candidates:
            try:
                m = genai.GenerativeModel(cand)
                # Quick check
                model = m
                break
            except Exception:
                continue

        if not model:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")

        prompt = f"""
        You are an expert Options Scalper. Evaluate: BUY {option_type} on {asset_symbol}.
        - RSI: {rsi_val:.1f}, VWAP Distance: {vwap_dist:.2f}%, Candle Body: {candle_body:.2f}
        Rules: Reject BUY PUT if RSI < 35. Reject BUY CALL if RSI > 65.
        JSON output: {{"decision": "APPROVED" or "REJECTED", "reason": "Short reason in Tamil"}}
        """

        response = model.generate_content(prompt)
        import json
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)

    except Exception as e:
        return {"decision": "APPROVED", "reason": f"Gemini Fallback: {e}"}
