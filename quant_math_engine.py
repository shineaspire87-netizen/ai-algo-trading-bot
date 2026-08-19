# ================================================================================
# ANTONY QUANT AI TERMINAL - DUAL-ASSET QUANT MATH ENGINE (0MS PUMP FIX)
# ================================================================================
import numpy as np
from datetime import time, datetime
import config

def evaluate_btc_15m_signal(df):
    """
    Evaluates Bitcoin 15M Candlestick Quant Signal with Impulse Breakout Logic.
    """
    if df.empty or len(df) < 5:
        return "WAIT", "REJECT: Insufficient BTC Data", 0.0, {}
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    close = float(last_row['close'])
    high = float(last_row['high'])
    low = float(last_row['low'])
    prev_close = float(prev_row['close'])
    
    price_change_pct = ((close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
    
    log_hl = np.log(high / low) ** 2 if (low > 0 and high >= low) else 0
    gk_vol = np.sqrt(0.5 * log_hl) * 100.0
    
    swing_range = high - low
    retrace = (high - close) / swing_range if swing_range > 0 else 0.5
    
    breakdown = {
        "l1_heavyweights": "Crypto 24/7 (Binance Direct 0ms)",
        "l2_vix": f"GK Volatility: {gk_vol:.2f}%",
        "l3_pcr": f"15M Momentum: {price_change_pct:+.2f}%",
        "l4_runway": f"Fib Retrace: {retrace:.3f}",
        "l5_status": "WAIT"
    }
    
    # 💥 IMPULSE PUMP RULE: If 15M candle move >= +0.30%, trigger BUY CALL (LONG) immediately!
    if price_change_pct >= +0.30:
        breakdown["l5_status"] = f"CONFIRMED: BTC Bullish Impulse Pump ({price_change_pct:+.2f}%)"
        return "BUY_CALL", breakdown["l5_status"], 1.0, breakdown
    elif price_change_pct <= -0.30:
        breakdown["l5_status"] = f"CONFIRMED: BTC Bearish Impulse Dump ({price_change_pct:+.2f}%)"
        return "BUY_PUT", breakdown["l5_status"], 1.0, breakdown
    elif price_change_pct > +0.15 and retrace <= 0.886:
        breakdown["l5_status"] = f"CONFIRMED: BTC Moderate Bullish Move ({price_change_pct:+.2f}%)"
        return "BUY_CALL", breakdown["l5_status"], 1.0, breakdown
    elif price_change_pct < -0.15 and retrace <= 0.886:
        breakdown["l5_status"] = f"CONFIRMED: BTC Moderate Bearish Move ({price_change_pct:+.2f}%)"
        return "BUY_PUT", breakdown["l5_status"], 1.0, breakdown
    else:
        breakdown["l5_status"] = f"REJECT: Sideways BTC Range ({price_change_pct:+.2f}%)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown


# --- EXISTING NIFTY ENGINE ---
def evaluate_volume_and_time_filter(volume, ist_time):
    try:
        vol = float(volume) if volume is not None else 65000.0
    except (ValueError, TypeError):
        vol = 65000.0

    if vol <= 0:
        vol = 65000.0

    if vol < config.MIN_15M_CANDLE_VOLUME:
        return False, f"REJECT: Low Volume ({vol:,.0f} < 50k Cutoff)"
    
    if hasattr(ist_time, "time"):
        t = ist_time.time()
    elif isinstance(ist_time, time):
        t = ist_time
    else:
        t = None

    if t is not None and config.LUNCH_HOUR_START <= t <= config.LUNCH_HOUR_END:
        if vol < (config.MIN_15M_CANDLE_VOLUME * 1.5):
            return False, "REJECT: Lunch Hour Choppy Zone (11:30 AM - 01:30 PM)"
            
    return True, "VOLUME_OK"

def evaluate_fib_golden_pocket(high, low, close, direction):
    try:
        h, l, c = float(high), float(low), float(close)
    except (ValueError, TypeError):
        return True, 0.75, "FIB_OK"
    swing_range = h - l
    if swing_range <= 0:
        return True, 0.75, "FIB_OK"
    retrace = (h - c) / swing_range if direction in ["CALL", "UP"] else (c - l) / swing_range
    if config.FIB_DISCOUNT_MIN <= retrace <= config.FIB_DISCOUNT_MAX:
        return True, retrace, "GOLDEN_POCKET_DISCOUNT"
    elif retrace < config.FIB_DISCOUNT_MIN:
        return True, retrace, "STRONG_BREAKOUT"
    else:
        return False, retrace, "OVEREXTENDED_PREMIUM_TRAP"

def evaluate_pcr_layer(pcr_oi, delta_pcr_15):
    if 0.90 <= pcr_oi <= 1.10:
        return "NEUTRAL_TRAP", False, False
    call_pcr_confirmed = (pcr_oi >= 1.10) and (delta_pcr_15 > 0)
    put_pcr_confirmed = (pcr_oi <= 0.90) and (delta_pcr_15 < 0)
    if call_pcr_confirmed:
        return "BULLISH_CONFIRMED", True, False
    elif put_pcr_confirmed:
        return "BEARISH_CONFIRMED", False, True
    else:
        return "PCR_CONTRADICTION", False, False

def evaluate_vix_layer(vix, delta_vix_15):
    if vix < 12.0:
        return "LOW_VIX_BLOCK", 0.0, False
    elif 12.0 <= vix <= 18.0:
        return "OPTIMAL", 1.0, (delta_vix_15 >= 0)
    else:
        return "HIGH_VOLATILITY", 0.50, (delta_vix_15 >= 0)

def evaluate_oi_runway(nifty_price, nearest_wall_strike, nifty_target, direction):
    runway = (nearest_wall_strike - nifty_price) if direction in ["CALL", "UP"] else (nifty_price - nearest_wall_strike)
    if runway < 75.0:
        return runway, 0.0, "IMMEDIATE_WALL_BLOCK"
    runway_ratio = runway / nifty_target if nifty_target > 0 else 0.0
    if runway >= 100.0 and runway_ratio >= 2.0:
        return runway, runway_ratio, "CLEAR_RUNWAY"
    elif runway >= 75.0 and runway_ratio >= 1.5:
        return runway, runway_ratio, "WEAK_RUNWAY"
    else:
        return runway, runway_ratio, "RUNWAY_TOO_TIGHT"

def master_institutional_decision_engine(
    nifty_direction, heavyweight_k, heavyweight_a, india_vix, delta_vix_15,
    pcr_oi, delta_pcr_15, nifty_spot, nearest_ce_wall, nearest_pe_wall,
    volume_15m=65000, candle_high=24200, candle_low=24100, ist_time=None, nifty_target=30.0
):
    breakdown = {
        "l1_heavyweights": f"K={heavyweight_k}/5 (A={heavyweight_a:.2f})",
        "l2_vix": f"VIX={india_vix:.1f} (Δ={delta_vix_15:+.2f})",
        "l3_pcr": f"PCR={pcr_oi:.2f} (Δ={delta_pcr_15:+.2f})",
        "l4_runway": "Pending",
        "l5_status": "WAIT"
    }

    if ist_time is not None:
        vol_ok, vol_msg = evaluate_volume_and_time_filter(volume_15m, ist_time)
        if not vol_ok:
            breakdown["l5_status"] = vol_msg
            return "WAIT", breakdown["l5_status"], 0.0, breakdown

    if heavyweight_k < 4 or heavyweight_a < 0.75:
        breakdown["l5_status"] = "REJECT: Heavyweights disagree (K < 4)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    
    fib_ok, fib_ratio, fib_status = evaluate_fib_golden_pocket(candle_high, candle_low, nifty_spot, nifty_direction)
    if not fib_ok:
        breakdown["l5_status"] = f"REJECT: Overextended Premium Trap (Fib={fib_ratio:.3f})"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown

    vix_regime, pos_multiplier, vix_expanding = evaluate_vix_layer(india_vix, delta_vix_15)
    if vix_regime == "LOW_VIX_BLOCK":
        breakdown["l5_status"] = "REJECT: VIX < 12 (Premium Decay Trap)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    if not vix_expanding:
        breakdown["l5_status"] = "REJECT: Falling VIX (Weak Premium Expansion)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    
    pcr_status, call_pcr_ok, put_pcr_ok = evaluate_pcr_layer(pcr_oi, delta_pcr_15)
    
    if nifty_direction == "UP":
        if not call_pcr_ok:
            breakdown["l5_status"] = f"REJECT: CALL contradicted by PCR ({pcr_status})"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        runway, ratio, runway_status = evaluate_oi_runway(nifty_spot, nearest_ce_wall, nifty_target, "CALL")
        breakdown["l4_runway"] = f"CE Wall: {nearest_ce_wall} ({runway:.0f} pts, R={ratio:.1f}x)"
        if runway_status != "CLEAR_RUNWAY":
            breakdown["l5_status"] = f"REJECT: CE Wall too close ({runway:.0f} pts)"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        breakdown["l5_status"] = f"CONFIRMED: Golden Fib ({fib_ratio:.2f}) + Clear Runway ({runway:.0f} pts)"
        return "BUY_CALL", breakdown["l5_status"], pos_multiplier, breakdown

    elif nifty_direction == "DOWN":
        if not put_pcr_ok:
            breakdown["l5_status"] = f"REJECT: PUT contradicted by PCR ({pcr_status})"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        runway, ratio, runway_status = evaluate_oi_runway(nifty_spot, nearest_pe_wall, nifty_target, "PUT")
        breakdown["l4_runway"] = f"PE Wall: {nearest_pe_wall} ({runway:.0f} pts, R={ratio:.1f}x)"
        if runway_status != "CLEAR_RUNWAY":
            breakdown["l5_status"] = f"REJECT: PE Wall too close ({runway:.0f} pts)"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        breakdown["l5_status"] = f"CONFIRMED: Golden Fib ({fib_ratio:.2f}) + Clear Runway ({runway:.0f} pts)"
        return "BUY_PUT", breakdown["l5_status"], pos_multiplier, breakdown

    breakdown["l5_status"] = "REJECT: No Directional Momentum"
    return "WAIT", breakdown["l5_status"], 0.0, breakdown
