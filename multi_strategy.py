# multi_strategy.py - With Direct Telegram Mobile Alerts & Hurst Engine
import os
import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import ta
import numpy as np
from xgboost import XGBClassifier
from notifier import send_telegram_alert

MODEL_FILE = "xgboost_model.json"
model = None

if os.path.exists(MODEL_FILE):
    model = XGBClassifier()
    model.load_model(MODEL_FILE)

def detect_vcp_squeeze_contraction(df: pd.DataFrame) -> dict:
    """Detects Volatility Contraction Pattern (VCP) - Shrinking Range Before Explosive Breakout"""
    if len(df) < 5:
        return {"is_vcp": False, "score_boost": 0.0, "status": "NORMAL_RANGE"}

    # Calculate Candle Ranges for last 3 bars
    r1 = float(df['High'].iloc[-3] - df['Low'].iloc[-3])
    r2 = float(df['High'].iloc[-2] - df['Low'].iloc[-2])
    r3 = float(df['High'].iloc[-1] - df['Low'].iloc[-1])

    # VCP Rule: Volatility is shrinking (r3 < r2 < r1)
    is_contraction = (r3 < r2) and (r2 < r1)
    
    # Volume Contraction Check
    vol_ma20 = df['Volume'].rolling(20).mean().iloc[-1]
    is_low_vol = df['Volume'].iloc[-1] < vol_ma20

    # If VCP Squeeze is detected, boost AI Confidence score by +10%
    if is_contraction and is_low_vol:
        return {"is_vcp": True, "score_boost": 0.10, "status": "🎯 VCP SQUEEZE DETECTED (+10% AI Confidence Boost)"}
        
    return {"is_vcp": False, "score_boost": 0.0, "status": "NORMAL_RANGE"}

def detect_liquidity_sweep_trap(df: pd.DataFrame, pdh: float, pdl: float) -> dict:
    """Detects Institutional Liquidity Sweeps above PDH or below PDL for High-Probability Reversals"""
    if df is None or len(df) < 2:
        return {"signal": "NONE", "confidence_boost": 0.0, "status": "NORMAL"}

    last_candle = df.iloc[-1]
    candle_range = last_candle['High'] - last_candle['Low'] + 1e-6

    # 1. Bearish Liquidity Sweep (Spiked above PDH but closed inside range with long upper wick)
    if last_candle['High'] > pdh and last_candle['Close'] < pdh:
        upper_wick = last_candle['High'] - max(last_candle['Open'], last_candle['Close'])
        if (upper_wick / candle_range) >= 0.40: # Long Upper Wick Trap
            return {
                "signal": "BUY_PUT",
                "confidence_boost": 0.15,
                "status": "🚨 BEARISH LIQUIDITY SWEEP TRAP AT PDH (+15% AI Boost)"
            }

    # 2. Bullish Liquidity Sweep (Spiked below PDL but closed inside range with long lower wick)
    if last_candle['Low'] < pdl and last_candle['Close'] > pdl:
        lower_wick = min(last_candle['Open'], last_candle['Close']) - last_candle['Low']
        if (lower_wick / candle_range) >= 0.40: # Long Lower Wick Trap
            return {
                "signal": "BUY_CALL",
                "confidence_boost": 0.15,
                "status": "🚀 BULLISH LIQUIDITY SWEEP TRAP AT PDL (+15% AI Boost)"
            }

    return {"signal": "NONE", "confidence_boost": 0.0, "status": "NORMAL"}

def evaluate_pyramiding_scaling(current_gain_pct: float, vcp_active: bool) -> dict:
    """Zero-Risk Pyramiding Position Scaling Logic"""
    # Trigger Pyramiding only if Target 1 (+6%) is hit and VCP Momentum is present
    if current_gain_pct >= 0.06 and vcp_active:
        return {
            "allow_pyramiding": True,
            "additional_qty_pct": 0.50, # Add 50% additional scaling lot
            "sl_action": "SHIFT_TO_BREAKEVEN",
            "status": "🔥 PYRAMIDING SCALING ACTIVE (Zero Risk Mode)"
        }
    return {"allow_pyramiding": False, "additional_qty_pct": 0.0, "sl_action": "NORMAL", "status": "NORMAL"}

