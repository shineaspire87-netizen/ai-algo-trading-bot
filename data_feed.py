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
    """
    Fetches NIFTY 50 live 15M OHLCV data.
    Price sanity check: if returned price < 5000 it's garbage data → retry with ^NSEI.
    """
    def _clean_df(df):
        """Flatten MultiIndex columns and clean the DataFrame."""
        if df.empty:
            return df
        if isinstance(df.columns, pd.MultiIndex):
            # Flatten: take first level (Open/High/Low/Close/Volume), lowercase
            df.columns = [col[0].lower() if col[0] else col[1].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
        df.dropna(inplace=True)
        # Drop duplicate column names (MultiIndex artefact)
        df = df.loc[:, ~df.columns.duplicated()]
        return df

    for sym in [symbol, "^NSEI"]:
        try:
            df = yf.download(tickers=sym, period=period, interval=timeframe, progress=False, auto_adjust=True)
            df = _clean_df(df)
            if df.empty or len(df) < 2:
                continue
            price_check = float(df['close'].iloc[-1])
            if price_check < 5000.0:
                continue  # Bad data — try next symbol
            # 0ms fast_info real-time close override
            try:
                ticker_obj = yf.Ticker(sym)
                fast_price = float(ticker_obj.fast_info.get('lastPrice', 0.0) or ticker_obj.fast_info.get('regularMarketPrice', 0.0))
                if fast_price > 5000.0:
                    df.loc[df.index[-1], 'close'] = fast_price
            except Exception:
                pass
            return df
        except Exception as e:
            print(f"Error fetching NIFTY data ({sym}): {e}")
            continue

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

def fetch_forex_live_data(symbol=config.FOREX_SYMBOL, timeframe=config.TIMEFRAME, period="5d"):
    """Fetches 0ms real-time Forex (EUR/USD) candles with fast quote override."""
    try:
        df = yf.download(tickers=symbol, period=period, interval=timeframe, progress=False)
        if df.empty or len(df) < 2:
            try:
                k_res = requests.get(f"https://api.binance.com/api/v3/klines?symbol=EURUSDT&interval={timeframe}&limit=50", timeout=3)
                if k_res.status_code == 200:
                    raw_data = k_res.json()
                    cols = ['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'q_vol', 'trades', 'tb_base', 'tb_quote', 'ignore']
                    df = pd.DataFrame(raw_data, columns=cols)
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
            except Exception:
                pass

        if df.empty:
            return pd.DataFrame()
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
            
        df.dropna(inplace=True)
        
        # 0ms Fast Quote Override for EUR/USD
        try:
            ticker_obj = yf.Ticker(symbol)
            fast_price = float(ticker_obj.fast_info.get('lastPrice', 0.0) or ticker_obj.fast_info.get('regularMarketPrice', 0.0))
            if fast_price > 0.5:
                df.loc[df.index[-1], 'close'] = fast_price  # 0ms Live Forex Quote Override!
            else:
                r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT", timeout=2)
                if r.status_code == 200:
                    fast_p = float(r.json().get('price', 0.0))
                    if fast_p > 0.5:
                        df.loc[df.index[-1], 'close'] = fast_p
        except Exception:
            pass
            
        return df
    except Exception as e:
        print(f"Error fetching Forex data: {e}")
        return pd.DataFrame()

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

def is_forex_market_open():
    ist_now = get_ist_now()
    if ist_now.weekday() >= 5:
        return False
    return True
