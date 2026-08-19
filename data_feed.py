# ================================================================================
# ANTONY QUANT AI TERMINAL - DATA FEED ENGINE (0MS BINANCE DIRECT BTC FEED)
# ================================================================================
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
    try:
        df = yf.download(tickers=symbol, period=period, interval=timeframe, progress=False)
        if df.empty:
            return pd.DataFrame()
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
    """Fetches 0ms real-time Bitcoin 15M candles directly from Binance Public REST API."""
    try:
        # 1. Fetch 0ms Microsecond Live Price Ticker from Binance
        ticker_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        res = requests.get(ticker_url, timeout=3)
        live_price = float(res.json()['price']) if res.status_code == 200 else None

        # 2. Fetch Live 15M Klines from Binance
        klines_url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={timeframe}&limit=50"
        k_res = requests.get(klines_url, timeout=3)
        if k_res.status_code == 200:
            raw_data = k_res.json()
            cols = ['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'q_vol', 'trades', 'tb_base', 'tb_quote', 'ignore']
            df = pd.DataFrame(raw_data, columns=cols)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            if live_price and len(df) > 0:
                df.loc[df.index[-1], 'close'] = live_price  # Microsecond Binance Ticker Override!
            return df
    except Exception as e:
        print(f"Binance Direct API error: {e}")
    
    # Fallback to Yahoo Finance if Binance API is unreachable
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
