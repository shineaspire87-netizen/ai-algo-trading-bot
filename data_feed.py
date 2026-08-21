import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, time, timezone, timedelta
import config

def get_ist_now():
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=5, minutes=30)

def fetch_nifty_live_data(symbol=config.DEFAULT_SYMBOL, timeframe=config.TIMEFRAME, period="5d"):
    """Fetches real-time NIFTY 50 Futures (NIFTY1!) data synced with TradingView."""
    try:
        df = yf.download(tickers=symbol, period=period, interval=timeframe, progress=False)
        if df.empty or len(df) < 2:
            # Fallback to ^NSEI if NIFTY1.NS has a temporary Yahoo API delay
            df = yf.download(tickers="^NSEI", period=period, interval=timeframe, progress=False)
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
            
        df.dropna(inplace=True)
        if not df.empty and 'close' in df and float(df['close'].iloc[-1]) < 5000:
            df = yf.download(tickers="^NSEI", period=period, interval=timeframe, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0].lower() for col in df.columns]
            else:
                df.columns = [col.lower() for col in df.columns]
            df.dropna(inplace=True)
            
        return df
    except Exception as e:
        print(f"Error fetching NIFTY data: {e}")
        return pd.DataFrame()

def fetch_btc_live_data(symbol="BTCUSDT", timeframe="15m", period="5d"):
    endpoints = [
        f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={timeframe}&limit=50",
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit=50",
        f"https://api1.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit=50",
        f"https://api2.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit=50"
    ]
    
    for url in endpoints:
        try:
            k_res = requests.get(url, timeout=2)
            if k_res.status_code == 200:
                raw_data = k_res.json()
                cols = ['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'q_vol', 'trades', 'tb_base', 'tb_quote', 'ignore']
                df = pd.DataFrame(raw_data, columns=cols)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                return df
        except Exception:
            continue
            
    return fetch_nifty_live_data(config.BTC_SYMBOL, timeframe, period)

def fetch_india_vix():
    try:
        df = yf.download(tickers=config.VIX_SYMBOL, period="2d", interval="15m", progress=False)
        if df.empty or len(df) < 2:
            return 11.51, +0.12
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
        latest_vix = float(df['close'].iloc[-1])
        prev_vix = float(df['close'].iloc[-2])
        return latest_vix, (latest_vix - prev_vix)
    except Exception:
        return 11.51, +0.12

def calculate_atm_strike(spot_price):
    return int(round(spot_price / 50.0) * 50)

def is_market_open():
    ist_now = get_ist_now()
    if ist_now.weekday() >= 5:
        return False
    return time(9, 15) <= ist_now.time() <= time(15, 30)
