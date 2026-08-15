# paper_broker.py - Institutional Grade Defensive & Capital Protection Broker
import os
import csv
import json
import datetime

CSV_FILE = "trades.csv"
ACTIVE_JSON = "active_trade.json"
STATE_JSON = "live_state.json"

BROKERAGE_PER_TRADE = 45.0  # ₹45 Brokerage + STT + GST per trade

class PaperBroker:
    def __init__(self, initial_capital=100000):
        self.capital = initial_capital
        self.position = None
        self.daily_trades_count = 0
        self.daily_pnl = 0.0
        self.max_trades_per_day = 3
        self.max_daily_loss_limit = initial_capital * 0.02  # 2% Daily Loss Limit (₹2,000)
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

        # Persistent State Storage
        state_data = {
            "capital": self.capital,
            "daily_trades_count": self.daily_trades_count,
            "daily_pnl": self.daily_pnl,
            "position": self.position
        }
        with open(STATE_JSON, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)

    def _load_state(self):
        """கணினி ரீஸ்டார்ட் ஆனாலும் நினைவகத்தை மீட்டெடுக்கிறது"""
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
        # 1. Check Max Trades Per Day
        if self.daily_trades_count >= self.max_trades_per_day:
            print(f"\n[RISK GUARD] 🚫 Max Trades Limit ({self.max_trades_per_day}) reached for today. Trade Skipped.")
            return

        # 2. Check Hard Daily Loss Limit (2%)
        if self.daily_pnl <= -self.max_daily_loss_limit:
            print(f"\n[RISK GUARD] 🚨 Hard Daily Loss Limit (-2% / -₹{self.max_daily_loss_limit}) hit! Bot Kill-Switch Activated.")
            return

        if self.position is not None:
            return

        stop_loss = round(entry_price * (1 - stop_loss_pct), 2)
        target = round(entry_price * (1 + target_pct), 2)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        print(f"\n[{now_str}] 📥 [TRADE ENTERED] {symbol} ({option_type}) | Stock Entry: ₹{stock_price:.2f} | Trade #{self.daily_trades_count} Today")

    def update_market_price(self, current_price):
        if self.position is None:
            return

        entry = self.position["entry_price"]
        qty = self.position["qty"]
        now_time = datetime.datetime.now()
        now_str = now_time.strftime("%Y-%m-%d %H:%M:%S")

        # Trailing Stop Loss to Break-Even once 50% target (+15% gain) is reached
        half_target_price = entry * 1.15
        if current_price >= half_target_price and not self.position["trailed_to_breakeven"]:
            self.position["stop_loss"] = entry  # Trailed to Cost-to-Cost
            self.position["trailed_to_breakeven"] = True
            self._update_active_json()
            print(f"\n[{now_str}] 🛡️ [TRAILING SL] 50% Target Reached! Stop Loss Trailed to Break-Even (₹{entry:.2f} - 0% Risk).")

        # 1. Target Check
        if current_price >= self.position["target"]:
            gross_pnl = (current_price - entry) * qty
            net_pnl = gross_pnl - BROKERAGE_PER_TRADE
            self.capital += net_pnl
            self.daily_pnl += net_pnl
            print(f"[{now_str}] 🎯 [TARGET HIT] Exited at ₹{current_price:.2f} | Net PnL: ₹{net_pnl:.2f}")
            self._log_trade(current_price, "TARGET_HIT", gross_pnl, BROKERAGE_PER_TRADE, net_pnl, now_str)
            self._clear_active_json()

        # 2. Stop Loss Check
        elif current_price <= self.position["stop_loss"]:
            gross_pnl = (current_price - entry) * qty
            net_pnl = gross_pnl - BROKERAGE_PER_TRADE
            self.capital += net_pnl
            self.daily_pnl += net_pnl
            reason = "BREAKEVEN_EXIT" if self.position["trailed_to_breakeven"] else "STOP_LOSS_HIT"
            print(f"[{now_str}] ❌ [{reason}] Exited at ₹{current_price:.2f} | Net PnL: ₹{net_pnl:.2f}")
            self._log_trade(current_price, reason, gross_pnl, BROKERAGE_PER_TRADE, net_pnl, now_str)
            self._clear_active_json()

        # 3. Market Close (3:15 PM) Auto Square-Off Check
        elif now_time.time() >= datetime.time(15, 15):
            gross_pnl = (current_price - entry) * qty
            net_pnl = gross_pnl - BROKERAGE_PER_TRADE
            self.capital += net_pnl
            self.daily_pnl += net_pnl
            print(f"[{now_str}] 🔔 [3:15 PM MARKET CLOSE SQUARE-OFF] Exited at ₹{current_price:.2f} | Net PnL: ₹{net_pnl:.2f}")
            self._log_trade(current_price, "3:15_PM_MARKET_CLOSE", gross_pnl, BROKERAGE_PER_TRADE, net_pnl, now_str)
            self._clear_active_json()

    def _log_trade(self, exit_price, reason, gross_pnl, brokerage, net_pnl, exit_time_str):
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
        print(f"✅ [SAVED] டிரேட் விவரங்கள் 'trades.csv' கோப்பில் சேமிக்கப்பட்டது.\n")