def evaluate_smart_breakout_signals(df: pd.DataFrame, asset_symbol: str) -> dict:
    """Smart ATR Volatility Expansion & Friction Filter Strategy Engine"""
    if df is None or len(df) < 20:
        return {"signal": "HOLD", "confidence": 0.50, "reason": "Insufficient candle data for analysis"}

    df = df.copy()
    last_row = df.iloc[-1]

    # 1. Ezekiel Chew Candle Body Ratio Filter (>= 60%)
    candle_range = last_row['High'] - last_row['Low'] + 1e-6
    body_size = abs(last_row['Close'] - last_row['Open'])
    body_ratio = body_size / candle_range

    if body_ratio < 0.60:
        return {"signal": "HOLD", "confidence": 0.50, "reason": f"⚠️ Body ratio {body_ratio:.2f} < 0.60 (Weak Wick / Doji Candle Rejected)"}

    # 2. ADX Trend Strength Filter (> 22.0) - Rejects Dead Sideways Chop
    adx_ind = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    adx_val = adx_ind.adx().iloc[-1]
    if adx_val < 22.0:
        return {"signal": "HOLD", "confidence": 0.50, "reason": f"⚠️ ADX {adx_val:.1f} < 22.0 (Dead Sideways Chop - Signal Rejected)"}

    # 3. Volume Spike Filter (>= 1.20x 20-MA)
    vol_ma20 = df['Volume'].rolling(20).mean().iloc[-1]
    vol_ratio = last_row['Volume'] / (vol_ma20 + 1e-6)
    if vol_ratio < 1.20:
        return {"signal": "HOLD", "confidence": 0.50, "reason": f"⚠️ Volume {vol_ratio:.2f}x < 1.20x Average (Low Institutional Volume)"}

    # 4. Minimum Volatility Threshold (Expected Move > Brokerage Friction ₹50)
    atr_val = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14).iloc[-1]
    min_required_atr = last_row['Close'] * 0.0015 # Minimum 0.15% Move Requirement
    if atr_val < min_required_atr:
        return {"signal": "HOLD", "confidence": 0.50, "reason": f"⚠️ ATR {atr_val:.2f} < Volatility Threshold (Potential Brokerage Fee Trap)"}

    # 5. EMA 9/21 Trend & VWAP Direction Alignment
    ema9 = ta.trend.ema_indicator(df['Close'], window=9).iloc[-1]
    ema21 = ta.trend.ema_indicator(df['Close'], window=21).iloc[-1]
    vwap_series = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    vwap_curr = vwap_series.iloc[-1]

    # BUY CALL Condition
    if last_row['Close'] > vwap_curr and ema9 > ema21 and last_row['Close'] > last_row['Open']:
        return {
            "signal": "BUY_CALL",
            "confidence": 0.72,
            "reason": f"🚀 High-Conviction Bullish Breakout: Body {body_ratio:.2f} | ADX {adx_val:.1f} | Vol {vol_ratio:.2f}x | ATR {atr_val:.2f}"
        }

    # BUY PUT Condition
    if last_row['Close'] < vwap_curr and ema9 < ema21 and last_row['Close'] < last_row['Open']:
        return {
            "signal": "BUY_PUT",
            "confidence": 0.72,
            "reason": f"🚨 High-Conviction Bearish Breakdown: Body {body_ratio:.2f} | ADX {adx_val:.1f} | Vol {vol_ratio:.2f}x | ATR {atr_val:.2f}"
        }

    return {"signal": "HOLD", "confidence": 0.50, "reason": "⏸️ Waiting for clear VWAP/EMA Trend Breakout"}

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

last_notified_signal = {}

