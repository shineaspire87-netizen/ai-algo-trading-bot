# multi_strategy.py - Institutional Bitcoin Multi-Factor Signal Decision Engine

import pandas as pd
import numpy as np
import ta
import datetime
import logging
import requests
import os
import yfinance as yf
import streamlit as st
from notifier import send_telegram_alert

# Import Core Quant Math Functions from Phase 1 Module
try:
    from quant_math_engine import (
        compute_weighted_obi,
        compute_spoofing_detection_ratio,
        compute_garman_klass_volatility,
        compute_spread_to_volatility_ratio,
        compute_oi_std_deviation_spike,
        compute_funding_zscore_mad,
        compute_hurst_exponent_rs,
        compute_bbwp
    )
except ImportError:
    logging.warning("quant_math_engine.py not found. Ensure Phase 1 file is saved!")

# -------------------------------------------------------------
# 1. MULTI-TIMEFRAME EMA HIERARCHY CASCADE (5m, 15m, 1h)
# -------------------------------------------------------------
def evaluate_multi_timeframe_cascade(df_5m: pd.DataFrame) -> dict:
    """Evaluates 3-Timeframe Hierarchical EMA Sorting (5m, 15m, 1h)"""
    if df_5m is None or len(df_5m) < 60:
        return {"cascade_status": "NEUTRAL", "allow_long": False, "allow_short": False}

    df = df_5m.copy()
    
    # 5-Min EMAs
    ema9_5m = ta.trend.ema_indicator(df['Close'], window=9).iloc[-1]
    ema21_5m = ta.trend.ema_indicator(df['Close'], window=21).iloc[-1]
    ema50_5m = ta.trend.ema_indicator(df['Close'], window=50).iloc[-1]
    
    # Resample 15-Min Bar Data
    df_15m = df.resample('15min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    if len(df_15m) >= 21:
        ema9_15m = ta.trend.ema_indicator(df_15m['Close'], window=9).iloc[-1]
        ema21_15m = ta.trend.ema_indicator(df_15m['Close'], window=21).iloc[-1]
    else:
        ema9_15m, ema21_15m = ema9_5m, ema21_5m

    # Resample 1-Hour Bar Data
    df_1h = df.resample('1h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    if len(df_1h) >= 50:
        ema9_1h = ta.trend.ema_indicator(df_1h['Close'], window=9).iloc[-1]
        ema21_1h = ta.trend.ema_indicator(df_1h['Close'], window=21).iloc[-1]
        ema50_1h = ta.trend.ema_indicator(df_1h['Close'], window=50).iloc[-1]
        
        # Check 1h EMA Spread Filter: |EMA21 - EMA50| / Close >= 0.0015
        ema_spread_1h = abs(ema21_1h - ema50_1h) / df_1h['Close'].iloc[-1]
        if ema_spread_1h < 0.0015:
            return {"cascade_status": "1H_FLAT_CONSOLIDATION_VETO", "allow_long": False, "allow_short": False}
    else:
        ema9_1h, ema21_1h, ema50_1h = ema9_5m, ema21_5m, ema50_5m

    # Hierarchical Cascade Rules
    long_cascade = (ema9_1h > ema21_1h > ema50_1h) and (ema9_15m > ema21_15m) and (ema9_5m > ema21_5m > ema50_5m) and (df['Close'].iloc[-1] > ema50_5m)
    short_cascade = (ema9_1h < ema21_1h < ema50_1h) and (ema9_15m < ema21_15m) and (ema9_5m < ema21_5m < ema50_5m) and (df['Close'].iloc[-1] < ema50_5m)

    if long_cascade:
        return {"cascade_status": "PERFECT_BULLISH_CASCADE_100%", "allow_long": True, "allow_short": False}
    elif short_cascade:
        return {"cascade_status": "PERFECT_BEARISH_CASCADE_100%", "allow_long": False, "allow_short": True}

    return {"cascade_status": "TIMEFRAME_DIVERGENCE_NEUTRAL", "allow_long": False, "allow_short": False}

# -------------------------------------------------------------
# 2. SWING FAILURE PATTERN (SFP) LIQUIDITY SWEEP TRAP DETECTOR
# -------------------------------------------------------------
def detect_liquidity_sweep_sfp_trap(df_5m: pd.DataFrame, pdh: float, pdl: float, atr_14: float) -> dict:
    """Detects Institutional Liquidity Sweeps above PDH or below PDL (Swing Failure Pattern)"""
    if len(df_5m) < 2:
        return {"is_sweep": False, "signal": "NONE", "boost": 0.0}

    last_candle = df_5m.iloc[-1]
    candle_range = last_candle['High'] - last_candle['Low'] + 1e-6
    body_size = abs(last_candle['Close'] - last_candle['Open'])
    
    body_ratio = body_size / candle_range
    vol_ma20 = df_5m['Volume'].rolling(20).mean().iloc[-1]
    vol_ratio = last_candle['Volume'] / (vol_ma20 + 1e-6)

    # 1. Bearish Liquidity Sweep (PDH Bull Trap SFP)
    spiked_pdh = last_candle['High'] > (pdh + 0.10 * atr_14)
    closed_inside_pdh = last_candle['Close'] < pdh
    upper_wick_ratio = (last_candle['High'] - max(last_candle['Open'], last_candle['Close'])) / candle_range

    if spiked_pdh and closed_inside_pdh and (upper_wick_ratio >= 0.45) and (body_ratio <= 0.40) and (vol_ratio >= 1.5):
        return {
            "is_sweep": True,
            "signal": "BUY_PUT",
            "boost": 0.15,
            "status": "🚨 SFP BEARISH LIQUIDITY SWEEP TRAP AT PDH (+15% AI Boost)"
        }

    # 2. Bullish Liquidity Sweep (PDL Bear Trap SFP)
    spiked_pdl = last_candle['Low'] < (pdl - 0.10 * atr_14)
    closed_inside_pdl = last_candle['Close'] > pdl
    lower_wick_ratio = (min(last_candle['Open'], last_candle['Close']) - last_candle['Low']) / candle_range

    if spiked_pdl and closed_inside_pdl and (lower_wick_ratio >= 0.45) and (body_ratio <= 0.40) and (vol_ratio >= 1.5):
        return {
            "is_sweep": True,
            "signal": "BUY_CALL",
            "boost": 0.15,
            "status": "🚀 SFP BULLISH LIQUIDITY SWEEP TRAP AT PDL (+15% AI Boost)"
        }

    return {"is_sweep": False, "signal": "NONE", "boost": 0.0}

# -------------------------------------------------------------
# 3. PREDICTIVE VCP SQUEEZE BREAKOUT TRIGGER
# -------------------------------------------------------------
def detect_predictive_vcp_breakout(df_5m: pd.DataFrame, bbwp_val: float, atr_14: float, obi_10: float) -> dict:
    """Predicts Volatility Contraction Breakout 1 Bar Before Full Expansion"""
    if len(df_5m) < 5:
        return {"is_vcp_predictive": False, "boost": 0.0}

    atr_5 = ta.volatility.average_true_range(df_5m['High'], df_5m['Low'], df_5m['Close'], window=5).iloc[-1]
    atr_50 = ta.volatility.average_true_range(df_5m['High'], df_5m['Low'], df_5m['Close'], window=50).iloc[-1]
    
    # VCP Squeeze Conditions: BBWP < 20th percentile AND ATR_5/ATR_50 < 0.80
    squeeze_active = (bbwp_val < 20.0) and (atr_5 / (atr_50 + 1e-6) < 0.80)
    
    # Predictive Trigger via Microstructure Orderbook Depth Bias
    if squeeze_active and (obi_10 > 0.33):
        return {
            "is_vcp_predictive": True,
            "signal": "BUY_CALL",
            "boost": 0.10,
            "status": "🎯 PREDICTIVE VCP BULLISH SQUEEZE TRIGGER (+10% AI Boost)"
        }
    elif squeeze_active and (obi_10 < -0.33):
        return {
            "is_vcp_predictive": True,
            "signal": "BUY_PUT",
            "boost": 0.10,
            "status": "🎯 PREDICTIVE VCP BEARISH SQUEEZE TRIGGER (+10% AI Boost)"
        }

    return {"is_vcp_predictive": False, "boost": 0.0, "status": "NORMAL"}

# -------------------------------------------------------------
# 4. MASTER MULTI-FACTOR SIGNAL DECISION MATRIX
# -------------------------------------------------------------
def evaluate_institutional_bitcoin_signals(df_5m: pd.DataFrame, asset_symbol: str = "BITCOIN", orderbook_bids: list = None, orderbook_asks: list = None) -> dict:
    """Evaluates All Microstructure Feeds with Priority Volume Override (Vol >= 1.15x)"""
    if df_5m is None or len(df_5m) < 20:
        return {"signal": "HOLD", "confidence": 0.50, "reason": "Insufficient candle history"}

    df = df_5m.copy()
    last_row = df.iloc[-1]

    # Calculate Indicators
    atr_14 = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14).iloc[-1]
    rsi_14 = ta.momentum.rsi(df['Close'], window=14).iloc[-1]
    
    adx_ind = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    adx_14 = adx_ind.adx().iloc[-1]

    vol_ma20 = df['Volume'].rolling(20).mean().iloc[-1]
    vol_ratio = last_row['Volume'] / (vol_ma20 + 1e-6)

    candle_range = last_row['High'] - last_row['Low'] + 1e-6
    body_ratio = abs(last_row['Close'] - last_row['Open']) / candle_range

    hurst_val = compute_hurst_exponent_rs(df['Close'], window=64)
    if hurst_val <= 0.05 or np.isnan(hurst_val):
        hurst_val = 0.55

    # 1. PRIORITY VOLUME OVERRIDE (Vol >= 1.15x immediately bypasses Hurst Chop Check)
    is_high_volume = vol_ratio >= 1.15

    if not is_high_volume and hurst_val < 0.42 and adx_14 < 20.0:
        return {
            "signal": "HOLD",
            "confidence": 0.45,
            "reason": f"⏸️ Low Volume ({vol_ratio:.2f}x) & Sideways Chop Range (H={hurst_val:.2f}). Waiting for Volume Spike."
        }

    # 2. EVALUATE BUY CALL / BUY PUT SIGNALS
    vwap_val = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    vwap_curr = vwap_val.iloc[-1]

    base_confidence = 0.55
    if body_ratio >= 0.60: base_confidence += 0.10
    if vol_ratio >= 1.15: base_confidence += 0.15
    if adx_14 >= 20.0: base_confidence += 0.10

    final_confidence = round(min(base_confidence, 0.95), 2)

    if last_row['Close'] > vwap_curr and rsi_14 <= 75.0 and is_high_volume:
        return {
            "signal": "BUY_CALL",
            "confidence": final_confidence,
            "reason": f"🔥 HIGH VOLUME BREAKOUT DETECTED: Vol {vol_ratio:.2f}x >= 1.15x | ADX {adx_14:.1f} | RSI {rsi_14:.1f}"
        }
    elif last_row['Close'] < vwap_curr and rsi_14 >= 25.0 and is_high_volume:
        return {
            "signal": "BUY_PUT",
            "confidence": final_confidence,
            "reason": f"🚨 HIGH VOLUME BREAKDOWN DETECTED: Vol {vol_ratio:.2f}x >= 1.15x | ADX {adx_14:.1f} | RSI {rsi_14:.1f}"
        }

    return {
        "signal": "HOLD",
        "confidence": final_confidence,
        "reason": f"⏸️ Waiting for VWAP Breakout Confirmation | Vol: {vol_ratio:.2f}x | RSI: {rsi_14:.1f}"
    }

# -------------------------------------------------------------
# 5. CROSS-COMPATIBILITY EXPORTS & HELPER BRIDGES
# -------------------------------------------------------------
def fetch_binance_orderbook_depth_ratio(symbol: str = "BTCUSDT") -> float:
    """Data Feed: Fetches Real-Time Order Book Depth & Calculates Buy Wall Ratio"""
    try:
        url = f"https://api.binance.com/api/v3/depth?symbol={symbol.upper()}&limit=20"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            bids = sum(float(b[1]) for b in data.get('bids', []))
            asks = sum(float(a[1]) for a in data.get('asks', []))
            total_vol = bids + asks
            if total_vol > 0:
                return round((bids / total_vol) * 100.0, 2)
    except Exception as e:
        logging.warning(f"Orderbook Depth Feed Warning: {e}")
    return 50.0

def evaluate_multi_timeframe_alignment(df_5m: pd.DataFrame) -> dict:
    """Data Feed: Evaluates Multi-Timeframe Trend Alignment (5m, 15m, 1h)"""
    if df_5m is None or len(df_5m) < 30:
        return {"is_aligned": False, "tf_trend": "NEUTRAL", "boost": 0.0}

    cascade = evaluate_multi_timeframe_cascade(df_5m)
    return {
        "is_aligned": cascade["allow_long"] or cascade["allow_short"],
        "tf_trend": cascade["cascade_status"],
        "boost": 0.15 if (cascade["allow_long"] or cascade["allow_short"]) else 0.0
    }

def detect_vcp_squeeze_contraction(df: pd.DataFrame) -> dict:
    """Detects Volatility Contraction Pattern (VCP)"""
    if len(df) < 5:
        return {"is_vcp": False, "score_boost": 0.0, "status": "NORMAL_RANGE"}
    r1 = float(df['High'].iloc[-3] - df['Low'].iloc[-3])
    r2 = float(df['High'].iloc[-2] - df['Low'].iloc[-2])
    r3 = float(df['High'].iloc[-1] - df['Low'].iloc[-1])
    is_contraction = (r3 < r2) and (r2 < r1)
    vol_ma20 = df['Volume'].rolling(20).mean().iloc[-1]
    is_low_vol = df['Volume'].iloc[-1] < vol_ma20
    if is_contraction and is_low_vol:
        return {"is_vcp": True, "score_boost": 0.10, "status": "🎯 VCP SQUEEZE DETECTED (+10% AI Confidence Boost)"}
    return {"is_vcp": False, "score_boost": 0.0, "status": "NORMAL_RANGE"}

def detect_liquidity_sweep_trap(df: pd.DataFrame, pdh: float, pdl: float) -> dict:
    """Institutional Liquidity Sweep Detection"""
    atr = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14).iloc[-1] if len(df) >= 14 else 100.0
    sfp = detect_liquidity_sweep_sfp_trap(df, pdh, pdl, atr)
    return {
        "signal": sfp.get("signal", "NONE"),
        "confidence_boost": sfp.get("boost", 0.0),
        "status": sfp.get("status", "NORMAL")
    }

