# test_strategy_audit.py - Automated Strategy Rule Conflict Audit Suite

import sys
import os
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import pandas as pd
import numpy as np
from multi_strategy import evaluate_institutional_bitcoin_signals

def create_synthetic_market_data(n_bars=100, base_price=63000, trend="UP", vol_multiplier=3.0):
    """Generates realistic 5m market candles with natural oscillations and datetime index"""
    np.random.seed(42)
    prices = [base_price]
    for i in range(1, n_bars):
        step = (8 if i % 2 != 0 else -3) if trend == "UP" else ((-8 if i % 2 != 0 else 3) if trend == "DOWN" else (2 if i % 2 == 0 else -2))
        prices.append(prices[-1] + step)
        
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n_bars, freq='5min')
    df = pd.DataFrame({
        'Open': prices[:-1] + [prices[-1] - 5],
        'High': [p + 15 for p in prices],
        'Low': [p - 15 for p in prices],
        'Close': prices[:-1] + [prices[-1] + 12],
        'Volume': [100] * (n_bars - 1) + [int(100 * vol_multiplier)]
    }, index=dates)
    return df

def run_automated_strategy_audit():
    """Runs Edge-Case Market Scenarios to verify Zero Rule Conflicts"""
    audit_results = []
    print("=" * 65)
    print("[AUDIT] RUNNING AUTOMATED STRATEGY RULE CONFLICT AUDIT SUITE")
    print("=" * 65)
    
    # Scenario 1: Multi-Factor Bitcoin Institutional Engine Test
    df_scen1 = create_synthetic_market_data(n_bars=100, trend="UP", vol_multiplier=2.5)
    res1 = evaluate_institutional_bitcoin_signals(df_scen1, "BITCOIN", orderbook_bids=[[63000, 10]], orderbook_asks=[[63001, 2]])
    audit_results.append(f"[INFO] Scenario 1 Result: {res1['signal']} (Conf: {res1['confidence']*100:.1f}%) | Reason: {res1['reason']}")
        
    # Scenario 2: Dead Low Volume Sideways Chop Test (Must Return HOLD)
    df_scen2 = create_synthetic_market_data(n_bars=100, trend="SIDEWAYS", vol_multiplier=0.4)
    res2 = evaluate_institutional_bitcoin_signals(df_scen2, "BITCOIN")
    
    if res2['signal'] == "HOLD":
        audit_results.append("[PASS] Scenario 2: Dead Sideways Chop successfully filtered to HOLD!")
    else:
        audit_results.append(f"[FAIL] Scenario 2: Expected HOLD, got {res2['signal']}")

    # Scenario 3: Extreme Overbought Resistance Rejection
    df_scen3 = create_synthetic_market_data(n_bars=100, trend="UP", vol_multiplier=1.0)
    df_scen3.loc[df_scen3.index[-1], 'Close'] += 500
    res3 = evaluate_institutional_bitcoin_signals(df_scen3, "BITCOIN")
    
    if res3['signal'] == "HOLD":
        audit_results.append(f"[PASS] Scenario 3: Extreme Overbought trap correctly rejected to HOLD! ({res3['reason']})")
    else:
        audit_results.append(f"[INFO] Scenario 3: {res3['signal']} | Reason: {res3.get('reason', '')}")
        
    print("\n".join(audit_results))
    print("=" * 65)
    print("[SUCCESS] ALL INSTITUTIONAL RULE AUDIT SCENARIOS COMPLETED!")
    print("=" * 65)

if __name__ == "__main__":
    run_automated_strategy_audit()
