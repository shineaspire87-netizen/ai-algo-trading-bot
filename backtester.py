# backtester.py
import pandas as pd
import numpy as np

class InstitutionalBacktester:
    def __init__(self, initial_capital=100000, friction_per_trade=45.0):
        self.capital = initial_capital
        self.friction = friction_per_trade

    def run_backtest(self, df: pd.DataFrame, target_pct=0.06, sl_pct=0.03):
        trades = []
        equity_curve = [self.capital]
        current_capital = self.capital

        for i in range(len(df) - 1):
            row = df.iloc[i]
            # Entry Signal Check: Candle Body >= 60%, ADX > 25, Price > VWAP
            if row['Body_Range_Ratio'] >= 0.60 and row['ADX'] > 25.0 and row['Close'] > row['VWAP']:
                entry_price = df.iloc[i+1]['Open']
                tp = entry_price * (1 + target_pct)
                sl = entry_price * (1 - sl_pct)
                
                # Single Candle 5-Min Expiry Check
                exit_price = df.iloc[i+1]['Close']
                if df.iloc[i+1]['High'] >= tp:
                    exit_price = tp
                    status = "TARGET_HIT"
                elif df.iloc[i+1]['Low'] <= sl:
                    exit_price = sl
                    status = "SL_HIT"
                else:
                    status = "SINGLE_CANDLE_TIMEOUT"

                pnl = (exit_price - entry_price) / entry_price * current_capital - self.friction
                current_capital += pnl
                equity_curve.append(current_capital)

                trades.append({
                    "Timestamp": df.index[i+1],
                    "Entry": entry_price,
                    "Exit": exit_price,
                    "PnL": pnl,
                    "Status": status
                })

        trades_df = pd.DataFrame(trades)
        win_rate = (len(trades_df[trades_df['PnL'] > 0]) / len(trades_df)) * 100 if len(trades_df) > 0 else 0
        profit_factor = trades_df[trades_df['PnL'] > 0]['PnL'].sum() / abs(trades_df[trades_df['PnL'] < 0]['PnL'].sum() + 1e-6)

        return {
            "Equity_Curve": equity_curve,
            "Trades_Log": trades_df,
            "Win_Rate": win_rate,
            "Profit_Factor": profit_factor,
            "Final_Capital": current_capital
        }
