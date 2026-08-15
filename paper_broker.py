# paper_broker.py - Full Telegram Mobile Alerts Integration
import os
import csv
import json
import datetime
from notifier import send_telegram_alert

CSV_FILE = "trades.csv"
ACTIVE_JSON = "active_trade.json"
STATE_JSON = "live_state.json"

BROKERAGE_PER_TRADE = 45.0

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
            "stop_loss": stop_loss,
            "initial_stop_loss": stop_loss,
            "target": target,
            "trailed_to_breakeven": False
        }
        self.daily_trades_count += 1
        self._update_active_json()
        
        # 🚨 TELEGRAM INSTANT TRADE ENTRY ALERT
        telegram_msg = (
            f"🚨 <b>ALGO TRADE ENTERED!</b>\n\n"
            f"<b>Symbol:</b> {symbol} ({option_type})\n"
            f"<b>Stock Price:</b> {p_curr}{stock_price:,.2f}\n"
            f"<b>Option Premium:</b> {p_curr}{entry_price:.2f}\n"
            f"<b>Quantity:</b> {qty}\n"
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

        p_curr = "$" if "USD" in self.position["symbol"] or "BTC" in self.position["symbol"] else "₹"

        # Trailing Stop Loss to Break-Even
        half_target_price = entry * 1.15
        if current_price >= half_target_price and not self.position["trailed_to_breakeven"]:
            self.position["stop_loss"] = entry
            self.position["trailed_to_breakeven"] = True
            self._update_active_json()
            
            # 🛡️ TELEGRAM TRAILING SL ALERT
            trail_msg = (
                f"🛡️ <b>TRAILING SL TO BREAK-EVEN!</b>\n\n"
                f"<b>Symbol:</b> {self.position['symbol']}\n"
                f"<b>Reason:</b> 50% Target Reached (+15% Gain)\n"
                f"<b>New Stop Loss:</b> {p_curr}{entry:.2f} (0% Risk Locked)"
            )
            send_telegram_alert(trail_msg)

        # 1. Target Check
        if current_price >= self.position["target"]:
            gross_pnl = (current_price - entry) * qty
            net_pnl = gross_pnl - BROKERAGE_PER_TRADE
            self.capital += net_pnl
            self.daily_pnl += net_pnl
            self._log_trade(current_price, "TARGET_HIT", gross_pnl, BROKERAGE_PER_TRADE, net_pnl, now_str)
            self._clear_active_json()

        # 2. Stop Loss Check
        elif current_price <= self.position["stop_loss"]:
            gross_pnl = (current_price - entry) * qty
            net_pnl = gross_pnl - BROKERAGE_PER_TRADE
            self.capital += net_pnl
            self.daily_pnl += net_pnl
            reason = "BREAKEVEN_EXIT" if self.position["trailed_to_breakeven"] else "STOP_LOSS_HIT"
            self._log_trade(current_price, reason, gross_pnl, BROKERAGE_PER_TRADE, net_pnl, now_str)
            self._clear_active_json()

        # 3. Market Close (3:15 PM) Auto Square-Off Check
        elif now_time.time() >= datetime.time(15, 15) and "USD" not in self.position["symbol"]:
            gross_pnl = (current_price - entry) * qty
            net_pnl = gross_pnl - BROKERAGE_PER_TRADE
            self.capital += net_pnl
            self.daily_pnl += net_pnl
            self._log_trade(current_price, "3:15_PM_MARKET_CLOSE", gross_pnl, BROKERAGE_PER_TRADE, net_pnl, now_str)
            self._clear_active_json()

    def _log_trade(self, exit_price, reason, gross_pnl, brokerage, net_pnl, exit_time_str):
        p_curr = "$" if "USD" in self.position["symbol"] or "BTC" in self.position["symbol"] else "₹"
        
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
                f"{gross_pnl:.2f}",
                f"{brokerage:.2f}",
                f"{net_pnl:.2f}",
                f"{self.capital:.2f}"
            ])

        # 🏁 TELEGRAM TRADE EXIT ALERT
        exit_msg = (
            f"🏁 <b>TRADE COMPLETED & LOGGED!</b>\n\n"
            f"<b>Symbol:</b> {self.position['symbol']} ({self.position['type']})\n"
            f"<b>Exit Reason:</b> {reason}\n"
            f"<b>Entry Premium:</b> {p_curr}{self.position['entry_price']:.2f}\n"
            f"<b>Exit Premium:</b> {p_curr}{exit_price:.2f}\n"
            f"<b>Net P&L:</b> {p_curr}{net_pnl:+.2f}\n"
            f"<b>Account Capital:</b> {p_curr}{self.capital:,.2f}"
        )
        send_telegram_alert(exit_msg)
        print(f"✅ [SAVED & NOTIFIED] டிரேட் விவரங்கள் 'trades.csv' கோப்பில் சேமிக்கப்பட்டு Telegram-க்கும் அனுப்பப்பட்டது.\n")