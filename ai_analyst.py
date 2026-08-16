# ai_analyst.py - Google AI Studio Gemini Integration

import google.generativeai as genai
import streamlit as st
import os

# Read API Key
try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = ""

gemini_key_from_secrets = ""
try:
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        gemini_key_from_secrets = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

GEMINI_KEY = gemini_key_from_secrets or os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)

if GEMINI_KEY and GEMINI_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_KEY)

def ask_gemini_trade_validation(asset_symbol: str, option_type: str, rsi_val: float, vwap_dist: float, candle_body: float) -> dict:
    """Ask Gemini 2.5 Flash to validate if taking PUT/CALL is a trap or good entry"""
    if not GEMINI_KEY or GEMINI_KEY == "your_gemini_api_key_here":
        return {"decision": "APPROVED", "reason": "Gemini API Key missing, falling back to indicator rules."}

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        You are an expert Institutional Options Scalper for {asset_symbol}.
        Evaluate this signal: BUY {option_type}
        - Current RSI (14): {rsi_val:.1f}
        - Distance from VWAP: {vwap_dist:.2f}%
        - Candle Body Range Ratio: {candle_body:.2f}
        
        RULES:
        1. Reject BUY PUT if RSI < 35 (Overbought at Support, risk of rebound).
        2. Reject BUY CALL if RSI > 65 (Overbought at Resistance).
        
        Respond in JSON: {{"decision": "APPROVED" or "REJECTED", "reason": "Short explanation in Tamil"}}
        """

        response = model.generate_content(prompt)
        text_content = response.text.strip()
        # Clean any markdown block wrappers
        if text_content.startswith("```"):
            lines = text_content.split("\n")
            if len(lines) > 2:
                # Remove starting ```json or ``` and ending ```
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                text_content = "\n".join(lines).strip()
            else:
                text_content = text_content.replace("```json", "").replace("```", "").strip()

        import json
        result = json.loads(text_content)
        return result

    except Exception as e:
        return {"decision": "APPROVED", "reason": f"Gemini Analysis Error Fallback: {e}"}
