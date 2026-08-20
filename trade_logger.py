# ================================================================================
# ANTONY QUANT AI TERMINAL - TRADE LOGGER & PERSISTENCE ENGINE
# ================================================================================
import json
import os
from datetime import datetime, timezone, timedelta

TRADES_FILE = "trades.json"
STATE_FILE = "live_state.json"

def get_ist_now():
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=5, minutes=30)

def load_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    try:
        with open(TRADES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_trades(trades):
    with open(TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=4)

def delete_trade_by_id(trade_id):
    """Deletes a specific trade record by unique trade_id."""
    trades = load_trades()
    updated_trades = [t for t in trades if t.get("trade_id") != trade_id]
    save_trades(updated_trades)

def clear_all_trades():
    """Wipes all trades.json records to ensure 100% fresh start from today."""
    save_trades([])
    save_live_state({"active_trade": None})

def calculate_brokerage_fees(qty, entry_price, exit_price):
    flat_brokerage = 40.0
    turnover = (entry_price + exit_price) * qty
    stt_and_taxes = turnover * 0.0005
    return round(flat_brokerage + stt_and_taxes, 2)

def record_completed_trade(symbol, strike, entry_price, exit_price, qty, status, win_loss_reason, layer_breakdown=None):
    trades = load_trades()
    ist_now = get_ist_now()
    date_time_str = ist_now.strftime("%Y-%m-%d %I:%M:%S %p IST")
    today_str = ist_now.strftime("%Y-%m-%d")
    
    if layer_breakdown is None:
        layer_breakdown = {}
    
    # DEDUPLICATION CHECK
    if trades:
        last_trade = trades[-1]
        if last_trade.get("symbol") == symbol and abs(last_trade.get("entry_price", 0) - entry_price) < 0.01 and last_trade.get("result") == status:
            return last_trade
    
    gross_pnl = round((exit_price - entry_price) * qty if status == "WIN" else (exit_price - entry_price) * qty, 2)
    brokerage = calculate_brokerage_fees(qty, entry_price, exit_price)
    net_pnl = round(gross_pnl - brokerage, 2)
    
    trade_record = {
        "trade_id": len(trades) + 1,
        "date_time": date_time_str,
        "date": today_str,
        "symbol": symbol,
        "strike": str(strike),
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "quantity": qty,
        "gross_pnl": gross_pnl,
        "brokerage_fee": brokerage,
        "net_pnl": net_pnl,
        "result": "WIN" if net_pnl > 0 else "LOSS",
        "post_mortem": win_loss_reason,
        "layers": layer_breakdown
    }
    
    trades.append(trade_record)
    save_trades(trades)
    return trade_record

def get_today_trades():
    trades = load_trades()
    today_str = get_ist_now().strftime("%Y-%m-%d")
    return [t for t in trades if t.get("date") == today_str]

def get_today_summary():
    today_trades = get_today_trades()
    total_trades = len(today_trades)
    wins = len([t for t in today_trades if t.get("result") == "WIN"])
    losses = len([t for t in today_trades if t.get("result") == "LOSS"])
    net_pnl = sum([t.get("net_pnl", 0.0) for t in today_trades])
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl": round(net_pnl, 2),
        "trades_remaining": max(0, 3 - total_trades)
    }

def get_weekly_trades(days=7):
    trades = load_trades()
    if not trades:
        return []
    ist_now = get_ist_now()
    cutoff_date = (ist_now - timedelta(days=days)).strftime("%Y-%m-%d")
    return [t for t in trades if t.get("date", "") >= cutoff_date]

def get_weekly_summary(days=7):
    weekly_trades = get_weekly_trades(days)
    total_trades = len(weekly_trades)
    wins = len([t for t in weekly_trades if t.get("result") == "WIN"])
    losses = len([t for t in weekly_trades if t.get("result") == "LOSS"])
    net_pnl = sum([t.get("net_pnl", 0.0) for t in weekly_trades])
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl": round(net_pnl, 2)
    }

def load_live_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_live_state(state_data):
    try:
        existing = load_live_state()
        existing.update(state_data)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4)
    except Exception as e:
        print(f"Error saving live state: {e}")
