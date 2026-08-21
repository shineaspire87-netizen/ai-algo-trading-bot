import numpy as np
import config

def calculate_candle_body_ratio(high, low, open_p, close_p):
    total_range = high - low
    if total_range <= 0:
        return 0.0
    body = abs(close_p - open_p)
    return round((body / total_range) * 100.0, 1)

def _safe_vol_ratio(df, volume):
    """BUG 2 FIX: NaN-safe volume ratio calculation."""
    try:
        if 'volume' not in df.columns:
            return 1.0
        vol_series = df['volume'].replace(0, np.nan).dropna()
        if len(vol_series) < 2:
            return 1.0
        avg_vol = float(vol_series.iloc[-6:-1].mean())
        if np.isnan(avg_vol) or avg_vol <= 0:
            return 1.0
        return float(volume) / avg_vol
    except Exception:
        return 1.0

def _directional_fib_retrace(high, low, close, direction_up):
    """
    BUG 1 FIX: Correct directional Fibonacci retrace.
    UP candle: small = strong close near top (CALL signal quality).
    DOWN candle: small = strong close near bottom (PUT signal quality).
    """
    swing_range = high - low
    if swing_range <= 0:
        return 0.5
    if direction_up:
        return (high - close) / swing_range
    else:
        return (close - low) / swing_range

def _three_candle_momentum(df):
    """3-candle momentum confirmation — returns avg directional bias."""
    if len(df) < 4:
        return 0.0
    last3 = df.iloc[-4:-1]
    deltas = []
    for i in range(len(last3)):
        row = last3.iloc[i]
        try:
            deltas.append(float(row['close']) - float(row['open']))
        except Exception:
            pass
    return sum(deltas) / len(deltas) if deltas else 0.0

def evaluate_forex_15m_signal(df, use_closed_candle=False):
    """
    Evaluates Forex 15M (EUR/USD) Candlestick Signal.
    BUG 6 FIX: use_closed_candle=True evaluates df.iloc[-2] (last completed candle).
    """
    if df.empty or len(df) < 4:
        return "WAIT", 0.0, "REJECT: Insufficient Forex Data", {}

    # BUG 6 FIX: Evaluate from completed candle for confirmed signal
    target_row = df.iloc[-2] if use_closed_candle else df.iloc[-1]
    prev_row   = df.iloc[-3] if use_closed_candle else df.iloc[-2]

    close  = float(target_row['close'])
    open_p = float(target_row['open'])
    high   = float(target_row['high'])
    low    = float(target_row['low'])
    prev_close = float(prev_row['close'])

    price_change_pips = (close - prev_close) * 10000.0
    candle_pips = (close - open_p) * 10000.0
    abs_pips = max(abs(price_change_pips), abs(candle_pips))
    eff_pips = price_change_pips if abs(price_change_pips) >= abs(candle_pips) else candle_pips
    direction_up = eff_pips > 0

    # BUG 7 FIX: Tighter body ratio threshold (40% for Forex, was 35%)
    body_ratio = calculate_candle_body_ratio(high, low, open_p, close)
    l1_passed = body_ratio >= 40.0

    l3_passed = abs_pips >= 1.5

    # BUG 1 FIX: Directional fib retrace
    retrace = _directional_fib_retrace(high, low, close, direction_up)
    l4_passed = retrace <= 0.85

    # 3-candle momentum confirmation
    momentum_avg = _three_candle_momentum(df)
    momentum_aligned = (momentum_avg > 0 and direction_up) or (momentum_avg < 0 and not direction_up)

    confidence = 50.0
    if abs_pips >= 5.0:   confidence += 25.0
    elif abs_pips >= 2.5: confidence += 18.0
    elif abs_pips >= 1.5: confidence += 12.0

    if l1_passed:        confidence += 12.0
    if l4_passed:        confidence += 8.0
    if momentum_aligned: confidence += 5.0
    confidence = min(95.0, confidence)

    breakdown = {
        "l1_status": f"🟢 PASSED (Forex Body: {body_ratio}%)" if l1_passed else f"🔴 FAILED (Flat Forex Body: {body_ratio}% < 40%)",
        "l2_status": f"🟢 PASSED (3-Candle Momentum: {momentum_avg:+.5f})" if momentum_aligned else f"🟡 COUNTER-TREND (Avg: {momentum_avg:+.5f})",
        "l3_status": f"🟢 PASSED (15M Pips: {abs_pips:+.1f} Pips)" if l3_passed else f"🔴 FAILED (Weak Pips: {abs_pips:+.1f} Pips)",
        "l4_status": f"🟢 PASSED (Directional Fib: {retrace:.3f})" if l4_passed else f"🔴 FAILED (Weak Close Fib: {retrace:.3f} > 0.85)",
        "l5_status": f"CANDLE WIN PROBABILITY: {confidence:.1f}%"
    }

    if confidence < 55.0 or not l3_passed or not l1_passed:
        breakdown["l5_status"] = f"🔴 REJECTED: Low Forex Win Confidence ({confidence:.1f}%)"
        return "WAIT", confidence, breakdown["l5_status"], breakdown

    if eff_pips >= +1.5:
        breakdown["l5_status"] = f"🟢 CONFIRMED: EUR/USD Bullish Momentum ({eff_pips:+.1f} Pips)"
        return "BUY_CALL", confidence, breakdown["l5_status"], breakdown
    elif eff_pips <= -1.5:
        breakdown["l5_status"] = f"🟢 CONFIRMED: EUR/USD Bearish Momentum ({eff_pips:+.1f} Pips)"
        return "BUY_PUT", confidence, breakdown["l5_status"], breakdown
    else:
        breakdown["l5_status"] = f"🔴 REJECTED: Sideways Forex Range ({eff_pips:+.1f} Pips)"
        return "WAIT", confidence, breakdown["l5_status"], breakdown