def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    open_p, high_p, low_p, close_p = df['Open'], df['High'], df['Low'], df['Close']
    body = abs(close_p - open_p)
    candle_range = (high_p - low_p).replace(0, 0.001)
    
    df['Pattern_Doji'] = (body <= (candle_range * 0.1)).astype(int)
    df['Pattern_Marubozu'] = (body >= (candle_range * 0.85)).astype(int)
    lower_shadow = np.minimum(open_p, close_p) - low_p
    df['Pattern_Hammer'] = ((lower_shadow >= (body * 2)) & (body > 0)).astype(int)
    upper_shadow = high_p - np.maximum(open_p, close_p)
    df['Pattern_ShootingStar'] = ((upper_shadow >= (body * 2)) & (body > 0)).astype(int)
    df['Pattern_BullishEngulfing'] = ((close_p > open_p) & (close_p.shift(1) < open_p.shift(1)) & (close_p >= open_p.shift(1))).astype(int)
    df['Pattern_BearishEngulfing'] = ((close_p < open_p) & (close_p.shift(1) > open_p.shift(1)) & (close_p <= open_p.shift(1))).astype(int)
    return df

def calculate_daily_reset_vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3.0
    vol = df['Volume'].replace(0, np.nan).fillna(1)
    vol_price = typical_price * vol
    dates = df.index.date
    cum_vol_price = vol_price.groupby(dates).cumsum()
    cum_vol = vol.groupby(dates).cumsum()
    vwap = cum_vol_price / cum_vol
    return vwap.fillna(typical_price)

def calculate_garman_klass_volatility(df: pd.DataFrame, window: int = 14) -> pd.Series:
    log_hl = np.log(df['High'] / df['Low']) ** 2
    log_co = np.log(df['Close'] / df['Open']) ** 2
    gk = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co
    return np.sqrt(gk.rolling(window).mean()).fillna(0)

