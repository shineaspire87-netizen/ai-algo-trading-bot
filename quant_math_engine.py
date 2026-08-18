"""
ANTONY QUANT AI ALGO TERMINAL - QUANT MATH ENGINE V3.0
Includes:
1. Multi-Level Order-Flow Imbalance (MLOFI) with Exponential Decay (w_i = 0.5^(i-1))
2. VPIN (Volume-Synchronized Probability of Informed Trading) via Bulk Volume Classification
3. Corwin-Schultz Bid-Ask Spread Estimator (S_t)
4. Garman-Klass Volatility (sigma_GK) & BBWP Squeeze Filter
"""

import numpy as np
import pandas as pd
from scipy.stats import norm

def compute_decay_weighted_mlofi(bids: list, asks: list, levels: int = 10) -> float:
    """
    Computes Decay-Weighted Multi-Level Order Flow Imbalance (MLOFI)
    OFI_decay = sum(0.5^(i-1) * ofi_i) / sum(0.5^(i-1))
    """
    try:
        if not bids or not asks:
            return 0.0
            
        n_levels = min(len(bids), len(asks), levels)
        if n_levels == 0:
            return 0.0
            
        weights = [0.5 ** (i) for i in range(n_levels)]
        ofi_levels = []
        
        for i in range(n_levels):
            bid_vol = float(bids[i][1]) if len(bids[i]) > 1 else 0.0
            ask_vol = float(asks[i][1]) if len(asks[i]) > 1 else 0.0
            total_vol = bid_vol + ask_vol
            
            if total_vol > 0:
                imbalance = (bid_vol - ask_vol) / total_vol
            else:
                imbalance = 0.0
            ofi_levels.append(imbalance)
            
        weighted_sum = sum(w * ofi for w, ofi in zip(weights, ofi_levels))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    except Exception:
        return 0.0


def compute_vpin_bvc(df: pd.DataFrame, bucket_vol: float = 10.0, window: int = 20) -> float:
    """
    Computes VPIN (Volume-Synchronized Probability of Informed Trading) 
    using Bulk Volume Classification (BVC) with Gaussian CDF
    """
    try:
        # Standardize column names (lowercase or capitalized)
        df_cols = {col.lower(): col for col in df.columns}
        c_col = df_cols.get('close', 'Close')
        v_col = df_cols.get('volume', 'Volume')
        
        if len(df) < window or c_col not in df.columns or v_col not in df.columns:
            return 0.15 # Baseline normal flow
            
        prices = df[c_col].values
        volumes = df[v_col].values
        
        price_diffs = np.diff(prices)
        if len(price_diffs) == 0:
            return 0.15
            
        sigma_dp = np.std(price_diffs) if np.std(price_diffs) > 0 else 1e-5
        
        buy_vols = []
        sell_vols = []
        
        for i in range(1, len(prices)):
            dp = prices[i] - prices[i-1]
            z_score = dp / sigma_dp
            buy_frac = norm.cdf(z_score)
            
            v_b = volumes[i] * buy_frac
            v_s = volumes[i] * (1.0 - buy_frac)
            
            buy_vols.append(v_b)
            sell_vols.append(v_s)
            
        buy_arr = np.array(buy_vols[-window:])
        sell_arr = np.array(sell_vols[-window:])
        
        vpin = np.sum(np.abs(buy_arr - sell_arr)) / (np.sum(buy_arr + sell_arr) + 1e-5)
        return float(np.clip(vpin, 0.0, 1.0))
    except Exception:
        return 0.15


def compute_corwin_schultz_spread(df: pd.DataFrame) -> float:
    """
    Computes Corwin-Schultz Effective Bid-Ask Spread Estimator (S_t) from High-Low Ranges
    """
    try:
        if len(df) < 2:
            return 0.0005 # 0.05% baseline spread
            
        df_cols = {col.lower(): col for col in df.columns}
        h_col = df_cols.get('high', 'High')
        l_col = df_cols.get('low', 'Low')
        
        h1, l1 = df[h_col].iloc[-2], df[l_col].iloc[-2]
        h2, l2 = df[h_col].iloc[-1], df[l_col].iloc[-1]
        
        h2_combined = max(h1, h2)
        l2_combined = min(l1, l2)
        
        if l1 <= 0 or l2 <= 0 or l2_combined <= 0:
            return 0.0005
            
        beta = (np.log(h1 / l1))**2 + (np.log(h2 / l2))**2
        gamma = (np.log(h2_combined / l2_combined))**2
        
        sqrt_2beta = np.sqrt(2 * beta)
        sqrt_beta = np.sqrt(beta)
        denom = 3.0 - 2.0 * np.sqrt(2)
        
        alpha = (sqrt_2beta - sqrt_beta) / denom - np.sqrt(gamma / denom)
        
        if np.isnan(alpha) or alpha <= 0:
            return 0.0001
            
        spread = (2.0 * (np.exp(alpha) - 1.0)) / (1.0 + np.exp(alpha))
        return float(max(spread, 0.0))
    except Exception:
        return 0.0005


def compute_garman_klass_volatility(df: pd.DataFrame, window: int = 14) -> float:
    """
    Computes Garman-Klass Range-Based Volatility Estimator (8x efficiency)
    sigma^2_GK = 0.5 * (ln(H/L))^2 - (2*ln(2) - 1) * (ln(C/O))^2
    """
    try:
        if len(df) < window:
            return 0.01
            
        df_cols = {col.lower(): col for col in df.columns}
        h_col = df_cols.get('high', 'High')
        l_col = df_cols.get('low', 'Low')
        c_col = df_cols.get('close', 'Close')
        o_col = df_cols.get('open', 'Open')
        
        log_hl = np.log(df[h_col] / df[l_col])**2
        log_co = np.log(df[c_col] / df[o_col])**2
        
        gk_var = 0.5 * log_hl - (2.0 * np.log(2) - 1.0) * log_co
        rolling_gk = np.sqrt(np.maximum(gk_var.rolling(window).mean(), 1e-8))
        
        return float(rolling_gk.iloc[-1])
    except Exception:
        return 0.01


def compute_bbwp_squeeze(df: pd.DataFrame, n: int = 20, k: float = 2.0, lookback: int = 252) -> float:
    """
    Computes Bollinger Band Width Percentile (BBWP) over macro lookback L=252.
    Returns percentile (0.0 to 100.0). BBWP < 20.0 indicates severe VCP squeeze!
    """
    try:
        df_cols = {col.lower(): col for col in df.columns}
        c_col = df_cols.get('close', 'Close')
        
        if len(df) < n or c_col not in df.columns:
            return 50.0
            
        sma = df[c_col].rolling(n).mean()
        std = df[c_col].rolling(n).std()
        
        ub = sma + k * std
        lb = sma - k * std
        
        bbw = (ub - lb) / (sma + 1e-8)
        
        curr_bbw = bbw.iloc[-1]
        hist_bbw = bbw.tail(lookback).values
        
        if len(hist_bbw) == 0:
            return 50.0
            
        percentile = (np.sum(hist_bbw < curr_bbw) / len(hist_bbw)) * 100.0
        return float(percentile)
    except Exception:
        return 50.0
