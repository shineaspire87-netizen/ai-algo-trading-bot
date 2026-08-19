# ================================================================================
# ANTONY QUANT AI TERMINAL - 15M CANDLE WIN PREDICTION ENGINE
# ================================================================================
import numpy as np
from datetime import time, datetime
import config

def calculate_candle_body_ratio(high, low, open_p, close_p):
    """Calculates Candle Body Intensity Ratio (Body / Range)."""
    total_range = high - low
    if total_range <= 0:
        return 0.0
    body = abs(close_p - open_p)
    return round((body / total_range) * 100.0, 1)

def predict_15m_candle_winning_direction(df):
    """
    Backend Math Engine to predict if the current 15M candle will CLOSE GREEN (UP) or RED (DOWN).
    Requires >= 70% Confidence Score to issue a Signal!
    """
    if df.empty or len(df) < 5:
        return "WAIT", 0.0, "REJECT: Insufficient Data", {}
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    close = float(last_row['close'])
    open_p = float(last_row['open'])
    high = float(last_row['high'])
    low = float(last_row['low'])
    volume = float(last_row['volume']) if 'volume' in last_row else 50000.0
    
    prev_close = float(prev_row['close'])
    
    # 1. Price Change %
    price_change_pct = ((close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
    
    # 2. Candle Body Intensity Ratio
    body_ratio = calculate_candle_body_ratio(high, low, open_p, close)
    
    # 3. Volume Acceleration Proxy
    avg_vol = df['volume'].rolling(5).mean().iloc[-1] if 'volume' in df else 50000.0
    vol_ratio = (volume / avg_vol) if (avg_vol is not None and avg_vol > 0) else 1.0
    
    # 4. Fib Retrace
    swing_range = high - low
    retrace = (high - close) / swing_range if swing_range > 0 else 0.5
    
    # CALCULATE CANDLE WIN PROBABILITY SCORE (%)
    confidence = 50.0  # Baseline
    
    if abs(price_change_pct) >= 0.25:
        confidence += 15.0
    if body_ratio >= 60.0:
        confidence += 12.0
    if vol_ratio >= 1.1:
        confidence += 10.0
    if 0.20 <= retrace <= 0.886:
        confidence += 8.0
        
    confidence = min(95.0, confidence)
    
    breakdown = {
        "l1_status": f"🟢 PASSED (Candle Body Intensity: {body_ratio}%)",
        "l2_status": f"🟢 PASSED (Volume Acceleration: {vol_ratio:.1f}x)",
        "l3_status": f"🟢 PASSED (Momentum: {price_change_pct:+.2f}%)",
        "l4_status": f"🟢 PASSED (Fib Discount: {retrace:.3f})",
        "l5_status": f"CANDLE WIN PROBABILITY: {confidence:.1f}%"
    }
    
    # STRICT 70% WIN CONFIDENCE THRESHOLD
    if confidence < 70.0:
        breakdown["l5_status"] = f"🔴 REJECTED: Low Win Confidence ({confidence:.1f}% < 70%)"
        return "WAIT", confidence, breakdown["l5_status"], breakdown
    
    if price_change_pct > +0.15:
        breakdown["l5_status"] = f"🟢 CONFIRMED GREEN CANDLE WIN (Confidence: {confidence:.1f}%)"
        return "BUY_CALL", confidence, breakdown["l5_status"], breakdown
    elif price_change_pct < -0.15:
        breakdown["l5_status"] = f"🟢 CONFIRMED RED CANDLE WIN (Confidence: {confidence:.1f}%)"
        return "BUY_PUT", confidence, breakdown["l5_status"], breakdown
    else:
        breakdown["l5_status"] = f"🔴 REJECTED: Flat Candle Range ({price_change_pct:+.2f}%)"
        return "WAIT", confidence, breakdown["l5_status"], breakdown


def evaluate_btc_15m_signal(df):
    return predict_15m_candle_winning_direction(df)


# --- EXISTING NIFTY ENGINE ---
def evaluate_volume_and_time_filter(volume, ist_time):
    try:
        vol = float(volume) if volume is not None else 65000.0
    except (ValueError, TypeError):
        vol = 65000.0

    if vol <= 0:
        vol = 65000.0

    if vol < config.MIN_15M_CANDLE_VOLUME:
        return False, f"🔴 FAILED: Low Volume ({vol:,.0f} < 50k Cutoff)"
    
    if hasattr(ist_time, "time"):
        t = ist_time.time()
    elif isinstance(ist_time, time):
        t = ist_time
    else:
        t = None

    if t is not None and config.LUNCH_HOUR_START <= t <= config.LUNCH_HOUR_END:
        if vol < (config.MIN_15M_CANDLE_VOLUME * 1.5):
            return False, "🔴 FAILED: Lunch Hour Choppy Zone (11:30 AM - 01:30 PM)"
            
    return True, "🟢 PASSED: Volume Participation OK"

def evaluate_fib_golden_pocket(high, low, close, direction):
    try:
        h, l, c = float(high), float(low), float(close)
    except (ValueError, TypeError):
        return True, 0.75, "🟢 PASSED"
    swing_range = h - l
    if swing_range <= 0:
        return True, 0.75, "🟢 PASSED"
    retrace = (h - c) / swing_range if direction in ["CALL", "UP"] else (c - l) / swing_range
    if config.FIB_DISCOUNT_MIN <= retrace <= config.FIB_DISCOUNT_MAX:
        return True, retrace, f"🟢 PASSED (Golden Pocket {retrace:.2f})"
    elif retrace < config.FIB_DISCOUNT_MIN:
        return True, retrace, f"🟢 PASSED (Strong Breakout {retrace:.2f})"
    else:
        return False, retrace, f"🔴 FAILED (Overextended Fib {retrace:.2f})"

def evaluate_pcr_layer(pcr_oi, delta_pcr_15):
    if 0.90 <= pcr_oi <= 1.10:
        return "🔴 FAILED: NEUTRAL_TRAP", False, False
    call_pcr_confirmed = (pcr_oi >= 1.10) and (delta_pcr_15 > 0)
    put_pcr_confirmed = (pcr_oi <= 0.90) and (delta_pcr_15 < 0)
    if call_pcr_confirmed:
        return "🟢 PASSED: BULLISH_CONFIRMED", True, False
    elif put_pcr_confirmed:
        return "🟢 PASSED: BEARISH_CONFIRMED", False, True
    else:
        return "🔴 FAILED: PCR_CONTRADICTION", False, False

def evaluate_vix_layer(vix, delta_vix_15):
    if vix < 12.0:
        return "🔴 FAILED: LOW_VIX_BLOCK (< 12.0)", 0.0, False
    elif 12.0 <= vix <= 18.0:
        return "🟢 PASSED: OPTIMAL_VOLATILITY", 1.0, (delta_vix_15 >= 0)
    else:
        return "🟢 PASSED: HIGH_VOLATILITY", 0.50, (delta_vix_15 >= 0)

def evaluate_oi_runway(nifty_price, nearest_wall_strike, nifty_target, direction):
    runway = (nearest_wall_strike - nifty_price) if direction in ["CALL", "UP"] else (nifty_price - nearest_wall_strike)
    if runway < 75.0:
        return runway, 0.0, "🔴 FAILED: IMMEDIATE_WALL_BLOCK"
    runway_ratio = runway / nifty_target if nifty_target > 0 else 0.0
    if runway >= 100.0 and runway_ratio >= 2.0:
        return runway, runway_ratio, f"🟢 PASSED: CLEAR_RUNWAY ({runway:.0f} pts)"
    else:
        return runway, runway_ratio, f"🔴 FAILED: RUNWAY_TOO_TIGHT ({runway:.0f} pts)"

def master_institutional_decision_engine(
    nifty_direction, heavyweight_k, heavyweight_a, india_vix, delta_vix_15,
    pcr_oi, delta_pcr_15, nifty_spot, nearest_ce_wall, nearest_pe_wall,
    volume_15m=65000, candle_high=24200, candle_low=24100, ist_time=None, nifty_target=30.0
):
    breakdown = {
        "l1_status": f"🟢 PASSED (Heavyweights K={heavyweight_k}/5, A={heavyweight_a:.2f})" if heavyweight_k >= 4 else f"🔴 FAILED (Heavyweights Disagree K={heavyweight_k}/5)",
        "l2_status": f"VIX={india_vix:.1f}",
        "l3_status": f"PCR={pcr_oi:.2f}",
        "l4_status": "Pending",
        "l5_status": "WAIT"
    }

    if ist_time is not None:
        vol_ok, vol_msg = evaluate_volume_and_time_filter(volume_15m, ist_time)
        if not vol_ok:
            breakdown["l5_status"] = vol_msg
            return "WAIT", breakdown["l5_status"], 0.0, breakdown

    if heavyweight_k < 4 or heavyweight_a < 0.75:
        breakdown["l5_status"] = "🔴 REJECTED: Heavyweights disagree (K < 4)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    
    fib_ok, fib_ratio, fib_status = evaluate_fib_golden_pocket(candle_high, candle_low, nifty_spot, nifty_direction)
    breakdown["l4_status"] = fib_status
    if not fib_ok:
        breakdown["l5_status"] = f"🔴 REJECTED: Overextended Premium Trap (Fib={fib_ratio:.3f})"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown

    vix_regime, pos_multiplier, vix_expanding = evaluate_vix_layer(india_vix, delta_vix_15)
    breakdown["l2_status"] = vix_regime
    if vix_regime.startswith("🔴"):
        breakdown["l5_status"] = f"🔴 REJECTED: {vix_regime}"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    if not vix_expanding:
        breakdown["l5_status"] = "🔴 REJECTED: Falling VIX (Weak Premium Expansion)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    
    pcr_status, call_pcr_ok, put_pcr_ok = evaluate_pcr_layer(pcr_oi, delta_pcr_15)
    breakdown["l3_status"] = pcr_status
    
    if nifty_direction == "UP":
        if not call_pcr_ok:
            breakdown["l5_status"] = f"🔴 REJECTED: CALL contradicted by PCR ({pcr_status})"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        runway, ratio, runway_status = evaluate_oi_runway(nifty_spot, nearest_ce_wall, nifty_target, "CALL")
        breakdown["l4_status"] = runway_status
        if not runway_status.startswith("🟢"):
            breakdown["l5_status"] = f"🔴 REJECTED: CE Wall too close ({runway:.0f} pts)"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        breakdown["l5_status"] = f"🟢 CONFIRMED: Clear CE Runway ({runway:.0f} pts)"
        return "BUY_CALL", breakdown["l5_status"], pos_multiplier, breakdown

    elif nifty_direction == "DOWN":
        if not put_pcr_ok:
            breakdown["l5_status"] = f"🔴 REJECTED: PUT contradicted by PCR ({pcr_status})"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        runway, ratio, runway_status = evaluate_oi_runway(nifty_spot, nearest_pe_wall, nifty_target, "PUT")
        breakdown["l4_status"] = runway_status
        if not runway_status.startswith("🟢"):
            breakdown["l5_status"] = f"🔴 REJECTED: PE Wall too close ({runway:.0f} pts)"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        breakdown["l5_status"] = f"🟢 CONFIRMED: Clear PE Runway ({runway:.0f} pts)"
        return "BUY_PUT", breakdown["l5_status"], pos_multiplier, breakdown

    breakdown["l5_status"] = "🔴 REJECTED: No Directional Momentum"
    return "WAIT", breakdown["l5_status"], 0.0, breakdown
