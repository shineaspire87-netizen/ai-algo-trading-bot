# force_close.py - Write Today's Trade to trades.csv & Update Dashboard
import os
import csv
import json

CSV_FILE = "trades.csv"
ACTIVE_JSON = "active_trade.json"

# Write Header if missing
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Entry_Time", "Exit_Time", "Symbol", "Option_Type", 
            "Entry_Price", "Exit_Price", "Stop_Loss", "Target", 
            "Quantity", "Exit_Reason", "PnL", "Capital_Balance"
        ])

# Append Today's Reliance Trade Result
with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "2026-08-14 13:09:26",
        "2026-08-14 15:15:00",
        "RELIANCE_OPT_CE",
        "CALL",
        "26.14",
        "27.64",
        "22.22",
        "33.99",
        "15",
        "3:15_PM_MARKET_CLOSE",
        "22.50",
        "100022.50"
    ])

# Clear Active Trade JSON
with open(ACTIVE_JSON, "w", encoding="utf-8") as f:
    json.dump({"status": "NO_POSITION"}, f, indent=4)

print("✅ இன்றைய Reliance டிரேட் வெற்றிகரமாக 'trades.csv' கோப்பில் சேமிக்கப்பட்டது!")