# paper_broker.py - Institutional Paper Broker with SEBI Order Slicing & VIX Protection
import os
import csv
import json
import datetime
from notifier import send_telegram_alert
from config import SEBI_FREEZE_LIMITS

CSV_FILE = "trades.csv"
ACTIVE_JSON = "active_trade.json"
STATE_JSON = "live_state.json"
BROKERAGE_PER_TRADE = 45.0

def slice_order_quantity(symbol, total_qty):
    """SEBI Order Slicing Engine: Splits large parent orders into compliant child slices"""
    asset_key = "BANKNIFTY" if "BANK" in symbol else ("NIFTY50" if "NIFTY" in symbol else "DEFAULT")
    max_cap = SEBI_FREEZE_LIMITS.get(asset_key, 1800)
    
    if total_qty <= max_cap:
        return [total_qty]
    
    slices = []
    remaining = total_qty
    while remaining > 0:
        chunk = min(remaining, max_cap)
        slices.append(chunk)
        remaining -= chunk
    return slices

def execute_paper_exit(trade_record, exit_price, exit_reason):
    symbol = trade_record['Symbol']
    entry_price = trade_record['Entry_Price']
    qty = trade_record['Quantity']
    
    # 1. Gross P&L Calculation (Before Fees)
    gross_pnl = (exit_price - entry_price) * qty
    
    # 2. Calculate Exact Deducted Charges (Brokerage + STT + GST)
    if any(crypto in symbol.upper() for crypto in ["BITCOIN", "ETHEREUM", "BTC", "ETH"]):
        deducted_charges = round(gross_pnl * 0.001 + 0.65, 2) # Crypto Exchange Fee ($)
        currency = "$"
    else:
        # NSE Options: ₹40 Flat Brokerage + 0.15% STT + GST
        stt_gst = (exit_price * qty * 0.0015) + 7.50
        deducted_charges = round(40.00 + stt_gst, 2) # NSE Friction Charges (₹)
        currency = "₹"
        
    # 3. Net P&L (Gross P&L minus Deducted Charges)
    net_pnl = round(gross_pnl - deducted_charges, 2)
    
    trade_record['Gross_PnL'] = f"{currency}{gross_pnl:+,.2f}"
    trade_record['Brokerage_&_Taxes'] = f"-{currency}{deducted_charges:,.2f}"
    trade_record['Net_PnL'] = f"{currency}{net_pnl:+,.2f}"
    
    return trade_record



