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
