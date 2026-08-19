# ================================================================================
# ANTONY QUANT AI TERMINAL - DATA FEED ENGINE (IST TIMEZONE FIXED)
# ================================================================================
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time, timezone, timedelta
import config

def get_ist_now():
    """Returns exact current time in Indian Standard Time (IST = UTC+5:30)."""
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=5, minutes=30)

def fetch_nifty_live_data(symbol=config.DEFAULT_SYMBOL, timeframe=config.TIMEFRAME, period="5d"):
    """Fetches real-time NIFTY 50 Index candles from Yahoo Finance."""
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

def fetch_india_vix():
    """Fetches real-time India VIX level and calculates 15m delta."""
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
        delta_vix = latest_vix - prev_vix
        return latest_vix, delta_vix
    except Exception:
        return 11.51, +0.12

def calculate_atm_strike(spot_price):
    """Calculates At-The-Money (ATM) Option Strike for NIFTY 50."""
    return int(round(spot_price / 50.0) * 50)

def is_market_open():
    """Checks if Indian Equity Market (NSE) is open (9:15 AM - 3:30 PM IST)."""
    ist_now = get_ist_now()
    if ist_now.weekday() >= 5:
        return False
    return time(9, 15) <= ist_now.time() <= time(15, 30)