def evaluate_pyramiding_scaling(current_gain_pct: float, vcp_active: bool) -> dict:
    """Zero-Risk Pyramiding Position Scaling Logic"""
    if current_gain_pct >= 0.06 and vcp_active:
        return {
            "allow_pyramiding": True,
            "additional_qty_pct": 0.50,
            "sl_action": "SHIFT_TO_BREAKEVEN",
            "status": "🔥 PYRAMIDING SCALING ACTIVE (Zero Risk Mode)"
        }
    return {"allow_pyramiding": False, "additional_qty_pct": 0.0, "sl_action": "NORMAL", "status": "NORMAL"}

def calculate_dynamic_atr_levels(df: pd.DataFrame, entry_price: float, signal_type: str, atr_multiplier_sl: float = 1.5, atr_multiplier_tp1: float = 1.5, atr_multiplier_tp2: float = 3.0):
    """Dynamic ATR-Based Stop Loss & Target Calculation"""
    atr = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14).iloc[-1]
    if signal_type == "BUY_CALL":
        sl = entry_price - (atr * atr_multiplier_sl)
        tp1 = entry_price + (atr * atr_multiplier_tp1)
        tp2 = entry_price + (atr * atr_multiplier_tp2)
    else:
        sl = entry_price + (atr * atr_multiplier_sl)
        tp1 = entry_price - (atr * atr_multiplier_tp1)
        tp2 = entry_price - (atr * atr_multiplier_tp2)
    return round(sl, 2), round(tp1, 2), round(tp2, 2), round(atr, 2)

