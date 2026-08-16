# backtester.py
import pandas as pd
import numpy as np

def run_historical_backtest(df, initial_capital=100000, target_pct=0.06, sl_pct=0.03, friction=45.0):
    if df is None or len(df) < 30:
        return None
    
    df = df.copy()
    # Body Range Ratio
    df['Body_Ratio'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-6)
    
    trades = []
    capital = initial_capital
    equity = [capital]
    
    for i in range(20, len(df) - 1):
        row = df.iloc[i]
        # Core Entry Rules Check
        if row['Body_Ratio'] >= 0.60:
            entry = df.iloc[i+1]['Open']
            tp = entry * (1 + target_pct)
            sl = entry * (1 - sl_pct)
            
            next_candle = df.iloc[i+1]
            if next_candle['High'] >= tp:
                exit_p = tp
                res = "TARGET (+6%)"
            elif next_candle['Low'] <= sl:
                exit_p = sl
                res = "STOP LOSS (-3%)"
            else:
                exit_p = next_candle['Close']
                res = "5-MIN TIMEOUT"
                
            pnl = ((exit_p - entry) / entry) * capital - friction
            capital += pnl
            equity.append(capital)
            
            trades.append({"Time": df.index[i+1], "Type": "BUY", "Entry": entry, "Exit": exit_p, "PnL": pnl, "Result": res})
            
    tdf = pd.DataFrame(trades)
    wins = len(tdf[tdf['PnL'] > 0]) if len(tdf) > 0 else 0
    total = len(tdf) if len(tdf) > 0 else 1
    win_rate = (wins / total) * 100
    
    return {
        "trades": tdf,
        "equity": equity,
        "win_rate": round(win_rate, 2),
        "total_trades": total,
        "final_capital": round(capital, 2),
        "total_profit": round(capital - initial_capital, 2)
    }

def run_institutional_backtest_with_slippage(df: pd.DataFrame, initial_capital: float = 100000.0, slippage_pct: float = 0.0008, brokerage_flat: float = 40.0):
    """Vectorized Backtest Engine with Realistic Slippage (0.08%) & Spread Cost"""
    if df is None or len(df) < 30:
        return None
        
    df = df.copy()
    df['Body_Ratio'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-6)
    
    trades = []
    capital = initial_capital
    equity_curve = [capital]
    
    for i in range(20, len(df) - 1):
        row = df.iloc[i]
        if row['Body_Ratio'] >= 0.60:
            raw_entry = df.iloc[i+1]['Open']
            
            # Apply Realistic Slippage (0.08% Buy Slippage)
            entry_price = raw_entry * (1 + slippage_pct)
            
            # Dynamic ATR Distance
            atr_val = row.get('ATR', raw_entry * 0.01)
            tp = entry_price + (atr_val * 3.0)
            sl = entry_price - (atr_val * 1.5)
            
            next_bar = df.iloc[i+1]
            if next_bar['High'] >= tp:
                raw_exit = tp
            elif next_bar['Low'] <= sl:
                raw_exit = sl
            else:
                raw_exit = next_bar['Close']
                
            # Apply Realistic Slippage (0.08% Sell Slippage)
            exit_price = raw_exit * (1 - slippage_pct)
            
            # PnL Calculation minus Slippage & Brokerage/STT Friction
            gross_pnl = (exit_price - entry_price) / entry_price * capital
            stt_gst = (exit_price * 0.0015) + 5.0
            total_friction = brokerage_flat + stt_gst
            net_pnl = gross_pnl - total_friction
            
            capital += net_pnl
            equity_curve.append(capital)
            
            trades.append({
                "Entry": round(entry_price, 2),
                "Exit": round(exit_price, 2),
                "Gross_PnL": round(gross_pnl, 2),
                "Friction_Cost": round(total_friction, 2),
                "Net_PnL": round(net_pnl, 2)
            })
            
    tdf = pd.DataFrame(trades)
    return {
        "trades": tdf,
        "equity": equity_curve,
        "final_capital": round(capital, 2)
    }
