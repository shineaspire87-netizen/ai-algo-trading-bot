import json
import os
import csv
from datetime import datetime, timezone, timedelta
import ai_analyst

TRADES_FILE = "trades.json"
CSV_FILE = "trades.csv"
STATE_FILE = "live_state.json"

def get_ist_now():
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=5, minutes=30)

def calculate_brokerage_fees(qty, entry_price, exit_price):
    flat_brokerage = 40.0
    turnover = (entry_price + exit_price) * qty
    stt_and_taxes = turnover * 0.0005
    return round(flat_brokerage + stt_and_taxes, 2)

def clean_float(val):
    if not val:
        return 0.0
    cleaned = str(val).replace("$", "").replace("₹", "").replace(",", "").replace("+", "").strip()
    try:
        return float(cleaned)
    except Exception:
        return 0.0

def load_trades():
    trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, "r", encoding="utf-8") as f:
                trades = json.load(f)
        except Exception:
            trades = []

    # Sync with trades.csv if available
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        try:
            with open(CSV_FILE, mode="r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                
            if len(lines) > 1:
                csv_trades = []
                for idx, line in enumerate(lines[1:], start=1):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 8:
                        continue
                    
                    if len(parts) >= 10 and ("202" in parts[0] or "202" in parts[1]):
                        entry_time = parts[0]
                        exit_time = parts[1]
                        symbol = parts[2]
                        opt_type = parts[3]
                        entry_p = clean_float(parts[4])
                        exit_p = clean_float(parts[5])
                        qty = int(clean_float(parts[8])) if len(parts) > 8 else 1
                        reason = parts[9] if len(parts) > 9 else "COMPLETED_TRADE"
                        
                        if len(parts) >= 13:
                            gross_pnl = clean_float(parts[10])
                            brokerage = clean_float(parts[11])
                            net_pnl = clean_float(parts[12])
                        elif len(parts) == 12:
                            gross_pnl = clean_float(parts[10])
                            brokerage = calculate_brokerage_fees(qty, entry_p, exit_p)
                            net_pnl = round(gross_pnl - brokerage, 2)
                        else:
                            gross_pnl = round((exit_p - entry_p) * qty, 2)
                            brokerage = calculate_brokerage_fees(qty, entry_p, exit_p)
                            net_pnl = round(gross_pnl - brokerage, 2)
                            
                        dt_str = exit_time if exit_time else entry_time
                        date_part = dt_str.split(" ")[0] if dt_str else get_ist_now().strftime("%Y-%m-%d")
                        strike_sym = f"{symbol} ({opt_type})" if (opt_type and opt_type not in symbol) else symbol
                        result = "WIN" if net_pnl > 0 else "LOSS"

                        record = {
                            "trade_id": idx,
                            "date_time": dt_str,
                            "date": date_part,
                            "symbol": symbol,
                            "strike": strike_sym,
                            "entry_price": entry_p,
                            "exit_price": exit_p,
                            "quantity": qty,
                            "gross_pnl": gross_pnl,
                            "brokerage_fee": brokerage,
                            "net_pnl": net_pnl,
                            "result": result,
                            "post_mortem": reason,
                            "layers": {}
                        }
                        csv_trades.append(record)

                if not trades and csv_trades:
                    trades = csv_trades
                    save_trades(trades)
                elif csv_trades:
                    existing_keys = {(t.get("date_time"), t.get("symbol")) for t in trades}
                    added = False
                    for ct in csv_trades:
                        key = (ct.get("date_time"), ct.get("symbol"))
                        if key not in existing_keys:
                            ct["trade_id"] = len(trades) + 1
                            trades.append(ct)
                            added = True
                    if added:
                        save_trades(trades)
        except Exception as e:
            print(f"Error parsing trades.csv: {e}")

    # Ensure every trade record has bot_thoughts and required_improvements fields
    updated_needed = False
    for t in trades:
        if "bot_thoughts" not in t or "required_improvements" not in t:
            reflection = ai_analyst.generate_bot_reflection(t)
            t["bot_thoughts"] = reflection["bot_thought"]
            t["required_improvements"] = reflection["required_improvements"]
            updated_needed = True
            
    if updated_needed:
        save_trades(trades)

    return trades

def save_trades(trades):
    with open(TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=4)

def clear_all_trades():
    """Clears trade logs only when manually requested."""
    save_trades([])
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Entry_Time", "Exit_Time", "Symbol", "Option_Type", 
                    "Entry_Price", "Exit_Price", "Stop_Loss", "Target", 
                    "Quantity", "Exit_Reason", "Gross_PnL", "Brokerage_Taxes", "Net_PnL", "Capital_Balance"
                ])
        except Exception:
            pass
    save_live_state({"last_signal": {}, "active_trade": {"status": "NO_POSITION"}})

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