def predict_15m_candle_winning_direction(df, use_closed_candle=False):
    """
    BTC / NIFTY 15M candle direction predictor.
    BUG 1 FIX: Directional fib retrace.
    BUG 2 FIX: NaN-safe volume ratio.
    BUG 7 FIX: Tighter body ratio threshold (35%, was 30%).
    BUG 6 FIX: use_closed_candle evaluates from df.iloc[-2].
    """
    if df.empty or len(df) < 4:
        return "WAIT", 0.0, "REJECT: Insufficient Data", {}

    target_row = df.iloc[-2] if use_closed_candle else df.iloc[-1]
    prev_row   = df.iloc[-3] if use_closed_candle else df.iloc[-2]

    close  = float(target_row['close'])
    open_p = float(target_row['open'])
    high   = float(target_row['high'])
    low    = float(target_row['low'])

    try:
        volume = float(target_row['volume']) if 'volume' in target_row.index and float(target_row['volume']) > 0 else 50000.0
    except Exception:
        volume = 50000.0

    prev_close = float(prev_row['close'])
    price_change_pct  = ((close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
    candle_change_pct = ((close - open_p) / open_p) * 100.0 if open_p > 0 else 0.0
    eff_pct = price_change_pct if abs(price_change_pct) >= abs(candle_change_pct) else candle_change_pct

    direction_up = eff_pct > 0

    # BUG 7 FIX: Tighter body ratio (35% for BTC/NIFTY, was 30%)
    body_ratio = calculate_candle_body_ratio(high, low, open_p, close)
    l1_passed = body_ratio >= 35.0
    l1_str = f"🟢 PASSED (Body Intensity: {body_ratio}%)" if l1_passed else f"🔴 FAILED (Low Body Intensity: {body_ratio}% < 35%)"

    # BUG 2 FIX: NaN-safe volume ratio
    vol_ratio = _safe_vol_ratio(df, volume)
    l2_passed = vol_ratio >= 0.70
    l2_str = f"🟢 PASSED (Volume Acceleration: {vol_ratio:.1f}x)" if l2_passed else f"🔴 FAILED (Low Volume Accel: {vol_ratio:.1f}x < 0.7x)"

    l3_passed = abs(eff_pct) >= 0.05
    l3_str = f"🟢 PASSED (15M Momentum: {eff_pct:+.2f}%)" if l3_passed else f"🔴 FAILED (Weak Momentum: {eff_pct:+.2f}% < 0.05%)"

    # BUG 1 FIX: Directional fib retrace
    retrace = _directional_fib_retrace(high, low, close, direction_up)
    l4_passed = retrace <= 0.85
    l4_str = f"🟢 PASSED (Directional Fib: {retrace:.3f})" if l4_passed else f"🔴 FAILED (Weak Close Fib: {retrace:.3f} > 0.85)"

    # 3-candle momentum confirmation
    momentum_avg = _three_candle_momentum(df)
    momentum_aligned = (momentum_avg > 0 and direction_up) or (momentum_avg < 0 and not direction_up)

    confidence = 50.0
    if abs(eff_pct) >= 0.15: confidence += 20.0
    elif abs(eff_pct) >= 0.08: confidence += 12.0

    if l1_passed:        confidence += 10.0
    if l2_passed:        confidence += 8.0
    if l4_passed:        confidence += 7.0
    if momentum_aligned: confidence += 5.0
    confidence = min(95.0, confidence)

    l5_passed = confidence >= 55.0 and l3_passed and l4_passed and l1_passed

    breakdown = {
        "l1_status": l1_str,
        "l2_status": l2_str,
        "l3_status": l3_str,
        "l4_status": l4_str,
        "l5_status": f"🟢 CONFIRMED CANDLE WIN (Confidence: {confidence:.1f}%)" if l5_passed else f"🔴 REJECTED: Low Win Confidence ({confidence:.1f}% < 55%)"
    }

    if l5_passed and eff_pct > 0:
        return "BUY_CALL", confidence, breakdown["l5_status"], breakdown
    elif l5_passed and eff_pct < 0:
        return "BUY_PUT", confidence, breakdown["l5_status"], breakdown
    else:
        return "WAIT", confidence, breakdown["l5_status"], breakdown

def evaluate_btc_15m_signal(df, use_closed_candle=False):
    return predict_15m_candle_winning_direction(df, use_closed_candle=use_closed_candle)

def evaluate_nifty_15m_signal(df, use_closed_candle=False):
    """BUG 10 FIX: Real candle-based NIFTY signal using actual price data."""
    return predict_15m_candle_winning_direction(df, use_closed_candle=use_closed_candle)

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
