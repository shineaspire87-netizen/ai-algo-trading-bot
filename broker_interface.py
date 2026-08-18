# broker_interface.py
import abc
import logging

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
        self.exchange = None
        self.is_authenticated = False
        if self.api_key and self.secret_key:
            self.authenticate()

    def authenticate(self):
        try:
            import ccxt
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            # Verify live connectivity
            bal = self.exchange.fetch_balance()
            self.is_authenticated = True
            return True
        except Exception as e:
            logging.error(f"Binance Auth Error: {e}")
            self.is_authenticated = False
            self.exchange = None
            return False

    def get_spot_usdt_balance(self):
        try:
            if self.exchange:
                balance = self.exchange.fetch_balance()
                return float(balance['free'].get('USDT', 0.0))
        except Exception as e:
            logging.error(f"Binance Balance Fetch Error: {e}")
        return 0.0

    def place_order(self, symbol, order_type, quantity, price=0.0):
        if not self.exchange:
            return {"status": "FAILED", "reason": "Binance Exchange Not Initialized"}
        try:
            sym_upper = str(symbol).upper()
            pair = "BTC/USDT" if ("BITCOIN" in sym_upper or "BTC" in sym_upper) else ("ETH/USDT" if "ETH" in sym_upper else f"{sym_upper}/USDT")
            
            if order_type.upper() in ["BUY", "CALL"]:
                order = self.exchange.create_market_buy_order(pair, quantity)
            else:
                order = self.exchange.create_market_sell_order(pair, quantity)
            return {"status": "SUCCESS", "order": order, "order_id": order.get('id')}
        except Exception as e:
            logging.error(f"Binance Live Order Error: {e}")
            return {"status": "FAILED", "reason": str(e)}

    def get_positions(self):
        try:
            if self.exchange:
                return self.exchange.fetch_balance()
        except:
            pass
        return {}

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
