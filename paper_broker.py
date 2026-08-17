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

def get_official_nse_lot_size(symbol: str) -> int:
    """Returns official NSE Exchange Lot Size for Options"""
    sym = str(symbol).upper()
    if "NIFTY" in sym and "BANK" not in sym:
        return 25  # Nifty 50 Lot Size
    elif "BANKNIFTY" in sym:
        return 15  # BankNifty Lot Size
    elif "RELIANCE" in sym:
        return 250 # Reliance Stock Option Lot Size
    elif "HDFCBANK" in sym:
        return 550 # HDFC Bank Option Lot Size
    elif "ICICIBANK" in sym:
        return 700 # ICICI Bank Option Lot Size
    elif "INFY" in sym:
        return 400 # Infosys Option Lot Size
    elif "SBIN" in sym:
        return 750 # SBI Option Lot Size
    return 15      # Crypto / Default Lot Size

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

def get_current_ist_timestamp_str() -> str:
    """Returns clean formatted Indian Standard Time (IST) String"""
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    return ist_now.strftime('%d-%b-%Y %I:%M:%S %p IST')

def execute_paper_trade_entry(symbol: str, option_type: str, entry_price: float, qty: int, target_price: float, sl_price: float):
    """Executes Paper Entry, Logs IST Time, and Triggers Immediate Telegram Entry Alert"""
    ist_time_str = get_current_ist_timestamp_str()
    
    trade_record = {
        "Entry_Time": ist_time_str,
        "Symbol": symbol,
        "Option_Type": option_type,
        "Entry_Price": round(entry_price, 2),
        "Quantity": qty,
        "Target": round(target_price, 2),
        "Stop_Loss": round(sl_price, 2),
        "status": "ACTIVE"
    }
    
    # 🔔 TRIGGER IMMEDIATE TELEGRAM ENTRY ALERT!
    is_crypto = any(k in symbol.upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    curr = "$" if is_crypto else "₹"
    
    entry_msg = f"""🚀 <b>NEW ACTIVE TRADE ENTERED!</b>

📌 <b>Asset Symbol:</b> {symbol} ({option_type})
💵 <b>Entry Premium:</b> {curr}{entry_price:,.2f}
🎯 <b>Target Price:</b> {curr}{target_price:,.2f}
🛑 <b>Stop Loss:</b> {curr}{sl_price:,.2f}
⏰ <b>Entry Time:</b> {ist_time_str}
"""
    send_telegram_alert(entry_msg)
    
    return trade_record

def execute_paper_trade_exit(trade_record: dict, exit_price: float, exit_reason: str):
    """Executes Paper Exit, Logs IST Exit Time, and Triggers Telegram Exit Alert"""
    ist_exit_time_str = get_current_ist_timestamp_str()
    
    trade_record['Exit_Time'] = ist_exit_time_str
    trade_record['Exit_Price'] = round(exit_price, 2)
    trade_record['Exit_Reason'] = exit_reason
    trade_record['status'] = "CLOSED"
    
    # Calculate PnL & Friction
    symbol = trade_record.get('Symbol', '')
    is_crypto = any(k in symbol.upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    curr = "$" if is_crypto else "₹"
    
    entry_p = float(trade_record.get('Entry_Price', 0.0))
    q = int(trade_record.get('Quantity', 1))
    gross_pnl = (exit_price - entry_p) * q
    fees = round(abs(gross_pnl * 0.001) + 0.65, 2) if is_crypto else 48.00
    net_pnl = round(gross_pnl - fees, 2)
    
    trade_record['Gross_PnL'] = f"{curr}{gross_pnl:+,.2f}"
    trade_record['Brokerage_&_Taxes'] = f"-{curr}{fees:,.2f}"
    trade_record['Net_PnL'] = f"{curr}{net_pnl:+,.2f}"
    
    # 🔔 TRIGGER TELEGRAM EXIT ALERT
    exit_msg = f"""🏁 <b>TRADE COMPLETED & LOGGED!</b>

📌 <b>Asset Symbol:</b> {symbol}
🔚 <b>Exit Reason:</b> {exit_reason}
💵 <b>Entry Price:</b> {curr}{entry_p:,.2f} ➔ <b>Exit Price:</b> {curr}{exit_price:,.2f}
📊 <b>Net Realized P&L:</b> {curr}{net_pnl:+,.2f}
⏰ <b>Exit Time:</b> {ist_exit_time_str}
"""
    send_telegram_alert(exit_msg)
    
    return trade_record

def execute_paper_exit(trade_record, exit_price, exit_reason):
    return execute_paper_trade_exit(trade_record, exit_price, exit_reason)

def evaluate_realtime_intra_candle_risk(trade_record: dict, current_price: float) -> dict:
    """Evaluates Risk Every 1-Second Tick and Cuts Loss INSTANTLY at -$25.00 Mid-Candle"""
    entry_price = float(trade_record.get('Entry_Price') or trade_record.get('entry_price', 0.0))
    qty = int(trade_record.get('Quantity') or trade_record.get('qty', 1))
    symbol = trade_record.get('Symbol') or trade_record.get('symbol', '')
    
    is_crypto = any(k in str(symbol).upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    
    current_pnl = (current_price - entry_price) * qty
    
    # HARD INTRA-CANDLE CUT LOSS (Does NOT wait for 5-min candle close!)
    max_loss_limit = -25.00 if is_crypto else -180.00 # -$25 for Crypto, -₹180 for NSE
    
    if current_pnl <= max_loss_limit:
        return {
            "should_exit": True, 
            "reason": f"🚨 INTRA-CANDLE HARD CUT LOSS TRIGGERED ({current_pnl:.2f})", 
            "exit_price": current_price
        }
        
    return {"should_exit": False, "reason": "HOLDING"}

def enforce_strict_risk_reward_exit(trade_record: dict, current_price: float) -> dict:
    """Enforces Max Loss Cap at -$25.00 and Allows Target Gains up to +$50 / +$100"""
    entry_price = float(trade_record['Entry_Price'])
    qty = int(trade_record['Quantity'])
    symbol = trade_record['Symbol']
    
    is_crypto = any(k in symbol.upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    
    current_pnl = (current_price - entry_price) * qty
    
    if is_crypto:
        # STRICT CRYPTO CAP: Max Loss = -$25.00
        if current_pnl <= -25.00:
            return {"should_exit": True, "reason": "🛑 STRICT MAX LOSS CAP (-$25.00 Hit)", "exit_price": current_price}
            
        # TARGET 1: +$50.00 (+6% Gain)
        if current_pnl >= 50.00 and not trade_record.get('t1_hit', False):
            trade_record['t1_hit'] = True
            return {"should_exit": False, "action": "PARTIAL_PROFIT_BOOKING", "reason": "🎯 TARGET 1 HIT (+$50.00 Gain)"}

        # TARGET 2: +$100.00 (+12% Gain)
        if current_pnl >= 100.00:
            return {"should_exit": True, "reason": "🎯 TARGET 2 FULL EXIT (+$100.00 Gain)", "exit_price": current_price}

    return {"should_exit": False, "reason": "HOLDING"}

def apply_multi_asset_trailing_lock(trade_record: dict, current_price: float) -> dict:
    entry_price = float(trade_record['Entry_Price'])
    qty = int(trade_record['Quantity'])
    symbol = trade_record['Symbol']
    
    current_pnl = (current_price - entry_price) * qty
    is_crypto = any(k in symbol.upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])

    if is_crypto:
        # CRYPTO DOLLAR RULES ($)
        trigger_pnl = 35.00   # +$35.00 Gain Trigger
        lock_pnl = 15.00      # Lock +$15.00
        max_sl = -25.00       # Max Loss Cap -$25.00
    else:
        # NSE RUPEES RULES (₹)
        trigger_pnl = 250.00  # +₹250.00 Gain Trigger
        lock_pnl = 100.00     # Lock +₹100.00 (Covers ₹52 Brokerage)
        max_sl = -180.00      # Max Loss Cap -₹180.00

    # Max Loss Cut
    if current_pnl <= max_sl:
        return {"should_exit": True, "reason": "🛑 STRICT MAX LOSS CAP HIT", "exit_price": current_price}

    # Dynamic Profit Lock Trigger
    max_pnl = max(trade_record.get('max_pnl_seen', 0.0), current_pnl)
    trade_record['max_pnl_seen'] = max_pnl

    if max_pnl >= trigger_pnl:
        if current_pnl <= (max_pnl - lock_pnl):
            return {"should_exit": True, "reason": "🔒 DYNAMIC TRAILING PROFIT LOCK TRIGGERED", "exit_price": current_price}

    return {"should_exit": False, "reason": "HOLDING"}



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

    def buy_option(self, symbol, option_type, entry_price, stock_price=0.0, qty=None, stop_loss_pct=0.15, target_pct=0.30):
        if qty is None:
            qty = get_official_nse_lot_size(symbol)

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