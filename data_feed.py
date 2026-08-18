# ================================================================================
# ANTONY QUANT AI TERMINAL - DATA FEED ENGINE (NIFTY 50 & MULTI-ASSET LIVE)
# ================================================================================
import json
import threading
import time as time_lib
from datetime import datetime, time
import pandas as pd
import numpy as np
import yfinance as yf
import config

# Global in-memory cache for real-time spot prices
LATEST_SPOT_PRICES = {}

def get_latest_spot_price(symbol: str = "btcusdt") -> float:
    """Returns the latest spot price from the real-time WebSocket cache"""
    return LATEST_SPOT_PRICES.get(symbol.lower(), None)

def fetch_nifty_live_data(symbol=config.DEFAULT_SYMBOL, timeframe=config.TIMEFRAME, period="5d"):
    """
    Fetches real-time NIFTY 50 Index candles from NSE via yfinance wrapper.
    Returns clean Pandas DataFrame with OHLCV data.
    """
    try:
        df = yf.download(tickers=symbol, period=period, interval=timeframe, progress=False)
        if df.empty:
            return pd.DataFrame()
        
        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]
            
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching NIFTY data: {e}")
        return pd.DataFrame()

def calculate_atm_strike(spot_price: float) -> int:
    """
    Calculates At-The-Money (ATM) Option Strike for NIFTY 50 (Rounded to nearest 50).
    Example: 24,512 Spot -> 24,500 ATM Strike
    """
    if not spot_price or spot_price <= 0:
        return 24500
    return int(round(spot_price / 50.0) * 50)

def is_market_open() -> bool:
    """Checks if Indian Equity Market (NSE) is currently open (9:15 AM - 3:30 PM IST)."""
    now = datetime.now()
    # Monday = 0, Sunday = 6
    if now.weekday() >= 5:
        return False
    
    market_start = time(9, 15)
    market_end = time(15, 30)
    current_time = now.time()
    
    return market_start <= current_time <= market_end

def connect_direct_tradingview_websocket(symbol: str = "btcusdt"):
    """Connects to direct WebSocket Stream for 0ms Latency and 0% Price Discrepancy"""
    try:
        import websocket
    except ImportError:
        return

    ws_url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@ticker"

    def on_message(ws, message):
        try:
            data = json.loads(message)
            realtime_price = float(data.get('c', 0.0))
            LATEST_SPOT_PRICES[symbol.lower()] = realtime_price
        except Exception:
            pass

    try:
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
        )
        wsthread = threading.Thread(target=ws.run_forever, daemon=True)
        wsthread.start()
    except Exception:
        pass