def scan_all_assets():
    now_dt = datetime.datetime.now()
    now_time = now_dt.time()
    today_weekday = now_dt.weekday()
    
    best_opportunity = None
    scanned_results = []

    for name, symbol in WATCHLIST.items():
        is_crypto = "USD" in symbol
        is_market_open = (today_weekday < 5 and datetime.time(9, 15) <= now_time <= datetime.time(15, 30)) or is_crypto

        if not is_market_open:
            continue

        try:
            df = yf.download(tickers=symbol, period="5d", interval="5m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Calculate Previous Day High (PDH) and Low (PDL) for sweep detection
            try:
                daily_df = yf.download(tickers=symbol, period="5d", interval="1d", progress=False)
                if isinstance(daily_df.columns, pd.MultiIndex):
                    daily_df.columns = daily_df.columns.get_level_values(0)
                pdh_val = float(daily_df['High'].iloc[-2]) if len(daily_df) >= 2 else float(df['High'].max())
                pdl_val = float(daily_df['Low'].iloc[-2]) if len(daily_df) >= 2 else float(df['Low'].min())
            except Exception:
                pdh_val = float(df['High'].max()) if not df.empty else 0.0
                pdl_val = float(df['Low'].min()) if not df.empty else 0.0

            if df.empty or len(df) < 25:
                continue

            df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
            df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
            df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
            df['EMA_Diff'] = (df['EMA_9'] - df['EMA_21']) / df['EMA_21']
            
            adx_ind = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
            df['ADX'] = adx_ind.adx()
            
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            df['ATR_Pct'] = (df['ATR'] / df['Close']) * 100.0
            df['GK_Volatility'] = calculate_garman_klass_volatility(df, window=14)
            
            df['VWAP'] = calculate_daily_reset_vwap(df)
            df['VWAP_Diff'] = (df['Close'] - df['VWAP']) / df['VWAP']
            
            bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
            df['BB_Width'] = bb.bollinger_wband()
            df['BB_Pband'] = bb.bollinger_pband()

            df['Hour'] = df.index.hour
            df['Minute'] = df.index.minute
            df['Is_Morning_Open'] = ((df['Hour'] == 9) & (df['Minute'] >= 15) | (df['Hour'] == 10)).astype(int)
            df['Is_Lunch_Chop'] = ((df['Hour'] >= 11) & (df['Hour'] <= 13)).astype(int)
            df['Is_Power_Hour'] = ((df['Hour'] == 14) | ((df['Hour'] == 15) & (df['Minute'] <= 15))).astype(int)

            df['Return_1'] = df['Close'].pct_change(1)
            df['Return_3'] = df['Close'].pct_change(3)

            df = detect_candlestick_patterns(df)
            latest = df.iloc[-1]

            if model is not None:
                features = pd.DataFrame([{
                    'RSI': latest['RSI'],
                    'EMA_Diff': latest['EMA_Diff'],
                    'ADX': latest['ADX'],
                    'ATR_Pct': latest['ATR_Pct'],
                    'GK_Volatility': latest['GK_Volatility'],
                    'VWAP_Diff': latest['VWAP_Diff'],
                    'BB_Width': latest['BB_Width'],
                    'BB_Pband': latest['BB_Pband'],
                    'Return_1': latest['Return_1'],
                    'Return_3': latest['Return_3'],
                    'Is_Morning_Open': latest['Is_Morning_Open'],
                    'Is_Lunch_Chop': latest['Is_Lunch_Chop'],
                    'Is_Power_Hour': latest['Is_Power_Hour'],
                    'Pattern_Doji': latest['Pattern_Doji'],
                    'Pattern_Marubozu': latest['Pattern_Marubozu'],
                    'Pattern_Hammer': latest['Pattern_Hammer'],
                    'Pattern_ShootingStar': latest['Pattern_ShootingStar'],
                    'Pattern_BullishEngulfing': latest['Pattern_BullishEngulfing'],
                    'Pattern_BearishEngulfing': latest['Pattern_BearishEngulfing']
                }]).fillna(0)

                probs = model.predict_proba(features)[0]
                max_prob = np.max(probs)
                pred = model.predict(features)[0]

                # VCP Contraction Boost
                vcp_res = detect_vcp_squeeze_contraction(df)
                if vcp_res["is_vcp"]:
                    max_prob = min(1.0, max_prob + vcp_res["score_boost"])

                # Liquidity Sweep Boost
                sweep_res = detect_liquidity_sweep_trap(df, pdh_val, pdl_val)
                if sweep_res["signal"] != "NONE":
                    max_prob = min(1.0, max_prob + sweep_res["confidence_boost"])

                if max_prob >= 0.70:
                    signal = "BUY_CALL" if pred == 2 else ("BUY_PUT" if pred == 0 else "HOLD")
                else:
                    signal = "HOLD"
            else:
                signal = "BUY_CALL" if (latest['EMA_9'] > latest['EMA_21'] and latest['RSI'] > 58) else ("BUY_PUT" if (latest['EMA_9'] < latest['EMA_21'] and latest['RSI'] < 42) else "HOLD")

            gemini_reason = ""
            if signal != "HOLD":
                from ai_analyst import ask_gemini_trade_validation
                opt_type = "CALL" if signal == "BUY_CALL" else "PUT"
                vwap_dist = float(latest['VWAP_Diff'] * 100.0)
                body = abs(latest['Close'] - latest['Open'])
                candle_range = max(0.001, (latest['High'] - latest['Low']))
                body_ratio = float(body / candle_range)
                
                gemini_res = ask_gemini_trade_validation(name, opt_type, float(latest['RSI']), vwap_dist, body_ratio)
                
                if gemini_res.get("decision") == "APPROVED":
                    gemini_reason = gemini_res.get("reason", "Approved by Gemini AI.")
                    print(f"✅ Gemini Approved {signal} for {name}: {gemini_reason}")
                else:
                    gemini_reason = gemini_res.get("reason", "Rejected by Gemini AI.")
                    print(f"⚠️ Gemini Rejected {signal} for {name}: {gemini_reason}")
                    signal = "HOLD"

            if signal != "HOLD" and last_notified_signal.get(name) != signal:
                last_notified_signal[name] = signal
                alert_msg = f"🚨 <b>AI TRADE SIGNAL DETECTED!</b>\n\n<b>Asset:</b> {name}\n<b>Signal:</b> {signal}\n<b>Live Price:</b> {latest['Close']:,.2f}\n<b>RSI:</b> {latest['RSI']:.1f}\n<b>Gemini Validation:</b> {gemini_reason}\n<b>Time:</b> {now_dt.strftime('%H:%M:%S IST')}"
                send_telegram_alert(alert_msg)

            scanned_results.append({
                "Name": name, "Symbol": symbol, "Price": latest['Close'], "RSI": latest['RSI'], "Signal": signal
            })

            if signal != "HOLD" and best_opportunity is None:
                best_opportunity = {"Name": name, "Symbol": symbol, "Price": latest['Close'], "Signal": signal}

        except Exception as e:
            continue

    return best_opportunity, scanned_results

def is_daily_limit_reached(completed_trades_count: int) -> bool:
    """Check if 3 trades daily limit is reached (Bypassed if Extended Testing Mode is ON)"""
    
    # Check if user enabled the temporary testing toggle in Dashboard
    is_testing_mode_on = st.session_state.get('allow_extended_trades', False)
    
    if is_testing_mode_on:
        # Testing Mode is ON -> Allow scanning beyond 3 trades
        return False
        
    # Default Safe Mode -> Hard Lock at 3 completed trades
    return completed_trades_count >= 3

def is_safe_entry_window_in_candle() -> bool:
    """Ensure entry happens only between 2nd and 4th minute of the 5-min candle (60s to 240s)"""
    current_second = datetime.datetime.now().second + (datetime.datetime.now().minute % 5) * 60
    
    # 60 seconds <= current_second <= 240 seconds (Safest Entry Zone)
    if 60 <= current_second <= 240:
        return True
        
    return False # Rejects entry in 1st minute and last 1 minute of the candle

def calculate_dynamic_atr_levels(df: pd.DataFrame, entry_price: float, signal_type: str, atr_multiplier_sl: float = 1.5, atr_multiplier_tp1: float = 1.5, atr_multiplier_tp2: float = 3.0):
    """Dynamic ATR-Based Stop Loss & Target Calculation"""
    df = df.copy()
    atr = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14).iloc[-1]
    
    if signal_type == "BUY_CALL":
        sl = entry_price - (atr * atr_multiplier_sl)
        tp1 = entry_price + (atr * atr_multiplier_tp1)
        tp2 = entry_price + (atr * atr_multiplier_tp2)
    else: # BUY_PUT
        sl = entry_price + (atr * atr_multiplier_sl)
        tp1 = entry_price - (atr * atr_multiplier_tp1)
        tp2 = entry_price - (atr * atr_multiplier_tp2)
        
    return round(sl, 2), round(tp1, 2), round(tp2, 2), round(atr, 2)

def evaluate_soft_kill_switch_position_scaling(consecutive_losses: int):
    """Soft Kill-Switch: Position Sizing & Confidence Threshold Adjustment"""
    if consecutive_losses >= 2:
        # Soft Lock: Scale Position Size to 50% & Require 75% AI Confidence
        return {
            "position_scale_factor": 0.50, # 50% Position Size
            "min_ai_confidence": 0.75,     # Higher Bar for 3rd Trade (75%)
            "required_adx": 28.0,          # Strong Trend Only
            "status": "SOFT_KILL_SWITCH_ACTIVE"
        }
    return {
        "position_scale_factor": 1.00,
        "min_ai_confidence": 0.70,
        "required_adx": 25.0,
        "status": "NORMAL"
    }

def is_safe_mid_candle_window() -> bool:
    """Rule #4: Safest Entry Window (2nd to 4th minute inside 5-min candle: 60s to 240s)"""
    now = datetime.datetime.now()
    second_in_candle = now.second + (now.minute % 5) * 60
    return 60 <= second_in_candle <= 240