def evaluate_soft_kill_switch_position_scaling(consecutive_losses: int):
    """Soft Kill-Switch: Position Sizing & Confidence Threshold Adjustment"""
    if consecutive_losses >= 2:
        return {
            "position_scale_factor": 0.50,
            "min_ai_confidence": 0.75,
            "required_adx": 28.0,
            "status": "SOFT_KILL_SWITCH_ACTIVE"
        }
    return {
        "position_scale_factor": 1.00,
        "min_ai_confidence": 0.70,
        "required_adx": 25.0,
        "status": "NORMAL"
    }

def evaluate_smart_breakout_signals(df: pd.DataFrame, asset_symbol: str) -> dict:
    """Smart Breakout Strategy Evaluator Bridge"""
    return evaluate_institutional_bitcoin_signals(df, asset_symbol)

def evaluate_smart_breakout_signals_v2(df: pd.DataFrame, asset_symbol: str) -> dict:
    """Smart Breakout v2 Strategy Evaluator Bridge"""
    return evaluate_institutional_bitcoin_signals(df, asset_symbol)

WATCHLIST = {
    "BITCOIN": "BTC-USD",
    "ETHEREUM": "ETH-USD",
    "BANKNIFTY": "^NSEBANK",
    "NIFTY50": "^NSEI",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",
    "SBIN": "SBIN.NS"
}

def scan_all_assets():
    """Autonomous Background Scanner Bridge"""
    results = []
    best_trade = None
    for name, sym in WATCHLIST.items():
        try:
            df = yf.download(sym, period="5d", interval="5m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df is not None and len(df) >= 30:
                sig_res = evaluate_institutional_bitcoin_signals(df, name)
                price = float(df['Close'].iloc[-1])
                results.append({"Name": name, "Price": price, "Signal": sig_res['signal']})
                if sig_res['signal'] != "HOLD" and best_trade is None:
                    best_trade = {"Name": name, "Price": price, "Signal": sig_res['signal']}
        except Exception:
            continue
    return best_trade, results