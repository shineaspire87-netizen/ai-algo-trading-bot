# multi_strategy.py - Multi-Asset & 24/7 Crypto Strategy
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

# 24/7 Multi-Asset Watchlist (Includes Bitcoin & Ethereum)
WATCHLIST = {
    'BANKNIFTY': '^NSEBANK',
    'NIFTY50': '^NSEI',
    'RELIANCE': 'RELIANCE.NS',
    'HDFCBANK': 'HDFCBANK.NS',
    'ICICIBANK': 'ICICIBANK.NS',
    'INFY': 'INFY.NS',
    'SBIN': 'SBIN.NS',
    'BITCOIN': 'BTC-USD',
    'ETHEREUM': 'ETH-USD'
}

def detect_candlestick_patterns(df):
    open_p, high_p, low_p, close_p = df['Open'], df['High'], df['Low'], df['Close']
    body = abs(close_p - open_p)
    candle_range = (high_p - low_p).replace(0, 0.001)
    
    df['Pattern_Doji'] = (body <= (candle_range * 0.1)).astype(int)
    df['Pattern_Marubozu'] = (body >= (candle_range * 0.85)).astype(int)
    lower_shadow = np.minimum(open_p, close_p) - low_p
    df['Pattern_Hammer'] = ((lower_shadow >= (body * 2)) & (body > 0)).astype(int)
    upper_shadow = high_p - np.maximum(open_p, close_p)
    df['Pattern_ShootingStar'] = ((upper_shadow >= (body * 2)) & (body > 0)).astype(int)
    df['Pattern_BullishEngulfing'] = ((close_p > open_p) & (close_p.shift(1) < open_p.shift(1)) & (close_p >= open_p.shift(1))).astype(int)
    df['Pattern_BearishEngulfing'] = ((close_p < open_p) & (close_p.shift(1) > open_p.shift(1)) & (close_p <= open_p.shift(1))).astype(int)
    return df

def scan_all_assets():
    now_time = datetime.datetime.now().time()
    today_weekday = datetime.datetime.now().weekday()
    
    best_opportunity = None
    scanned_results = []

    for name, symbol in WATCHLIST.items():
        is_crypto = "USD" in symbol
        is_market_open = (today_weekday < 5 and datetime.time(9, 15) <= now_time <= datetime.time(15, 30)) or is_crypto

        if not is_market_open:
            continue

        # Opening Range Trap Avoidance for Indian Market
        if not is_crypto and (datetime.time(9, 15) <= now_time < datetime.time(9, 30)):
            continue

        # Expiry Day 1:30 PM Rule for Indian Options
        if not is_crypto and today_weekday == 3 and now_time >= datetime.time(13, 30):
            continue

        try:
            df = yf.download(tickers=symbol, period="5d", interval="5m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df.empty or len(df) < 25:
                continue

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

            df = detect_candlestick_patterns(df)
            latest = df.iloc[-1]
            adx_val = latest['ADX']

            if adx_val < 20 and not is_crypto:
                signal = "HOLD"
            elif model is not None:
                features = pd.DataFrame([{
                    'RSI': latest['RSI'],
                    'EMA_Diff': latest['EMA_Diff'],
                    'ATR': latest['ATR'],
                    'VWAP_Diff': latest['VWAP_Diff'],
                    'Return_1': latest['Return_1'],
                    'Return_3': latest['Return_3'],
                    'Pattern_Doji': latest['Pattern_Doji'],
                    'Pattern_Marubozu': latest['Pattern_Marubozu'],
                    'Pattern_Hammer': latest['Pattern_Hammer'],
                    'Pattern_ShootingStar': latest['Pattern_ShootingStar'],
                    'Pattern_BullishEngulfing': latest['Pattern_BullishEngulfing'],
                    'Pattern_BearishEngulfing': latest['Pattern_BearishEngulfing']
                }]).fillna(0)

                probs = model.predict_proba(features)[0]
                max_prob = np.max(probs)
                pred = model.predict(features)[0]

                if max_prob >= 0.70:
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