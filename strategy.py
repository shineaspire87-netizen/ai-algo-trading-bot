# strategy.py - XGBoost AI Model மூலம் சிக்னல் உருவாக்கும் அமைப்பு
import os
import yfinance as yf
import pandas as pd
import ta
from xgboost import XGBClassifier

MODEL_FILE = "xgboost_model.json"
model = None

# AI Model-ஐ லோட் செய்கிறது
if os.path.exists(MODEL_FILE):
    model = XGBClassifier()
    model.load_model(MODEL_FILE)

def get_banknifty_data():
    """நேரலை டேட்டாவைப் பெறுகிறது"""
    df = yf.download(tickers="^NSEBANK", period="5d", interval="5m", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
    df['EMA_Diff'] = (df['EMA_9'] - df['EMA_21']) / df['EMA_21']
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['Return_1'] = df['Close'].pct_change(1)
    df['Return_3'] = df['Close'].pct_change(3)
    return df

def generate_signal(df):
    """AI Model மூலம் சிக்னல் வழங்குகிறது"""
    latest = df.iloc[-1]
    current_spot = latest['Close']

    if model is None:
        # AI Model இல்லை என்றால் பழைய விதிகளைப் பயன்படுத்தும்
        if latest['EMA_9'] > latest['EMA_21'] and latest['RSI'] > 55:
            return "BUY_CALL", current_spot
        elif latest['EMA_9'] < latest['EMA_21'] and latest['RSI'] < 45:
            return "BUY_PUT", current_spot
        return "HOLD", current_spot

    # AI Model-க்கான Features
    features = pd.DataFrame([{
        'RSI': latest['RSI'],
        'EMA_Diff': latest['EMA_Diff'],
        'ATR': latest['ATR'],
        'Return_1': latest['Return_1'],
        'Return_3': latest['Return_3']
    }])

    # AI Prediction: 2 -> CALL, 0 -> PUT, 1 -> HOLD
    pred = model.predict(features)[0]

    if pred == 2:
        return "BUY_CALL", current_spot
    elif pred == 0:
        return "BUY_PUT", current_spot
    else:
        return "HOLD", current_spot