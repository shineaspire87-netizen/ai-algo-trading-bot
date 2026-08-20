# ================================================================================
# ANTONY QUANT AI TERMINAL - 15M CANDLE WIN PREDICTION ENGINE
# ================================================================================
import numpy as np
from datetime import datetime, time
import config

def calculate_candle_body_ratio(high, low, open_p, close_p):
    total_range = high - low
    if total_range <= 0:
        return 0.0
    body = abs(close_p - open_p)
    return round((body / total_range) * 100.0, 1)

def predict_15m_candle_winning_direction(df):
    """
    Evaluates Bitcoin 15M Candlestick Signal with STRICT DYNAMIC 🟢 PASSED / 🔴 FAILED Badges.
    """
    if df.empty or len(df) < 5:
        return "WAIT", 0.0, "REJECT: Insufficient Data", {}
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    close = float(last_row['close'])
    open_p = float(last_row['open'])
    high = float(last_row['high'])
    low = float(last_row['low'])
    volume = float(last_row['volume']) if 'volume' in last_row and float(last_row['volume']) > 0 else 50000.0
    
    prev_close = float(prev_row['close'])
    price_change_pct = ((close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
    
    # 1. Body Ratio
    body_ratio = calculate_candle_body_ratio(high, low, open_p, close)
    l1_passed = body_ratio >= 50.0
    l1_str = f"🟢 PASSED (Body Intensity: {body_ratio}%)" if l1_passed else f"🔴 FAILED (Low Body Intensity: {body_ratio}% < 50%)"
    
    # 2. Volume Acceleration
    avg_vol = df['volume'].rolling(5).mean().iloc[-1] if 'volume' in df and df['volume'].iloc[-1] > 0 else 50000.0
    vol_ratio = (volume / avg_vol) if avg_vol > 0 else 1.0
    l2_passed = vol_ratio >= 1.0
    l2_str = f"🟢 PASSED (Volume Acceleration: {vol_ratio:.1f}x)" if l2_passed else f"🔴 FAILED (Low Volume Accel: {vol_ratio:.1f}x < 1.0x)"
    
    # 3. Momentum Delta %
    l3_passed = abs(price_change_pct) >= 0.15
    l3_str = f"🟢 PASSED (15M Momentum: {price_change_pct:+.2f}%)" if l3_passed else f"🔴 FAILED (Weak Momentum: {price_change_pct:+.2f}% < 0.15%)"
    
    # 4. Fib Retrace Guard
    swing_range = high - low
    retrace = (high - close) / swing_range if swing_range > 0 else 0.5
    l4_passed = retrace <= 0.886
    l4_str = f"🟢 PASSED (Fib Discount: {retrace:.3f})" if l4_passed else f"🔴 FAILED (Overextended Fib: {retrace:.3f} > 0.886)"
    
    # 5. Calculate Candle Win Confidence Score (%)
    confidence = 50.0
    if abs(price_change_pct) >= 0.25: confidence += 15.0
    if l1_passed: confidence += 12.0
    if l2_passed: confidence += 10.0
    if l4_passed: confidence += 8.0
    confidence = float(min(95.0, confidence))
    
    l5_passed = confidence >= 70.0 and l1_passed and l3_passed and l4_passed
    
    breakdown = {
        "l1_status": l1_str,
        "l2_status": l2_str,
        "l3_status": l3_str,
        "l4_status": l4_str,
        "l5_status": f"🟢 CONFIRMED CANDLE WIN (Confidence: {confidence:.1f}%)" if l5_passed else f"🔴 REJECTED: Low Win Confidence ({confidence:.1f}% < 70%)"
    }
    
    if l5_passed and price_change_pct > 0:
        return "BUY_CALL", confidence, breakdown["l5_status"], breakdown
    elif l5_passed and price_change_pct < 0:
        return "BUY_PUT", confidence, breakdown["l5_status"], breakdown
    else:
        return "WAIT", confidence, breakdown["l5_status"], breakdown

def evaluate_btc_15m_signal(df):
    return predict_15m_candle_winning_direction(df)

# --- EXISTING NIFTY ENGINE WITH STRICT DYNAMIC BADGES ---
def evaluate_volume_and_time_filter(volume, ist_time):
    if volume < config.MIN_15M_CANDLE_VOLUME:
        return False, f"🔴 FAILED: Low Volume ({volume:,.0f} < 50k Cutoff)"
    if config.LUNCH_HOUR_START <= ist_time <= config.LUNCH_HOUR_END:
        if volume < (config.MIN_15M_CANDLE_VOLUME * 1.5):
            return False, "🔴 FAILED: Lunch Hour Choppy Zone (11:30 AM - 01:30 PM)"
    return True, "🟢 PASSED: Volume Participation OK"

def evaluate_fib_golden_pocket(high, low, close, direction):
    swing_range = high - low
    if swing_range <= 0:
        return True, 0.75, "🟢 PASSED"
    retrace = (high - close) / swing_range if direction == "CALL" else (close - low) / swing_range
    if retrace <= config.FIB_DISCOUNT_MAX:
        return True, retrace, f"🟢 PASSED (Fib Discount {retrace:.2f} <= 0.886)"
    else:
        return False, retrace, f"🔴 FAILED (Overextended Fib {retrace:.2f} > 0.886)"

def evaluate_pcr_layer(pcr_oi, delta_pcr_15):
    if 0.90 <= pcr_oi <= 1.10:
        return "🔴 FAILED: NEUTRAL_TRAP (0.90 - 1.10)", False, False
    call_pcr_confirmed = (pcr_oi >= 1.10) and (delta_pcr_15 > 0)
    put_pcr_confirmed = (pcr_oi <= 0.90) and (delta_pcr_15 < 0)
    if call_pcr_confirmed:
        return "🟢 PASSED: BULLISH_PCR_CONFIRMED", True, False
    elif put_pcr_confirmed:
        return "🟢 PASSED: BEARISH_PCR_CONFIRMED", False, True
    else:
        return "🔴 FAILED: PCR_CONTRADICTION", False, False

def evaluate_vix_layer(vix, delta_vix_15):
    if vix < 12.0:
        return "🔴 FAILED: LOW_VIX_BLOCK (VIX < 12.0)", 0.0, False
    elif 12.0 <= vix <= 18.0:
        return "🟢 PASSED: OPTIMAL_VOLATILITY", 1.0, (delta_vix_15 >= 0)
    else:
        return "🟢 PASSED: HIGH_VOLATILITY", 0.50, (delta_vix_15 >= 0)

def evaluate_oi_runway(nifty_price, nearest_wall_strike, nifty_target, direction):
    runway = (nearest_wall_strike - nifty_price) if direction == "CALL" else (nifty_price - nearest_wall_strike)
    if runway < 75.0:
        return runway, 0.0, f"🔴 FAILED: IMMEDIATE_WALL_BLOCK ({runway:.0f} pts < 75)"
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
    l1_pass = heavyweight_k >= 4 and heavyweight_a >= 0.75
    breakdown = {
        "l1_status": f"🟢 PASSED (Heavyweights K={heavyweight_k}/5, A={heavyweight_a:.2f})" if l1_pass else f"🔴 FAILED (Heavyweights Disagree K={heavyweight_k}/5)",
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

    if not l1_pass:
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
        breakdown["l2_status"] = "🔴 FAILED: Falling VIX (Weak Premium Expansion)"
        breakdown["l5_status"] = "🔴 REJECTED: Falling VIX"
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

def get_candle_confirmation_status(ist_time=None):
    """
    Evaluates current 15M candle's 60-second institutional confirmation window & 4-min entry status.
    """
    if ist_time is None:
        ist_now = datetime.now()
    elif hasattr(ist_time, "minute"):
        ist_now = ist_time
    else:
        ist_now = datetime.now()

    minute = ist_now.minute
    second = ist_now.second
    elapsed_sec = (minute % 15) * 60 + second
    rem_sec = max(0, 900 - elapsed_sec)
    
    if elapsed_sec <= 60:
        conf_remaining = max(0, 60 - elapsed_sec)
        conf_status = "ACTIVE"
        conf_msg = f"⏳ 60s INSTITUTIONAL CONFIRMATION WINDOW: {conf_remaining}s REMAINING..."
    else:
        conf_remaining = 0
        conf_status = "PASSED"
        conf_msg = "🟢 STRONG 60s CONFIRMATION PASSED! (SAFE ENTRY ACTIVE)"

    if 60 <= elapsed_sec <= 240:
        entry_window_status = "SAFEST_4MIN"
        entry_window_msg = "🟢 SAFEST 4-MIN ENTRY WINDOW ACTIVE! (EXECUTE NOW ON DHAN / BINANCE)"
    elif 240 < elapsed_sec <= 600:
        entry_window_status = "EXTENDED"
        entry_window_msg = "🟡 EXTENDED ENTRY WINDOW (CHECK IF PRICE IS STILL IN ENTRY ZONE)"
    else:
        entry_window_status = "LATE_WARNING"
        entry_window_msg = "🔴 LATE ENTRY WARNING: TOO LATE FOR THIS CANDLE (WAIT FOR NEXT CANDLE OPEN)"

    return {
        "elapsed_seconds": elapsed_sec,
        "remaining_seconds": rem_sec,
        "conf_status": conf_status,
        "conf_remaining": conf_remaining,
        "conf_msg": conf_msg,
        "entry_window_status": entry_window_status,
        "entry_window_msg": entry_window_msg
    }
