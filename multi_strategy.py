# multi_strategy.py - Institutional Strategy with ADX Regime & Time Filters
import os
import datetime
import yfinance as yf
import pandas as pd
import ta
import numpy as np
from xgboost import XGBClassifier

MODEL_FILE = "xgboost_model.json"
model = None

if os.path.exists(MODEL_FILE):
    model = XGBClassifier()
    model.load_model(MODEL_FILE)

WATCHLIST = {
    "BANKNIFTY": "^NSEBANK",
    "NIFTY50": "^NSEI",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",
    "SBIN": "SBIN.NS"
}

def scan_all_assets():
    now_time = datetime.datetime.now().time()
    
    # 1. No-Trade Time Zone (9:15 - 9:30 AM Opening Volatility Trap)
    if datetime.time(9, 15) <= now_time < datetime.time(9, 30):
        return None, []

    # 2. Expiry Day Rule (No fresh buying after 1:30 PM)
    today_weekday = datetime.datetime.now().weekday()
    if today_weekday == 3 and now_time >= datetime.time(13, 30): # Thursday Expiry
        return None, []

    best_opportunity = None
    scanned_results = []

    for name, symbol in WATCHLIST.items():
        try:
            df = yf.download(tickers=symbol, period="5d", interval="5m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df.empty or len(df) < 25:
                continue

            # Indicators & Market Regime (ADX)
            df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
            df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
            df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
            df['EMA_Diff'] = (df['EMA_9'] - df['EMA_21']) / df['EMA_21']
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)['ADX_14']
            
            vol = df['Volume'].replace(0, np.nan).fillna(1)
            typical_price = (df['High'] + df['Low'] + df['Close']) / 3
            df['VWAP'] = (typical_price * vol).cumsum() / vol.cumsum()
            df['VWAP_Diff'] = (df['Close'] - df['VWAP']) / df['VWAP']
            df['Return_1'] = df['Close'].pct_change(1)
            df['Return_3'] = df['Close'].pct_change(3)

            latest = df.iloc[-1]
            adx_val = latest['ADX']

            # ADX Regime Filter: ADX < 20 means Sideways market -> HOLD
            if adx_val < 20:
                signal = "HOLD"
            elif model is not None:
                features = pd.DataFrame([{
                    'RSI': latest['RSI'],
                    'EMA_Diff': latest['EMA_Diff'],
                    'ATR': latest['ATR'],
                    'VWAP_Diff': latest['VWAP_Diff'],
                    'Return_1': latest['Return_1'],
                    'Return_3': latest['Return_3'],
                    'Pattern_Doji': 0, 'Pattern_Marubozu': 0, 'Pattern_Hammer': 0,
                    'Pattern_ShootingStar': 0, 'Pattern_BullishEngulfing': 0, 'Pattern_BearishEngulfing': 0
                }]).fillna(0)

                # High Confidence Threshold (Prob >= 75%)
                probs = model.predict_proba(features)[0]
                max_prob = np.max(probs)
                pred = model.predict(features)[0]

                if max_prob >= 0.75:
                    signal = "BUY_CALL" if pred == 2 else ("BUY_PUT" if pred == 0 else "HOLD")
                else:
                    signal = "HOLD"
            else:
                signal = "BUY_CALL" if (latest['EMA_9'] > latest['EMA_21'] and latest['RSI'] > 58) else ("BUY_PUT" if (latest['EMA_9'] < latest['EMA_21'] and latest['RSI'] < 42) else "HOLD")

            scanned_results.append({
                "Name": name, "Symbol": symbol, "Price": latest['Close'], "RSI": latest['RSI'], "Signal": signal
            })

            if signal != "HOLD" and best_opportunity is None:
                best_opportunity = {"Name": name, "Symbol": symbol, "Price": latest['Close'], "Signal": signal}

        except:
            continue

    return best_opportunity, scanned_results