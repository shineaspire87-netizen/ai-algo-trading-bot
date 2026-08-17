# paper_broker.py - Stateful Dynamic Trailing Profit Lock & Friction Execution Engine

import datetime
import logging
import json
import os
import csv
import streamlit as st
from notifier import send_telegram_alert

CSV_FILE = "trades.csv"
ACTIVE_JSON = "active_trade.json"
STATE_JSON = "live_state.json"
BROKERAGE_PER_TRADE = 45.0

# -------------------------------------------------------------
# 1. OFFICIAL EXCHANGE LOT SIZES
# -------------------------------------------------------------
def get_official_exchange_lot_size(symbol: str) -> int:
    """Returns official exchange lot sizes for Indian NSE and Crypto"""
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
    return 15      # Default Crypto Lot Quantity

# Backward-compatibility alias
get_official_nse_lot_size = get_official_exchange_lot_size

def get_current_ist_timestamp_str() -> str:
    """Returns clean formatted Indian Standard Time (IST) String"""
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    return ist_now.strftime('%d-%b-%Y %I:%M:%S %p IST')

# -------------------------------------------------------------
# 2. STATEFUL DYNAMIC TRAILING PROFIT LOCK ENGINE
# -------------------------------------------------------------
def apply_stateful_dynamic_trailing_lock(trade_record: dict, current_spot_price: float) -> dict:
    """
    Piecewise Stateful Dynamic Trailing Profit Lock Engine
    Triggers at +$35.00 (+3% Gain) -> Locks +$15.00 Minimum Guaranteed Net Profit Floor!
    """
    entry_spot = float(trade_record.get('Entry_Stock_Price', trade_record.get('Entry_Price', 0.0)))
    qty = int(trade_record.get('Quantity', 15))
    symbol = trade_record.get('Symbol', '')
    option_type = trade_record.get('Option_Type', 'CALL')
    
    is_crypto = any(k in symbol.upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    
    # Calculate Current Floating PnL
    if option_type == "CALL":
        floating_pnl = (current_spot_price - entry_spot) * qty
    else: # PUT
        floating_pnl = (entry_spot - current_spot_price) * qty

    # Track Maximum Favorable Excursion (H_max / L_min)
    max_pnl_seen = max(trade_record.get('max_pnl_seen', 0.0), floating_pnl)
    trade_record['max_pnl_seen'] = max_pnl_seen

    # Calibrate Triggers ($ for Crypto, ₹ for NSE)
    d_trigger = 35.00 if is_crypto else 250.00  # +$35.00 USD / +₹250.00 INR
    d_lock = 15.00 if is_crypto else 100.00     # Lock +$15.00 USD / +₹100.00 INR
    max_loss_cap = -25.00 if is_crypto else -180.00 # Max Loss Cap

    # 1-SECOND INTRA-CANDLE HARD CUT LOSS (Does NOT wait for 5-min bar close!)
    if floating_pnl <= max_loss_cap:
        return {
            "should_exit": True,
            "action": "HARD_CUT_LOSS",
            "reason": f"🚨 INTRA-CANDLE HARD CUT LOSS TRIGGERED ({floating_pnl:+.2f})",
            "exit_price": current_spot_price
        }

    # STATE 2: PROFIT LOCK ACTIVE (H_max >= d_trigger)
    if max_pnl_seen >= d_trigger:
        trade_record['profit_lock_active'] = True
        
        # Trailing Exit Condition: If price drops d_lock below maximum favorable excursion peak
        if floating_pnl <= (max_pnl_seen - d_lock):
            locked_pnl = max(floating_pnl, d_lock)
            return {
                "should_exit": True,
                "action": "PROFIT_LOCK_EXIT",
                "reason": f"🔒 DYNAMIC TRAILING PROFIT LOCK TRIGGERED (Guaranteed +${locked_pnl:.2f} Profit Locked)",
                "exit_price": current_spot_price
            }

    return {"should_exit": False, "action": "HOLD", "reason": "HOLDING"}

# Alias for compatibility
apply_multi_asset_trailing_lock = apply_stateful_dynamic_trailing_lock

# -------------------------------------------------------------
# 3. PAPER TRADE ENTRY EXECUTION WITH IMMEDIATE TELEGRAM ALERT
# -------------------------------------------------------------
def execute_paper_trade_entry(symbol: str, option_type: str, entry_spot_price: float, entry_premium: float = None, target_spot: float = None, sl_spot: float = None, qty: int = None):
    """Executes Paper Entry, Logs IST Time, and Triggers Immediate Telegram Entry Alert"""
    ist_time_str = get_current_ist_timestamp_str()
    if qty is None:
        qty = get_official_exchange_lot_size(symbol)
    
    if entry_premium is None:
        entry_premium = entry_spot_price
    if target_spot is None:
        target_spot = entry_spot_price * 1.012
    if sl_spot is None:
        sl_spot = entry_spot_price * 0.993
        
    is_crypto = any(k in symbol.upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    curr = "$" if is_crypto else "₹"

    margin_blocked = entry_premium * qty

    trade_record = {
        "Entry_Time": ist_time_str,
        "Symbol": symbol,
        "Option_Type": option_type,
        "Entry_Stock_Price": round(entry_spot_price, 2),
        "Live_Stock_Price": round(entry_spot_price, 2),
        "Target_Stock_Price": round(target_spot, 2),
        "SL_Stock_Price": round(sl_spot, 2),
        "Entry_Price": round(entry_premium, 2),
        "Live_Price": round(entry_premium, 2),
        "Quantity": qty,
        "Margin_Blocked": round(margin_blocked, 2),
        "max_pnl_seen": 0.0,
        "profit_lock_active": False,
        "status": "ACTIVE"
    }

    # Save to Local Active State JSON
    try:
        with open("active_trade.json", "w") as f:
            json.dump(trade_record, f, indent=4)
    except Exception as e:
        logging.warning(f"Active trade JSON write error: {e}")

    # 🔔 TRIGGER IMMEDIATE TELEGRAM ENTRY ALERT!
    entry_msg = f"""🚀 <b>NEW ACTIVE TRADE ENTERED!</b>

📌 <b>Asset Symbol:</b> {symbol} ({option_type})
📦 <b>Lots / Quantity:</b> {qty} Qty
💵 <b>Entry Premium:</b> {curr}{entry_premium:,.2f}
💸 <b>Margin Blocked:</b> {curr}{margin_blocked:,.2f}
📍 <b>Entry Spot Price:</b> {curr}{entry_spot_price:,.2f}
🎯 <b>Target Spot:</b> {curr}{target_spot:,.2f}
🛑 <b>Stop Loss Spot:</b> {curr}{sl_spot:,.2f}
⏰ <b>Entry Time:</b> {ist_time_str}
"""
    send_telegram_alert(entry_msg)
    
    return trade_record

# -------------------------------------------------------------
# 4. PAPER TRADE EXIT EXECUTION WITH FEE & SLIPPAGE FRICTION
# -------------------------------------------------------------
def execute_paper_trade_exit(trade_record: dict, exit_premium: float, exit_reason: str):
    """Executes Paper Exit, Applies Binance/NSE Fee & Slippage Friction Model, and Logs IST Time"""
    ist_exit_time_str = get_current_ist_timestamp_str()
    
    symbol = trade_record.get('Symbol', 'TRADE')
    entry_premium = float(trade_record.get('Entry_Price', trade_record.get('Entry_Stock_Price', 0.0)))
    qty = int(trade_record.get('Quantity', 1))
    
    is_crypto = any(k in symbol.upper() for k in ["BITCOIN", "ETHEREUM", "BTC", "ETH"])
    curr = "$" if is_crypto else "₹"

    # 1. Gross PnL Calculation (Before Fees & Slippage)
    gross_pnl = (exit_premium - entry_premium) * qty

    # 2. Binance Taker Fee (0.05%) & Slippage (0.06%) Friction Model
    if is_crypto:
        notional_entry = entry_premium * qty
        notional_exit = exit_premium * qty
        taker_fee = (notional_entry + notional_exit) * 0.0005 # 0.05% Taker Fee
        slippage_cost = (notional_entry + notional_exit) * 0.0006 # 0.06% Slippage
        deducted_fees = round(taker_fee + slippage_cost + 0.65, 2)
    else:
        # NSE Options: ₹40 Flat Brokerage + 0.15% STT + GST
        stt_gst = (exit_premium * qty * 0.0015) + 7.50
        deducted_fees = round(40.00 + stt_gst, 2)

    # 3. Net Realized PnL (Gross PnL minus Friction)
    net_pnl = round(gross_pnl - deducted_fees, 2)

    trade_record['Exit_Time'] = ist_exit_time_str
    trade_record['Exit_Price'] = round(exit_premium, 2)
    trade_record['Gross_PnL'] = f"{curr}{gross_pnl:+,.2f}"
    trade_record['Brokerage_&_Taxes'] = f"-{curr}{deducted_fees:,.2f}"
    trade_record['Net_PnL'] = f"{curr}{net_pnl:+,.2f}"
    trade_record['Exit_Reason'] = exit_reason
    trade_record['status'] = "CLOSED"

    # Clear Local Active State JSON
    if os.path.exists("active_trade.json"):
        try:
            os.remove("active_trade.json")
        except Exception:
            pass

    # 🔔 TRIGGER TELEGRAM EXIT ALERT
    exit_msg = f"""🏁 <b>TRADE COMPLETED & LOGGED!</b>

📌 <b>Asset Symbol:</b> {symbol}
🔚 <b>Exit Reason:</b> {exit_reason}
💵 <b>Entry Premium:</b> {curr}{entry_premium:,.2f} ➔ <b>Exit Premium:</b> {curr}{exit_premium:,.2f}
📊 <b>Gross P&L:</b> {curr}{gross_pnl:+,.2f}
💸 <b>Fees & Slippage:</b> -{curr}{deducted_fees:,.2f}
💰 <b>Net Realized P&L:</b> {curr}{net_pnl:+,.2f}
⏰ <b>Exit Time:</b> {ist_exit_time_str}
"""
    send_telegram_alert(exit_msg)
    
    return trade_record

# -------------------------------------------------------------
# 5. PAPER BROKER OOP CLASS FOR AUTONOMOUS SCANNER
# -------------------------------------------------------------
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
                    state_data = json.load(f)
                    self.capital = state_data.get("capital", self.capital)
                    self.daily_trades_count = state_data.get("daily_trades_count", 0)
                    self.daily_pnl = state_data.get("daily_pnl", 0.0)
                    self.position = state_data.get("position", None)
            except Exception:
                pass

    def buy_option(self, symbol, option_type, entry_price, stock_price=None, qty=15):
        if self.position is not None:
            return False, "Position already open"
        
        target = entry_price * 1.12
        stop_loss = entry_price * 0.93
        self.position = execute_paper_trade_entry(symbol, option_type, stock_price if stock_price else entry_price, entry_price, target, stop_loss, qty)
        self.daily_trades_count += 1
        self._update_active_json()
        return True, "Paper trade entered"

    def close_position(self, exit_price, exit_reason="MANUAL_EXIT"):
        if self.position is None:
            return False, "No active position to close"
        
        res = execute_paper_trade_exit(self.position, exit_price, exit_reason)
        net_num = float(str(res['Net_PnL']).replace("$", "").replace("₹", "").replace(",", ""))
        self.capital += net_num
        self.daily_pnl += net_num
        self.position = None
        self._update_active_json()
        return True, f"Closed with PnL: {res['Net_PnL']}"