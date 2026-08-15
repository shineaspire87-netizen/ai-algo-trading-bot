# train_model.py - Bug Fixed Institutional AI Model Training
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def detect_candlestick_patterns(df):
    open_p, high_p, low_p, close_p = df['Open'], df['High'], df['Low'], df['Close']
    body = abs(close_p - open_p)
    candle_range = (high_p - low_p).replace(0, 0.001)
    
    df['Pattern_Doji'] = (body <= (candle_range * 0.1)).astype(int)
    df['Pattern_Marubozu'] = (body >= (candle_range * 0.85)).astype(int)
    lower_shadow = np.minimum(open_p, close_p) - low_p
    df['Pattern_Hammer'] = ((lower_shadow >= (body * 2)) & (body > 0)).astype(int)
    upper_shadow = high_p - np.maximum(open_p, close_p)
    df['Pattern_ShootingStar'] = ((upper_shadow >= (body * 2)) & (body > 0)).astype(int)
    df['Pattern_BullishEngulfing'] = ((close_p > open_p) & (close_p.shift(1) < open_p.shift(1)) & (close_p >= open_p.shift(1))).astype(int)
    df['Pattern_BearishEngulfing'] = ((close_p < open_p) & (close_p.shift(1) > open_p.shift(1)) & (close_p <= open_p.shift(1))).astype(int)
    return df

def train_institutional_ai():
    print("==================================================")
    print("🤖 TRAINING INSTITUTIONAL LIFE-LONG AI MODEL 🤖")
    print("==================================================")
    
    print("1. 60 நாட்களின் வரலாற்றுத் தரவுகளைப் பதிவிறக்குகிறது...")
    df = yf.download(tickers="^NSEBANK", period="60d", interval="5m", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    print("2. 15+ நிறுவனத் தர இண்டிகேட்டர்கள் மற்றும் Candlestick Patterns கணக்கிடுகிறது...")
    # Indicators
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
    df['EMA_Diff'] = (df['EMA_9'] - df['EMA_21']) / df['EMA_21']
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    
    # Safe VWAP Calculation
    vol = df['Volume'].replace(0, np.nan).fillna(1)
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (typical_price * vol).cumsum() / vol.cumsum()
    df['VWAP_Diff'] = (df['Close'] - df['VWAP']) / df['VWAP']
    
    # Returns
    df['Return_1'] = df['Close'].pct_change(1)
    df['Return_3'] = df['Close'].pct_change(3)

    # Patterns
    df = detect_candlestick_patterns(df)

    # Future Return Target (15 Mins)
    df['Future_Return'] = df['Close'].shift(-3).pct_change(3)
    
    conditions = [
        (df['Future_Return'] > 0.0015),
        (df['Future_Return'] < -0.0015)
    ]
    choices = [2, 0] # 2: CALL, 0: PUT, 1: HOLD
    df['Target'] = np.select(conditions, choices, default=1)

    # Fill NaN values safely
    features = [
        'RSI', 'EMA_Diff', 'ATR', 'VWAP_Diff', 'Return_1', 'Return_3',
        'Pattern_Doji', 'Pattern_Marubozu', 'Pattern_Hammer', 
        'Pattern_ShootingStar', 'Pattern_BullishEngulfing', 'Pattern_BearishEngulfing'
    ]
    
    df[features] = df[features].bfill().ffill().fillna(0)
    df.dropna(subset=['Target'], inplace=True)

    X = df[features]
    y = df['Target']

    print(f"3. {len(X)} தரவுகளில் AI Model-க்கு பயிற்சி அளிக்கிறது...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = XGBClassifier(
        n_estimators=150, 
        max_depth=5, 
        learning_rate=0.03, 
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n✅ Institutional AI Model Training Complete! Accuracy: {accuracy*100:.2f}%\n")

    model.save_model("xgboost_model.json")
    print("✅ Life-Long AI Model 'xgboost_model.json' கோப்பாகச் சேமிக்கப்பட்டது!")

if __name__ == "__main__":
    train_institutional_ai()