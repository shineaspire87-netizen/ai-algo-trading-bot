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
