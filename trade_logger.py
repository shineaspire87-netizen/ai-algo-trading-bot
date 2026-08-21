import json
import os
from datetime import datetime, timezone, timedelta
import importlib
import config
importlib.reload(config)

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
    if asset_filter is None:
        save_trades([])
        clear_active_trade("btc")
        clear_active_trade("nifty")
        clear_active_trade("forex")
    else:
        trades = load_trades()
        updated_trades = [t for t in trades if asset_filter.upper() not in t.get("symbol", "").upper()]
        save_trades(updated_trades)
        clear_active_trade(asset_filter.lower())

def calculate_brokerage_fees(qty, entry_price, exit_price, is_crypto=False):
    if is_crypto:
        turnover = (entry_price + exit_price) * qty
        return round(turnover * 0.00075, 2)
    else:
        return 0.0  # Zero brokerage for paper forex/options testing

def record_completed_trade(symbol, strike, entry_price, exit_price, qty, status, win_loss_reason, layer_breakdown, signal_type=None):
    """
    BUG 3 & 8 FIX: Accepts signal_type parameter for bulletproof directional PnL.
    signal_type = 'BUY_PUT' or 'BUY_CALL' — used for direction; falls back to symbol parsing.
    """
    trades = load_trades()
    ist_now = get_ist_now()
    date_time_str = ist_now.strftime("%Y-%m-%d %I:%M:%S %p IST")
    today_str = ist_now.strftime("%Y-%m-%d")
    now_ts = datetime.now().timestamp()

    sym_upper = symbol.upper()
    is_crypto = "BTC" in sym_upper
    is_forex = "FOREX" in sym_upper or "EUR" in sym_upper

    # BUG 3 & 8 FIX: Use signal_type param first; fall back to symbol parsing
    if signal_type is not None:
        is_put_short = signal_type.upper() in ["BUY_PUT", "SHORT", "SELL"]
    else:
        is_put_short = "PUT" in sym_upper or "SHORT" in sym_upper or "SELL" in sym_upper

    # DIRECTIONAL PNL FORMULA: Short/Put profit = (entry - exit) * qty
    if is_put_short:
        gross_pnl = round((entry_price - exit_price) * qty, 6 if is_forex else 2)
    else:
        gross_pnl = round((exit_price - entry_price) * qty, 6 if is_forex else 2)
    gross_pnl = round(gross_pnl, 2)

    brokerage = calculate_brokerage_fees(qty, entry_price, exit_price, is_crypto=is_crypto)
    net_pnl = round(gross_pnl - brokerage, 2)
    actual_result = "WIN" if net_pnl > 0 else "LOSS"
    
    # 5-SECOND DEDUPLICATION GUARD
    if trades:
        last_trade = trades[-1]
        last_ts = last_trade.get("timestamp_epoch", 0)
        if (now_ts - last_ts) < 5.0 and last_trade.get("symbol") == symbol and abs(last_trade.get("entry_price", 0) - entry_price) < 0.0001:
            return last_trade
    
    trade_record = {
        "trade_id": len(trades) + 1,
        "timestamp_epoch": now_ts,
        "date_time": date_time_str,
        "date": today_str,
        "symbol": symbol,
        "asset_type": "BTC" if is_crypto else ("FOREX" if is_forex else "NIFTY"),
        "currency": "$" if (is_crypto or is_forex) else "₹",
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
    asset_str = str(asset_filter).upper()
    if "BTC" in asset_str:
        target_key = "BTC"
    elif "FOREX" in asset_str:
        target_key = "FOREX"
    else:
        target_key = "NIFTY"
    return [t for t in trades if t.get("asset_type") == target_key or target_key in t.get("symbol", "").upper()]

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

def get_account_capital_summary(asset_filter="BTC", custom_start_cap=None):
    asset_str = str(asset_filter).upper()
    is_btc = "BTC" in asset_str
    is_forex = "FOREX" in asset_str
    
    if is_btc:
        default_cap = getattr(config, "BTC_START_CAPITAL_USD", 20.00)
        curr_sym = "$"
    elif is_forex:
        default_cap = getattr(config, "FOREX_START_CAPITAL_USD", 100.00)
        curr_sym = "$"
    else:
        default_cap = getattr(config, "NIFTY_START_CAPITAL_INR", 2000.00)
        curr_sym = "₹"

    start_cap = custom_start_cap if custom_start_cap is not None else default_cap
    
    summary = get_weekly_summary(days=30, asset_filter=asset_filter)
    cum_pnl = summary.get("net_pnl", 0.0)
    current_equity = round(start_cap + cum_pnl, 2)
    roi_pct = round((cum_pnl / start_cap) * 100.0, 1) if start_cap > 0 else 0.0
    
    return {
        "starting_capital": start_cap,
        "current_equity": current_equity,
        "cum_pnl": cum_pnl,
        "roi_pct": roi_pct,
        "currency": curr_sym
    }
