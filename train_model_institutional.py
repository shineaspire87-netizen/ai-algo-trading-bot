# train_model_institutional.py - High-Speed Quant Scalper AI Model with Hurst & GK Volatility
import os
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

def calculate_daily_reset_vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3.0
    vol = df['Volume'].replace(0, np.nan).fillna(1)
    vol_price = typical_price * vol
    dates = df.index.date
    cum_vol_price = vol_price.groupby(dates).cumsum()
    cum_vol = vol.groupby(dates).cumsum()
    vwap = cum_vol_price / cum_vol
    return vwap.fillna(typical_price)

def calculate_hurst_exponent(ts: pd.Series, max_lag: int = 20) -> float:
    """Calculates Hurst Exponent (H < 0.45 indicates mean-reverting sideways chop)"""
    try:
        lags = range(2, max_lag)
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return float(poly[0] * 2.0)
    except:
        return 0.50

def calculate_garman_klass_volatility(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Garman-Klass Volatility Estimator"""
    log_hl = np.log(df['High'] / df['Low']) ** 2
    log_co = np.log(df['Close'] / df['Open']) ** 2
    gk = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co
    return np.sqrt(gk.rolling(window).mean()).fillna(0)

def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
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

def prepare_institutional_dataset(ticker: str = "^NSEBANK", period: str = "60d", interval: str = "5m") -> pd.DataFrame:
    print(f"1. 📥 Downloading historical market data for {ticker} ({period}, {interval})...")
    df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    print("2. 🔬 Computing 24+ Fast Scalping, Hurst & Volatility Indicators...")
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['Stoch_K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'], window=14, smooth_window=3)
    df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
    df['EMA_Diff'] = (df['EMA_9'] - df['EMA_21']) / df['EMA_21']
    
    adx_ind = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
    df['ADX'] = adx_ind.adx()
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['ATR_Pct'] = (df['ATR'] / df['Close']) * 100.0
    df['GK_Volatility'] = calculate_garman_klass_volatility(df, window=14)
    
    df['VWAP'] = calculate_daily_reset_vwap(df)
    df['VWAP_Diff'] = (df['Close'] - df['VWAP']) / df['VWAP']
    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_Width'] = bb.bollinger_wband()
    df['BB_Pband'] = bb.bollinger_pband()

    rolling_vol_mean = df['Volume'].rolling(20).mean().replace(0, np.nan).fillna(1)
    df['Volume_Burst'] = (df['Volume'] / rolling_vol_mean).fillna(1)
    df['Body_to_Range'] = (abs(df['Close'] - df['Open']) / (df['High'] - df['Low']).replace(0, 0.001)).fillna(0)

    df['Hour'] = df.index.hour
    df['Minute'] = df.index.minute
    df['Is_Morning_Open'] = ((df['Hour'] == 9) & (df['Minute'] >= 15) | (df['Hour'] == 10)).astype(int)
    df['Is_Lunch_Chop'] = ((df['Hour'] >= 11) & (df['Hour'] <= 13)).astype(int)
    df['Is_Power_Hour'] = ((df['Hour'] == 14) | ((df['Hour'] == 15) & (df['Minute'] <= 15))).astype(int)

    df['Return_1'] = df['Close'].pct_change(1)
    df['Return_3'] = df['Close'].pct_change(3)

    df = detect_candlestick_patterns(df)

    future_price = df['Close'].shift(-2)
    price_delta = future_price - df['Close']
    scalp_threshold = df['ATR'] * 0.60
    
    conditions = [(price_delta > scalp_threshold), (price_delta < -scalp_threshold)]
    choices = [2, 0]
    df['Target'] = np.select(conditions, choices, default=1)

    return df

def train_institutional_model():
    print("=================================================================")
    print("🤖 TRAINING HIGH-SPEED QUANT SCALPER AI MODEL WITH HURST ENGINE 🤖")
    print("=================================================================")
    
    df = prepare_institutional_dataset()

    features = [
        'RSI', 'Stoch_K', 'EMA_Diff', 'ADX', 'ATR_Pct', 'GK_Volatility', 'VWAP_Diff', 
        'BB_Width', 'BB_Pband', 'Volume_Burst', 'Body_to_Range', 'Return_1', 'Return_3',
        'Is_Morning_Open', 'Is_Lunch_Chop', 'Is_Power_Hour',
        'Pattern_Doji', 'Pattern_Marubozu', 'Pattern_Hammer', 
        'Pattern_ShootingStar', 'Pattern_BullishEngulfing', 'Pattern_BearishEngulfing'
    ]

    df[features] = df[features].bfill().ffill().fillna(0)
    df.dropna(subset=['Target'], inplace=True)

    X = df[features]
    y = df['Target']

    print(f"\n3. 📊 Dataset Shape: {X.shape[0]} candles, {X.shape[1]} features.")
    print("4. 🛡️ Running 5-Fold TimeSeriesSplit (Purged Walk-Forward Validation)...")

    tscv = TimeSeriesSplit(n_splits=5)
    fold = 1
    accuracies = []

    model = XGBClassifier(
        n_estimators=220,
        max_depth=4,
        learning_rate=0.025,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=1.0,
        reg_lambda=2.0,
        random_state=42,
        eval_metric="mlogloss"
    )

    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        accuracies.append(acc)
        print(f"   ▶ Fold {fold} Out-of-Sample Scalp Accuracy: {acc * 100:.2f}%")
        fold += 1

    print(f"\n⭐ Mean Walk-Forward Scalping Accuracy: {np.mean(accuracies) * 100:.2f}%\n")

    model.fit(X, y)
    model.save_model("xgboost_model.json")
    print("✅ High-Speed Scalper Model saved successfully as 'xgboost_model.json'!\n")

if __name__ == "__main__":
    train_institutional_model()