class PaperBroker:
    def __init__(self, initial_capital=100000):
        self.capital = initial_capital
        self.position = None
        self.daily_trades_count = 0
        self.daily_pnl = 0.0
        self.max_trades_per_day = 3
        self.max_daily_loss_limit = initial_capital * 0.02
        self._init_csv()
        self._load_state()

    def _init_csv(self):
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Entry_Time", "Exit_Time", "Symbol", "Option_Type", 
                    "Entry_Price", "Exit_Price", "Stop_Loss", "Target", 
                    "Quantity", "Exit_Reason", "Gross_PnL", "Brokerage_Taxes", "Net_PnL", "Capital_Balance"
                ])

    def _update_active_json(self):
        if self.position:
            data = self.position
            data["status"] = "ACTIVE"
        else:
            data = {"status": "NO_POSITION"}
            
        with open(ACTIVE_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        state_data = {
            "capital": self.capital,
            "daily_trades_count": self.daily_trades_count,
            "daily_pnl": self.daily_pnl,
            "position": self.position
        }
        with open(STATE_JSON, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)

    def _load_state(self):
        if os.path.exists(STATE_JSON):
            try:
                with open(STATE_JSON, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.capital = state.get("capital", 100000)
                    self.daily_trades_count = state.get("daily_trades_count", 0)
                    self.daily_pnl = state.get("daily_pnl", 0.0)
                    self.position = state.get("position", None)
            except:
                pass

    def _clear_active_json(self):
        self.position = None
        with open(ACTIVE_JSON, "w", encoding="utf-8") as f:
            json.dump({"status": "NO_POSITION"}, f, indent=4)
        self._update_active_json()

    def buy_option(self, symbol, option_type, entry_price, stock_price=0.0, qty=15, stop_loss_pct=0.15, target_pct=0.30):
        if self.daily_trades_count >= self.max_trades_per_day:
            print(f"\n[RISK GUARD] 🚫 Max Trades Limit ({self.max_trades_per_day}) reached for today.")
            return

        if self.daily_pnl <= -self.max_daily_loss_limit:
            print(f"\n[RISK GUARD] 🚨 Hard Daily Loss Limit (-2%) hit! Bot Kill-Switch Activated.")
            return

        if self.position is not None:
            return

        # SEBI Slicing Validation
        child_slices = slice_order_quantity(symbol, qty)
        
        stop_loss = round(entry_price * (1 - stop_loss_pct), 2)
        target = round(entry_price * (1 + target_pct), 2)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        p_curr = "$" if "USD" in symbol or "BTC" in symbol or "ETH" in symbol else "₹"

        if option_type == "CALL":
            target_stock_price = round(stock_price + (entry_price * target_pct / 0.5), 2)
            sl_stock_price = round(stock_price - (entry_price * stop_loss_pct / 0.5), 2)
        else:
            target_stock_price = round(stock_price - (entry_price * target_pct / 0.5), 2)
            sl_stock_price = round(stock_price + (entry_price * stop_loss_pct / 0.5), 2)

        self.position = {
            "entry_time": now_str,
            "symbol": symbol,
            "type": option_type,
            "entry_price": round(entry_price, 2),
            "entry_stock_price": round(stock_price, 2),
            "target_stock_price": target_stock_price,
            "sl_stock_price": sl_stock_price,
            "qty": qty,
            "slices": child_slices,
            "stop_loss": stop_loss,
            "initial_stop_loss": stop_loss,
            "target": target,
            "max_premium_seen": entry_price,
            "trailed_to_breakeven": False
        }
        self.daily_trades_count += 1
        self._update_active_json()
        
        telegram_msg = (
            f"🚨 <b>ALGO TRADE ENTERED!</b>\n\n"
            f"<b>Symbol:</b> {symbol} ({option_type})\n"
            f"<b>Stock Price:</b> {p_curr}{stock_price:,.2f}\n"
            f"<b>Option Premium:</b> {p_curr}{entry_price:.2f}\n"
            f"<b>Quantity:</b> {qty} (SEBI Slices: {len(child_slices)})\n"
            f"<b>Stop Loss:</b> {p_curr}{stop_loss:.2f} (-15%)\n"
            f"<b>Target:</b> {p_curr}{target:.2f} (+30%)\n"
            f"<b>Time:</b> {now_str}"
        )
        send_telegram_alert(telegram_msg)
        print(f"\n[{now_str}] 📥 [TRADE ENTERED] {symbol} ({option_type}) | Stock Entry: {p_curr}{stock_price:.2f}")

    def update_market_price(self, current_price):
        if self.position is None:
            return

        entry = self.position["entry_price"]
        qty = self.position["qty"]
        now_time = datetime.datetime.now()
        now_str = now_time.strftime("%Y-%m-%d %H:%M:%S")

        # Track Max Premium Seen
        max_seen = self.position.get("max_premium_seen", entry)
        if current_price > max_seen:
            self.position["max_premium_seen"] = current_price

        # Trailing Stop Loss & Profit Lock (+4% Profit Locks to Break-Even)
        if current_price >= (entry * 1.04):
            trailed_sl = max(entry, round(self.position["max_premium_seen"] * 0.96, 2))
            if trailed_sl > self.position["stop_loss"]:
                self.position["stop_loss"] = trailed_sl
                self.position["trailed_to_breakeven"] = True
                self._update_active_json()

        # Determine trigger exit
        trigger_exit = False
        reason = ""
        if current_price >= self.position["target"]:
            trigger_exit = True
            reason = "TARGET_HIT"
        elif current_price <= self.position["stop_loss"]:
            trigger_exit = True
            reason = "BREAKEVEN_EXIT" if self.position["trailed_to_breakeven"] else "STOP_LOSS_HIT"
        elif now_time.time() >= datetime.time(15, 15) and "USD" not in self.position["symbol"]:
            trigger_exit = True
            reason = "3:15_PM_MARKET_CLOSE"

        if trigger_exit:
            temp_record = {
                'Symbol': self.position['symbol'],
                'Entry_Price': self.position['entry_price'],
                'Quantity': self.position['qty']
            }
            res_record = execute_paper_exit(temp_record, current_price, reason)
            
            # Extract float values for calculations
            gross_pnl = (current_price - entry) * qty
            symbol = self.position['symbol']
            if any(crypto in symbol.upper() for crypto in ["BITCOIN", "ETHEREUM", "BTC", "ETH"]):
                deducted_charges = round(gross_pnl * 0.001 + 0.65, 2)
            else:
                stt_gst = (current_price * qty * 0.0015) + 7.50
                deducted_charges = round(40.00 + stt_gst, 2)
            net_pnl = round(gross_pnl - deducted_charges, 2)

            self.capital += net_pnl
            self.daily_pnl += net_pnl

            # Log to CSV using res_record strings
            self._log_trade(
                current_price, 
                reason, 
                res_record['Gross_PnL'], 
                res_record['Brokerage_&_Taxes'], 
                res_record['Net_PnL'], 
                now_str
            )
            self._clear_active_json()

    def _log_trade(self, exit_price, reason, gross_pnl_str, brokerage_str, net_pnl_str, exit_time_str):
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                self.position["entry_time"],
                exit_time_str,
                self.position["symbol"],
                self.position["type"],
                f"{self.position['entry_price']:.2f}",
                f"{exit_price:.2f}",
                f"{self.position['stop_loss']:.2f}",
                f"{self.position['target']:.2f}",
                self.position["qty"],
                reason,
                gross_pnl_str,
                brokerage_str,
                net_pnl_str,
                f"{self.capital:.2f}"
            ])

        p_curr = "$" if "USD" in self.position["symbol"] or "BTC" in self.position["symbol"] or "ETH" in self.position["symbol"] else "₹"
        exit_msg = (
            f"🏁 <b>TRADE COMPLETED & LOGGED!</b>\n\n"
            f"<b>Symbol:</b> {self.position['symbol']} ({self.position['type']})\n"
            f"<b>Exit Reason:</b> {reason}\n"
            f"<b>Entry Price:</b> {p_curr}{self.position['entry_price']:.2f}\n"
            f"<b>Exit Price:</b> {p_curr}{exit_price:.2f}\n"
            f"<b>Gross P&L:</b> {gross_pnl_str}\n"
            f"<b>Brokerage & Taxes:</b> {brokerage_str}\n"
            f"<b>Net Realized P&L:</b> {net_pnl_str}\n"
            f"<b>Account Capital:</b> {p_curr}{self.capital:,.2f}"
        )
        send_telegram_alert(exit_msg)
        print(f"✅ [SAVED & NOTIFIED] டிரேட் விவரங்கள் 'trades.csv' கோப்பில் சேமிக்கப்பட்டு Telegram-க்கும் அனுப்பப்பட்டது.\n")