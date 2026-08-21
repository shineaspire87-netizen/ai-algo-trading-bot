import json
import os
from datetime import datetime, timezone, timedelta

TRADES_FILE = "trades.json"

def get_ist_now():
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=5, minutes=30)

def load_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    try:
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=4)

def save_active_trade(trade_dict, asset_key="BTC"):
    filename = f"active_trade_{asset_key.lower()}.json"
    with open(filename, "w") as f:
        json.dump(trade_dict, f, indent=4)

def load_active_trade(asset_key="BTC"):
    filename = f"active_trade_{asset_key.lower()}.json"
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception:
        return None

def clear_active_trade(asset_key="BTC"):
    filename = f"active_trade_{asset_key.lower()}.json"
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except Exception:
            pass

def delete_trade_by_id(trade_id):
    trades = load_trades()
    updated_trades = [t for t in trades if t.get("trade_id") != trade_id]
    save_trades(updated_trades)

def clear_asset_trades(asset_filter=None):
    """Clears trade logs for a specific asset or all trades if asset_filter is None."""
    if asset_filter is None:
        save_trades([])
        clear_active_trade("btc")
        clear_active_trade("nifty")
    else:
        trades = load_trades()
        updated_trades = [t for t in trades if asset_filter.upper() not in t.get("symbol", "").upper()]
        save_trades(updated_trades)
        clear_active_trade(asset_filter.lower())

def calculate_brokerage_fees(qty, entry_price, exit_price, is_crypto=False):
    if is_crypto:
        turnover = (entry_price + exit_price) * qty
        return round(turnover * 0.00075, 2)  # 0.075% Binance trading fee
    else:
        flat_brokerage = 40.0
        turnover = (entry_price + exit_price) * qty
        stt_and_taxes = turnover * 0.0005
        return round(flat_brokerage + stt_and_taxes, 2)

def record_completed_trade(symbol, strike, entry_price, exit_price, qty, status, win_loss_reason, layer_breakdown):
    trades = load_trades()
    ist_now = get_ist_now()
    date_time_str = ist_now.strftime("%Y-%m-%d %I:%M:%S %p IST")
    today_str = ist_now.strftime("%Y-%m-%d")
    
    is_crypto = "BTC" in symbol.upper()
    gross_pnl = round((exit_price - entry_price) * qty if status == "WIN" else (exit_price - entry_price) * qty, 2)
    brokerage = calculate_brokerage_fees(qty, entry_price, exit_price, is_crypto=is_crypto)
    net_pnl = round(gross_pnl - brokerage, 2)
    actual_result = "WIN" if net_pnl > 0 else "LOSS"
    
    # DEDUPLICATION CHECK
    if trades:
        last_trade = trades[-1]
        if last_trade.get("symbol") == symbol and abs(last_trade.get("entry_price", 0) - entry_price) < 0.01 and last_trade.get("result") == actual_result:
            return last_trade
    
    trade_record = {
        "trade_id": len(trades) + 1,
        "date_time": date_time_str,
        "date": today_str,
        "symbol": symbol,
        "asset_type": "BTC" if is_crypto else "NIFTY",
        "currency": "$" if is_crypto else "₹",
        "strike": strike,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": qty,
        "gross_pnl": gross_pnl,
        "brokerage_fee": brokerage,
        "net_pnl": net_pnl,
        "result": actual_result,
        "post_mortem": win_loss_reason,
        "layers": layer_breakdown
    }
    
    trades.append(trade_record)
    save_trades(trades)
    return trade_record

def filter_trades_by_asset(trades, asset_filter=None):
    if not asset_filter:
        return trades
    target_key = "BTC" if "BTC" in asset_filter.upper() else "NIFTY"
    return [t for t in trades if t.get("asset_type", "NIFTY") == target_key or target_key in t.get("symbol", "").upper()]

def get_today_trades(asset_filter=None):
    trades = load_trades()
    today_str = get_ist_now().strftime("%Y-%m-%d")
    today_list = [t for t in trades if t.get("date") == today_str]
    return filter_trades_by_asset(today_list, asset_filter)

def get_today_summary(asset_filter=None):
    today_trades = get_today_trades(asset_filter)
    total_trades = len(today_trades)
    wins = len([t for t in today_trades if t.get("result") == "WIN"])
    losses = len([t for t in today_trades if t.get("result") == "LOSS"])
    net_pnl = sum([t.get("net_pnl", 0) for t in today_trades])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl": round(net_pnl, 2),
        "trades_remaining": max(0, 3 - total_trades)
    }

def get_weekly_trades(days=7, asset_filter=None):
    trades = load_trades()
    if not trades:
        return []
    ist_now = get_ist_now()
    cutoff_date = (ist_now - timedelta(days=days)).strftime("%Y-%m-%d")
    weekly_list = [t for t in trades if t.get("date", "") >= cutoff_date]
    return filter_trades_by_asset(weekly_list, asset_filter)

def get_weekly_summary(days=7, asset_filter=None):
    weekly_trades = get_weekly_trades(days, asset_filter)
    total_trades = len(weekly_trades)
    wins = len([t for t in weekly_trades if t.get("result") == "WIN"])
    losses = len([t for t in weekly_trades if t.get("result") == "LOSS"])
    net_pnl = sum([t.get("net_pnl", 0) for t in weekly_trades])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl": round(net_pnl, 2)
    }
