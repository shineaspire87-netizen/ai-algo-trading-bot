# multi_strategy.py - With Direct Telegram Mobile Alerts & Hurst Engine
import os
import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import ta
import numpy as np
from xgboost import XGBClassifier
from notifier import send_telegram_alert

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
    "SBIN": "SBIN.NS",
    "BITCOIN": "BTC-USD",
    "ETHEREUM": "ETH-USD"
}

last_notified_signal = {}

def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
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

def calculate_daily_reset_vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3.0
    vol = df['Volume'].replace(0, np.nan).fillna(1)
    vol_price = typical_price * vol
    dates = df.index.date
    cum_vol_price = vol_price.groupby(dates).cumsum()
    cum_vol = vol.groupby(dates).cumsum()
    vwap = cum_vol_price / cum_vol
    return vwap.fillna(typical_price)

def calculate_garman_klass_volatility(df: pd.DataFrame, window: int = 14) -> pd.Series:
    log_hl = np.log(df['High'] / df['Low']) ** 2
    log_co = np.log(df['Close'] / df['Open']) ** 2
    gk = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co
    return np.sqrt(gk.rolling(window).mean()).fillna(0)

def scan_all_assets():
    now_dt = datetime.datetime.now()
    now_time = now_dt.time()
    today_weekday = now_dt.weekday()
    
    best_opportunity = None
    scanned_results = []

    for name, symbol in WATCHLIST.items():
        is_crypto = "USD" in symbol
        is_market_open = (today_weekday < 5 and datetime.time(9, 15) <= now_time <= datetime.time(15, 30)) or is_crypto

        if not is_market_open:
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
            
            adx_ind = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
            df['ADX'] = adx_ind.adx()
            
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            df['ATR_Pct'] = (df['ATR'] / df['Close']) * 100.0
            df['GK_Volatility'] = calculate_garman_klass_volatility(df, window=14)
            
            df['VWAP'] = calculate_daily_reset_vwap(df)
            df['VWAP_Diff'] = (df['Close'] - df['VWAP']) / df['VWAP']
            
            bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
            df['BB_Width'] = bb.bollinger_wband()
            df['BB_Pband'] = bb.bollinger_pband()

            df['Hour'] = df.index.hour
            df['Minute'] = df.index.minute
            df['Is_Morning_Open'] = ((df['Hour'] == 9) & (df['Minute'] >= 15) | (df['Hour'] == 10)).astype(int)
            df['Is_Lunch_Chop'] = ((df['Hour'] >= 11) & (df['Hour'] <= 13)).astype(int)
            df['Is_Power_Hour'] = ((df['Hour'] == 14) | ((df['Hour'] == 15) & (df['Minute'] <= 15))).astype(int)

            df['Return_1'] = df['Close'].pct_change(1)
            df['Return_3'] = df['Close'].pct_change(3)

            df = detect_candlestick_patterns(df)
            latest = df.iloc[-1]

            if model is not None:
                features = pd.DataFrame([{
                    'RSI': latest['RSI'],
                    'EMA_Diff': latest['EMA_Diff'],
                    'ADX': latest['ADX'],
                    'ATR_Pct': latest['ATR_Pct'],
                    'GK_Volatility': latest['GK_Volatility'],
                    'VWAP_Diff': latest['VWAP_Diff'],
                    'BB_Width': latest['BB_Width'],
                    'BB_Pband': latest['BB_Pband'],
                    'Return_1': latest['Return_1'],
                    'Return_3': latest['Return_3'],
                    'Is_Morning_Open': latest['Is_Morning_Open'],
                    'Is_Lunch_Chop': latest['Is_Lunch_Chop'],
                    'Is_Power_Hour': latest['Is_Power_Hour'],
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

            if signal != "HOLD" and last_notified_signal.get(name) != signal:
                last_notified_signal[name] = signal
                alert_msg = f"🚨 <b>AI TRADE SIGNAL DETECTED!</b>\n\n<b>Asset:</b> {name}\n<b>Signal:</b> {signal}\n<b>Live Price:</b> {latest['Close']:,.2f}\n<b>RSI:</b> {latest['RSI']:.1f}\n<b>Time:</b> {now_dt.strftime('%H:%M:%S IST')}"
                send_telegram_alert(alert_msg)

            scanned_results.append({
                "Name": name, "Symbol": symbol, "Price": latest['Close'], "RSI": latest['RSI'], "Signal": signal
            })

            if signal != "HOLD" and best_opportunity is None:
                best_opportunity = {"Name": name, "Symbol": symbol, "Price": latest['Close'], "Signal": signal}

        except Exception as e:
            continue

    return best_opportunity, scanned_results

def is_daily_limit_reached(completed_trades_count: int) -> bool:
    """Check if 3 trades daily limit is reached (Bypassed if Extended Testing Mode is ON)"""
    
    # Check if user enabled the temporary testing toggle in Dashboard
    is_testing_mode_on = st.session_state.get('allow_extended_trades', False)
    
    if is_testing_mode_on:
        # Testing Mode is ON -> Allow scanning beyond 3 trades
        return False
        
    # Default Safe Mode -> Hard Lock at 3 completed trades
    return completed_trades_count >= 3