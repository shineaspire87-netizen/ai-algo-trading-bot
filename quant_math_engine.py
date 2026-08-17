# quant_math_engine.py - Core Microstructure & Mathematical Indicator Engine

import pandas as pd
import numpy as np
import ta
import logging

# -------------------------------------------------------------
# 1. WEIGHTED MULTI-LEVEL ORDER BOOK IMBALANCE (OBI_w)
# -------------------------------------------------------------
def compute_weighted_obi(bids: list, asks: list, depth_levels: int = 10, decay_lambda: float = 0.5) -> float:
    """Calculates Distance-Weighted Order Book Imbalance (OBI_w) with exponential decay"""
    try:
        if not bids or not asks:
            return 0.0
            
        n_bids = min(len(bids), depth_levels)
        n_asks = min(len(asks), depth_levels)
        
        # Exponential Distance Weights: w_i = (0.5)^(i-1)
        weights = [decay_lambda ** i for i in range(max(n_bids, n_asks))]
        
        weighted_bids = sum(float(bids[i][1]) * weights[i] for i in range(n_bids))
        weighted_asks = sum(float(asks[i][1]) * weights[i] for i in range(n_asks))
        
        total_weighted_vol = weighted_bids + weighted_asks
        if total_weighted_vol == 0:
            return 0.0
            
        obi_w = (weighted_bids - weighted_asks) / total_weighted_vol
        return round(float(obi_w), 4) # Range: -1.0 to +1.0
    except Exception as e:
        logging.warning(f"Weighted OBI Error: {e}")
        return 0.0

# -------------------------------------------------------------
# 2. SPOOFING DETECTION RATIO (SDR)
# -------------------------------------------------------------
def compute_spoofing_detection_ratio(bids: list) -> float:
    """Calculates Spoofing Detection Ratio (SDR) to flag deep fake liquidity walls"""
    try:
        if len(bids) < 6:
            return 1.0
            
        top_2_vol = sum(float(bids[i][1]) for i in range(2)) / 2.0
        deep_4_vol = sum(float(bids[i][1]) for i in range(2, 6)) / 4.0
        
        if deep_4_vol == 0:
            return 1.0
            
        sdr = top_2_vol / deep_4_vol
        return round(float(sdr), 4) # SDR < 0.25 flags suspicious spoof walls
    except Exception as e:
        return 1.0

# -------------------------------------------------------------
# 3. GARMAN-KLASS VOLATILITY & SVR (Spread-to-Volatility Ratio)
# -------------------------------------------------------------
def compute_garman_klass_volatility(df_5m: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculates Garman-Klass Volatility Estimator (sigma_GK)"""
    df = df_5m.copy()
    
    log_hl = np.log(df['High'] / df['Low']) ** 2
    log_co = np.log(df['Close'] / df['Open']) ** 2
    
    gk_element = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co
    sigma_gk = np.sqrt(gk_element.rolling(window=window).mean())
    return sigma_gk.fillna(0.001)

def compute_spread_to_volatility_ratio(ask_price: float, bid_price: float, mid_price: float, gk_vol: float) -> float:
    """Calculates Spread-to-Volatility Ratio (SVR) to detect inventory absorption"""
    try:
        if mid_price == 0 or gk_vol == 0:
            return 1.0
        spread_pct = (ask_price - bid_price) / mid_price
        svr = spread_pct / gk_vol
        return round(float(svr), 4)
    except Exception:
        return 1.0

# -------------------------------------------------------------
# 4. OPEN INTEREST STD DEVIATION SPIKE (OI Classification)
# -------------------------------------------------------------
def compute_oi_std_deviation_spike(oi_series: pd.Series, window: int = 100) -> float:
    """Calculates normalized Open Interest standard deviation Z-score (delta_OI / sigma_OI)"""
    try:
        if len(oi_series) < 5:
            return 0.0
            
        delta_oi = oi_series.diff()
        rolling_std = delta_oi.rolling(window=window).std().iloc[-1]
        
        if rolling_std == 0 or np.isnan(rolling_std):
            return 0.0
            
        latest_delta = delta_oi.iloc[-1]
        z_oi = latest_delta / rolling_std
        return round(float(z_oi), 2)
    except Exception:
        return 0.0

# -------------------------------------------------------------
# 5. FUNDING RATE Z-SCORE (MAD Robust Standardization)
# -------------------------------------------------------------
def compute_funding_zscore_mad(funding_series: pd.Series, window: int = 24) -> float:
    """Calculates Robust Funding Rate Z-score using Median Absolute Deviation (MAD)"""
    try:
        if len(funding_series) < window:
            return 0.0
            
        recent = funding_series.iloc[-window:]
        median_f = recent.median()
        mad = 1.4826 * (recent - median_f).abs().median()
        
        if mad == 0 or np.isnan(mad):
            return 0.0
            
        latest_f = funding_series.iloc[-1]
        z_f = (latest_f - median_f) / mad
        return round(float(z_f), 2) # Z_f >= +2.0 = Crowded Long | Z_f <= -2.0 = Crowded Short
    except Exception:
        return 0.0

# -------------------------------------------------------------
# 6. ROLLING HURST EXPONENT (N=64 Rescaled Range R/S Analysis)
# -------------------------------------------------------------
def compute_hurst_exponent_rs(price_series: pd.Series, window: int = 64) -> float:
    """Calculates Hurst Exponent (H) over 64 5-minute candles with safe 0.55 fallback"""
    try:
        if len(price_series) < 32:
            return 0.55 # Active Trend Fallback (Never return 0.00!)
            
        prices = price_series.iloc[-window:].values
        log_returns = np.diff(np.log(prices))
        
        if len(log_returns) < 16:
            return 0.55
            
        sub_lengths = [8, 16, 32]
        rs_values = []
        
        for n in sub_lengths:
            num_splits = len(log_returns) // n
            rs_sub = []
            for i in range(num_splits):
                chunk = log_returns[i*n : (i+1)*n]
                mean_adj = chunk - np.mean(chunk)
                cum_sum = np.cumsum(mean_adj)
                r = np.max(cum_sum) - np.min(cum_sum)
                s = np.std(chunk, ddof=1) + 1e-8
                rs_sub.append(r / s)
            rs_values.append(np.mean(rs_sub))
            
        log_n = np.log(sub_lengths)
        log_rs = np.log(rs_values)
        
        poly = np.polyfit(log_n, log_rs, 1)
        hurst = poly[0]
        
        if np.isnan(hurst) or hurst <= 0.05:
            return 0.55
            
        return round(float(np.clip(hurst, 0.15, 0.85)), 2)
    except Exception:
        return 0.55 # Safe Fallback

# -------------------------------------------------------------
# 7. BOLLINGER BAND WIDTH PERCENTILE (BBWP < 20th Percentile)
# -------------------------------------------------------------
def compute_bbwp(df_5m: pd.DataFrame, bb_window: int = 20, percentile_window: int = 288) -> float:
    """Calculates Bollinger Band Width Percentile (BBWP) over 288 bars (24 hours)"""
    try:
        df = df_5m.copy()
        bb = ta.volatility.BollingerBands(df['Close'], window=bb_window, window_dev=2)
        bb_width = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
        
        if len(bb_width) < percentile_window:
            return 50.0
            
        rolling_bbw = bb_width.iloc[-percentile_window:]
        current_bbw = bb_width.iloc[-1]
        
        # Calculate Percentile Rank (0 to 100)
        rank = (rolling_bbw < current_bbw).sum() / float(percentile_window) * 100.0
        return round(float(rank), 2) # BBWP < 20.0 = Structural Volatility Squeeze
    except Exception:
        return 50.0
