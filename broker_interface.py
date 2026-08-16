# broker_interface.py
import abc
import logging
from config import ACTIVE_BROKER, PAPER_TRADING_MODE, ZERODHA_CONFIG, DHAN_CONFIG

class BaseBroker(abc.ABC):
    @abc.abstractmethod
    def authenticate(self):
        pass

    @abc.abstractmethod
    def place_order(self, symbol, order_type, quantity, price=0.0, trigger_price=0.0):
        pass

    @abc.abstractmethod
    def get_positions(self):
        pass

    @abc.abstractmethod
    def cancel_order(self, order_id):
        pass

# 1. Zerodha Kite Connect Adapter
class ZerodhaKiteBroker(BaseBroker):
    def __init__(self):
        self.api_key = ZERODHA_CONFIG.get("API_KEY")
        self.access_token = ZERODHA_CONFIG.get("ACCESS_TOKEN")
        self.kite = None
        self.authenticate()

    def authenticate(self):
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            logging.info("✅ Zerodha Kite Connect Authenticated Successfully.")
        except Exception as e:
            logging.error(f"❌ Zerodha Auth Failed: {str(e)}")

    def place_order(self, symbol, order_type, quantity, price=0.0, trigger_price=0.0):
        # Transaction Type: BUY / SELL
        transaction = self.kite.TRANSACTION_TYPE_BUY if order_type == "BUY" else self.kite.TRANSACTION_TYPE_SELL
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NFO if "CE" in symbol or "PE" in symbol else self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=transaction,
                quantity=quantity,
                product=self.kite.PRODUCT_MIS, # Intraday Option Buying
                order_type=self.kite.ORDER_TYPE_MARKET if price == 0 else self.kite.ORDER_TYPE_LIMIT,
                price=price
            )
            return {"status": "SUCCESS", "order_id": order_id}
        except Exception as e:
            return {"status": "FAILED", "reason": str(e)}

    def get_positions(self):
        return self.kite.positions() if self.kite else {}

    def cancel_order(self, order_id):
        return self.kite.cancel_order(variety=self.kite.VARIETY_REGULAR, order_id=order_id)

# 2. Dhan Broker Adapter
class DhanBroker(BaseBroker):
    def __init__(self):
        self.client_id = DHAN_CONFIG.get("CLIENT_ID")
        self.access_token = DHAN_CONFIG.get("ACCESS_TOKEN")
        self.dhan = None
        self.authenticate()

    def authenticate(self):
        try:
            from dhanhq import dhanhq
            self.dhan = dhanhq(self.client_id, self.access_token)
            logging.info("✅ Dhan API Authenticated Successfully.")
        except Exception as e:
            logging.error(f"❌ Dhan Auth Failed: {str(e)}")

    def place_order(self, symbol, order_type, quantity, price=0.0, trigger_price=0.0):
        try:
            response = self.dhan.place_order(
                security_id=symbol,
                exchange_segment=self.dhan.NSE_FNO,
                transaction_type=self.dhan.BUY if order_type == "BUY" else self.dhan.SELL,
                quantity=quantity,
                order_type=self.dhan.MARKET if price == 0 else self.dhan.LIMIT,
                product_type=self.dhan.INTRADAY,
                price=price
            )
            return response
        except Exception as e:
            return {"status": "FAILED", "reason": str(e)}

    def get_positions(self):
        return self.dhan.get_positions() if self.dhan else {}

    def cancel_order(self, order_id):
        return self.dhan.cancel_order(order_id)

# Broker Factory Switcher
def get_broker_instance(paper_mode=PAPER_TRADING_MODE, broker_type=ACTIVE_BROKER):
    if paper_mode:
        from paper_broker import PaperBroker
        return PaperBroker()
    elif broker_type == "ZERODHA":
        return ZerodhaKiteBroker()
    elif broker_type == "DHAN":
        return DhanBroker()
    else:
        raise ValueError(f"Unsupported Broker Type: {broker_type}")