def record_completed_trade(symbol, strike, entry_price, exit_price, qty, status, win_loss_reason, layer_breakdown=None):
    trades = load_trades()
    ist_now = get_ist_now()
    
    if layer_breakdown is None:
        layer_breakdown = {}

    opt_type = "CALL" if "CALL" in str(strike).upper() or "CE" in str(strike).upper() else ("PUT" if "PUT" in str(strike).upper() or "PE" in str(strike).upper() else "BUY")
    
    if opt_type == "PUT":
        gross_pnl = round((entry_price - exit_price) * qty, 2)
    else:
        gross_pnl = round((exit_price - entry_price) * qty, 2)

    brokerage = calculate_brokerage_fees(qty, entry_price, exit_price)
    net_pnl = round(gross_pnl - brokerage, 2)
    result_str = status.upper() if status in ["WIN", "LOSS"] else ("WIN" if net_pnl > 0 else "LOSS")
    
    trade_record = {
        "trade_id": len(trades) + 1,
        "date_time": ist_now.strftime("%Y-%m-%d %I:%M:%S %p IST"),
        "date": ist_now.strftime("%Y-%m-%d"),
        "symbol": symbol,
        "strike": str(strike),
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "quantity": qty,
        "gross_pnl": gross_pnl,
        "brokerage_fee": brokerage,
        "net_pnl": net_pnl,
        "result": result_str,
        "post_mortem": win_loss_reason,
        "layers": layer_breakdown
    }
    
    reflection = ai_analyst.generate_bot_reflection(trade_record)
    trade_record["bot_thoughts"] = reflection["bot_thought"]
    trade_record["required_improvements"] = reflection["required_improvements"]

    trades.append(trade_record)
    save_trades(trades)

    # Sync to trades.csv
    try:
        file_exists = os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Entry_Time", "Exit_Time", "Symbol", "Option_Type", 
                    "Entry_Price", "Exit_Price", "Stop_Loss", "Target", 
                    "Quantity", "Exit_Reason", "Gross_PnL", "Brokerage_Taxes", "Net_PnL", "Capital_Balance"
                ])
            writer.writerow([
                trade_record["date_time"],
                ist_now.strftime("%Y-%m-%d %H:%M:%S"),
                symbol,
                opt_type,
                f"{entry_price:.2f}",
                f"{exit_price:.2f}",
                "0.00",
                "0.00",
                qty,
                win_loss_reason,
                f"{gross_pnl:.2f}",
                f"{brokerage:.2f}",
                f"{net_pnl:.2f}",
                "100000.00"
            ])
    except Exception as e:
        print(f"Error appending to trades.csv: {e}")

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
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl": round(net_pnl, 2),
        "trades_remaining": max(0, 3 - total_trades)
    }

def get_weekly_trades(days=7):
    """Fetches all trades from the past 7 days for 1-Week evaluation."""
    trades = load_trades()
    if not trades:
        return []
    ist_now = get_ist_now()
    cutoff_date = (ist_now - timedelta(days=days)).strftime("%Y-%m-%d")
    return [t for t in trades if t.get("date", "") >= cutoff_date]

def get_weekly_summary(days=7):
    """Calculates aggregate statistics over 1-Week testing period."""
    weekly_trades = get_weekly_trades(days)
    total_trades = len(weekly_trades)
    wins = len([t for t in weekly_trades if t.get("result") == "WIN"])
    losses = len([t for t in weekly_trades if t.get("result") == "LOSS"])
    net_pnl = sum([t.get("net_pnl", 0.0) for t in weekly_trades])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl": round(net_pnl, 2)
    }

