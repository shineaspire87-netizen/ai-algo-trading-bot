# ================================================================================
# ANTONY QUANT AI TERMINAL - 5-LAYER CHAMPION QUANT MATH ENGINE
# ================================================================================
import numpy as np
from datetime import time, datetime
import config

def evaluate_volume_and_time_filter(volume, ist_time):
    """Evaluates 15M Volume Cutoff and Lunch Hour Chop Guard."""
    try:
        vol = float(volume) if volume is not None else 65000.0
    except (ValueError, TypeError):
        vol = 65000.0

    # Index feeds (like ^NSEI) have 0 volume in Yahoo Finance -> fallback to valid default
    if vol <= 0:
        vol = 65000.0

    if vol < config.MIN_15M_CANDLE_VOLUME:
        return False, f"REJECT: Low Volume ({vol:,.0f} < 50k Cutoff)"
    
    # Extract time object safely
    if hasattr(ist_time, "time"):
        t = ist_time.time()
    elif isinstance(ist_time, time):
        t = ist_time
    else:
        t = None

    # Lunch Hour Chop Guard (11:30 AM - 01:30 PM IST)
    if t is not None and config.LUNCH_HOUR_START <= t <= config.LUNCH_HOUR_END:
        if vol < (config.MIN_15M_CANDLE_VOLUME * 1.5):
            return False, "REJECT: Lunch Hour Choppy Zone (11:30 AM - 01:30 PM)"
            
    return True, "VOLUME_OK"


def evaluate_fib_golden_pocket(high, low, close, direction):
    """Calculates Fibonacci Retracement (0.705 - 0.886 Golden Pocket Discount Zone)."""
    try:
        h, l, c = float(high), float(low), float(close)
    except (ValueError, TypeError):
        return True, 0.75, "FIB_OK"

    swing_range = h - l
    if swing_range <= 0:
        return True, 0.75, "FIB_OK"
    
    if direction in ["CALL", "UP"]:
        retrace = (h - c) / swing_range
    else: # PUT / DOWN / FLAT
        retrace = (c - l) / swing_range
    
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
        regime = "OPTIMAL"
        pos_size = 1.0
    else:
        regime = "HIGH_VOLATILITY"
        pos_size = 0.50
    
    vol_expansion = (delta_vix_15 >= 0)
    return regime, pos_size, vol_expansion


def evaluate_oi_runway(nifty_price, nearest_wall_strike, nifty_target, direction):
    if direction in ["CALL", "UP"]:
        runway = nearest_wall_strike - nifty_price
    else:
        runway = nifty_price - nearest_wall_strike
        
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
    nifty_direction,      # "UP" or "DOWN"
    heavyweight_k,         # K >= 4
    heavyweight_a,         # A >= 0.75
    india_vix,            # e.g., 14.2
    delta_vix_15,          # e.g., +0.15
    pcr_oi,               # e.g., 1.18
    delta_pcr_15,          # e.g., +0.04
    nifty_spot,            # e.g., 24154.90
    nearest_ce_wall,       # e.g., 24300
    nearest_pe_wall,       # e.g., 24000
    volume_15m=65000,      # 15M Candle Volume
    candle_high=24200,     # Candle High
    candle_low=24100,      # Candle Low
    ist_time=None,         # Current IST Time
    nifty_target=30.0
):
    breakdown = {
        "l1_heavyweights": f"K={heavyweight_k}/5 (A={heavyweight_a:.2f})",
        "l2_vix": f"VIX={india_vix:.1f} (Δ={delta_vix_15:+.2f})",
        "l3_pcr": f"PCR={pcr_oi:.2f} (Δ={delta_pcr_15:+.2f})",
        "l4_runway": "Pending",
        "l5_status": "WAIT"
    }

    # VOLUME & TIME FILTER (CHRIS CREAMER RULE)
    if ist_time is not None:
        vol_ok, vol_msg = evaluate_volume_and_time_filter(volume_15m, ist_time)
        if not vol_ok:
            breakdown["l5_status"] = vol_msg
            return "WAIT", breakdown["l5_status"], 0.0, breakdown

    # LAYER 1: HEAVYWEIGHT ALIGNMENT
    if heavyweight_k < 4 or heavyweight_a < 0.75:
        breakdown["l5_status"] = "REJECT: Heavyweights disagree (K < 4)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    
    # FIB GOLDEN POCKET DISCOUNT CHECK
    fib_ok, fib_ratio, fib_status = evaluate_fib_golden_pocket(candle_high, candle_low, nifty_spot, nifty_direction)
    if not fib_ok:
        breakdown["l5_status"] = f"REJECT: Overextended Premium Trap (Fib={fib_ratio:.3f})"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown

    # LAYER 2: VIX REGIME & MOMENTUM
    vix_regime, pos_multiplier, vix_expanding = evaluate_vix_layer(india_vix, delta_vix_15)
    if vix_regime == "LOW_VIX_BLOCK":
        breakdown["l5_status"] = "REJECT: VIX < 12 (Premium Decay Trap)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    if not vix_expanding:
        breakdown["l5_status"] = "REJECT: Falling VIX (Weak Premium Expansion)"
        return "WAIT", breakdown["l5_status"], 0.0, breakdown
    
    # LAYER 3 & 4: PCR & PCR MOMENTUM
    pcr_status, call_pcr_ok, put_pcr_ok = evaluate_pcr_layer(pcr_oi, delta_pcr_15)
    
    if nifty_direction == "UP":
        if not call_pcr_ok:
            breakdown["l5_status"] = f"REJECT: CALL contradicted by PCR ({pcr_status})"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        
        # LAYER 5: OI RUNWAY (CALL)
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
        
        # LAYER 5: OI RUNWAY (PUT)
        runway, ratio, runway_status = evaluate_oi_runway(nifty_spot, nearest_pe_wall, nifty_target, "PUT")
        breakdown["l4_runway"] = f"PE Wall: {nearest_pe_wall} ({runway:.0f} pts, R={ratio:.1f}x)"
        
        if runway_status != "CLEAR_RUNWAY":
            breakdown["l5_status"] = f"REJECT: PE Wall too close ({runway:.0f} pts)"
            return "WAIT", breakdown["l5_status"], 0.0, breakdown
        
        breakdown["l5_status"] = f"CONFIRMED: Golden Fib ({fib_ratio:.2f}) + Clear Runway ({runway:.0f} pts)"
        return "BUY_PUT", breakdown["l5_status"], pos_multiplier, breakdown

    breakdown["l5_status"] = "REJECT: No Directional Momentum"
    return "WAIT", breakdown["l5_status"], 0.0, breakdown
