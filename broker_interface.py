# broker_interface.py
import abc
import logging
import time
import hmac
import hashlib
import requests
import streamlit as st

class BaseBroker(abc.ABC):
    @abc.abstractmethod
    def authenticate(self): pass
    @abc.abstractmethod
    def place_order(self, symbol, order_type, quantity, price=0.0): pass
    @abc.abstractmethod
    def get_positions(self): pass

class PaperBrokerAdapter(BaseBroker):
    def __init__(self):
        self.authenticate()

    def authenticate(self):
        logging.info("🎮 Paper Trading Broker Active (2-Week Test Phase)")
        return True

    def place_order(self, symbol, order_type, quantity, price=0.0):
        # Local & Cloud Session Paper Order Simulator
        return {"status": "SUCCESS", "mode": "PAPER_TRADING", "symbol": symbol, "qty": quantity, "price": price}

    def get_positions(self):
        return []

class BinanceSpotBroker(BaseBroker):
    def __init__(self, api_key="", secret_key=""):
        self.api_key = str(api_key).strip() if api_key else ""
        self.secret_key = str(secret_key).strip() if secret_key else ""
        self.is_authenticated = False
        self.base_urls = [
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com",
            "https://api4.binance.com",
            "https://api.binance.com"
        ]
        if self.api_key and self.secret_key:
            self.authenticate()

    def _sign_and_request(self, method: str, endpoint: str, params: dict = None):
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 60000
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(self.secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        full_query = f"{query_string}&signature={signature}"
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        for base in self.base_urls:
            try:
                url = f"{base}{endpoint}?{full_query}"
                if method.upper() == "GET":
                    res = requests.get(url, headers=headers, timeout=4)
                elif method.upper() == "POST":
                    res = requests.post(url, headers=headers, timeout=4)
                else:
                    res = requests.request(method, url, headers=headers, timeout=4)
                    
                if res.status_code == 200:
                    return True, res.json()
            except Exception:
                continue
        return False, {}

    def authenticate(self):
        success, data = self._sign_and_request("GET", "/api/v3/account")
        self.is_authenticated = success
        return success

    def get_spot_usdt_balance(self):
        success, data = self._sign_and_request("GET", "/api/v3/account")
        if success:
            balances = data.get('balances', [])
            for b in balances:
                if b.get('asset') == 'USDT':
                    return float(b.get('free', 0.0))
        return 0.0

    def place_order(self, symbol, order_type, quantity, price=0.0):
        sym_upper = str(symbol).upper()
        pair = "BTCUSDT" if ("BITCOIN" in sym_upper or "BTC" in sym_upper) else ("ETHUSDT" if "ETH" in sym_upper else f"{sym_upper}USDT")
        
        side = "BUY" if str(order_type).upper() in ["BUY", "CALL"] else "SELL"
        
        params = {
            "symbol": pair,
            "side": side,
            "type": "MARKET",
            "quantity": float(quantity)
        }
        
        success, data = self._sign_and_request("POST", "/api/v3/order", params)
        if success:
            return {"status": "SUCCESS", "order": data, "order_id": data.get('orderId')}
        else:
            return {"status": "FAILED", "reason": "Binance Order API error or restriction"}

    def get_positions(self):
        success, data = self._sign_and_request("GET", "/api/v3/account")
        return data if success else {}

class ZerodhaKiteBroker(BaseBroker):
    def __init__(self, api_key="", access_token=""):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = None

    def authenticate(self):
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            return True
        except Exception as e:
            logging.error(f"Zerodha Auth Error: {e}")
            return False

    def place_order(self, symbol, order_type, quantity, price=0.0):
        if not self.kite:
            return {"status": "FAILED", "reason": "Zerodha Not Authenticated"}
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NFO if ("CE" in symbol or "PE" in symbol) else self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=self.kite.TRANSACTION_TYPE_BUY if order_type == "BUY" else self.kite.TRANSACTION_TYPE_SELL,
                quantity=quantity,
                product=self.kite.PRODUCT_MIS,
                order_type=self.kite.ORDER_TYPE_MARKET
            )
            return {"status": "SUCCESS", "order_id": order_id}
        except Exception as e:
            return {"status": "FAILED", "reason": str(e)}

    def get_positions(self):
        return self.kite.positions() if self.kite else {}


# =============================================================
# MULTI-COIN CRYPTO RADAR EXTENSION (BTC, ETH, SOL, BNB, XRP)
# =============================================================

CRYPTO_RADAR_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT"
]

def get_binance_geofence_bypassed_exchange(api_key: str, secret_key: str):
    """Configures CCXT to bypass US Cloud IP Geofence via Asian CDN Endpoints"""
    return ccxt.binance({
        'apiKey': api_key.strip(),
        'secret': secret_key.strip(),
        'enableRateLimit': True,
        'urls': {
            'api': {
                'public': 'https://api1.binance.com/api/v3',
                'private': 'https://api1.binance.com/api/v3',
            }
        },
        'options': {
            'defaultType': 'spot',
            'adjustForTimeDifference': True
        }
    })

def execute_multi_coin_live_order(symbol: str, side: str, usdt_amount: float = 5.00, ai_confidence: float = 0.70):
    """
    Executes Micro $5.00 USDT Order across Top 5 Crypto Pairs without breaking BinanceSpotBroker class
    """
    api_key = st.session_state.get('binance_api_key', '')
    secret_key = st.session_state.get('binance_secret_key', '')
    
    if not api_key or not secret_key:
        return None

    if ai_confidence < 0.70:
        return None

    try:
        exchange = get_binance_geofence_bypassed_exchange(api_key, secret_key)

        ticker = exchange.fetch_ticker(symbol)
        curr_price = float(ticker['last'])
        raw_qty = usdt_amount / curr_price
        formatted_qty = float(exchange.amount_to_precision(symbol, raw_qty))

        if side.upper() in ['BUY', 'LONG', 'CALL']:
            return exchange.create_market_buy_order(symbol, formatted_qty)
        else:
            return exchange.create_market_sell_order(symbol, formatted_qty)
    except Exception as e:
        print(f"Multi-Coin Order Error ({symbol}): {e}")
        return None

execute_binance_live_order = execute_multi_coin_live_order
