# main.py - Stock Price Sync Fix
import time
from multi_strategy import scan_all_assets
from paper_broker import PaperBroker

def run_multi_asset_bot():
    print("==========================================================")
    print("🚀 MULTI-ASSET NSE ALGO SCANNER BOT STARTED 🚀")
    print("==========================================================")
    
    broker = PaperBroker(initial_capital=50.0)
    
    while True:
        try:
            best_trade, all_results = scan_all_assets()
            
            summary_str = " | ".join([f"{item['Name']}: {item['Signal']}" for item in all_results])
            print(f"\r[SCANNING] {summary_str}", end="")

            if broker.position is None and best_trade is not None:
                name = best_trade["Name"]
                signal = best_trade["Signal"]
                price = best_trade["Price"]
                
                premium = round(price * 0.01, 2) if "NIFTY" in name else round(price * 0.02, 2)
                opt_type = "CALL" if signal == "BUY_CALL" else "PUT"
                trade_symbol = f"{name}_OPT_{opt_type}"

                broker.buy_option(
                    symbol=trade_symbol, 
                    option_type=opt_type, 
                    entry_price=premium, 
                    stock_price=price, 
                    qty=15
                )

            elif broker.position is not None:
                current_trade_symbol = broker.position["symbol"]
                trade_name = current_trade_symbol.split("_")[0]
                
                for item in all_results:
                    if item["Name"] == trade_name:
                        curr_stock_price = item["Price"]
                        entry_stock_price = broker.position.get("entry_stock_price", curr_stock_price)
                        entry_premium = broker.position["entry_price"]
                        
                        stock_change = curr_stock_price - entry_stock_price
                        if broker.position["type"] == "CALL":
                            curr_premium = entry_premium + (stock_change * 0.5)
                        else:
                            curr_premium = entry_premium - (stock_change * 0.5)
                            
                        curr_premium = max(1.0, round(curr_premium, 2))
                        broker.update_market_price(curr_premium)
                        break

            time.sleep(5)

        except Exception as e:
            print(f"\n[ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_multi_asset_bot()