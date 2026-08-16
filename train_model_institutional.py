# train_model_institutional.py
import pandas as pd
import numpy as np
import ta
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import VotingClassifier
from sklearn.model_selection import TimeSeriesSplit

def compute_advanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """புதிய Institutional Technical Indicators கணக்கீடு"""
    df = df.copy()
    
    # 1. Trend Strength Index (ADX)
    adx_indicator = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    df['ADX'] = adx_indicator.adx()
    df['DMI_Plus'] = adx_indicator.adx_pos()
    df['DMI_Minus'] = adx_indicator.adx_neg()

    # 2. Average True Range (ATR Volatility Expansion)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['ATR_Ratio'] = df['ATR'] / df['Close']

    # 3. Bollinger Bands Squeeze & Breakout
    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()
    df['BB_Width'] = (df['BB_High'] - df['BB_Low']) / bb.bollinger_mavg()

    # 4. Supertrend Indicator (Period 10, Multiplier 3)
    hl2 = (df['High'] + df['Low']) / 2
    df['ST_Upper'] = hl2 + (3 * df['ATR'])
    df['ST_Lower'] = hl2 - (3 * df['ATR'])
    df['Supertrend_Direction'] = np.where(df['Close'] > df['ST_Upper'].shift(1), 1, 
                                 np.where(df['Close'] < df['ST_Lower'].shift(1), -1, 0))

    # 5. Candle Body Ratio (Ezekiel Chew Rule)
    df['Body_Range_Ratio'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-6)

    return df.dropna()

def train_institutional_ensemble(df: pd.DataFrame):
    """XGBoost + LightGBM Ensemble Model Training with TimeSeries Cross Validation"""
    df = compute_advanced_indicators(df)
    
    # Target Construction: Next 1-candle return >= +0.60% Option Gain (~0.003 Spot Gain)
    df['Target'] = np.where(df['Close'].shift(-1) > df['Close'] * 1.003, 1, 0)
    
    features = ['ADX', 'DMI_Plus', 'DMI_Minus', 'ATR_Ratio', 'BB_Width', 'Supertrend_Direction', 'Body_Range_Ratio']
    X = df[features]
    y = df['Target']

    # TimeSeries Split for Out-of-Sample Validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    xgb = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.03, random_state=42)
    lgb = LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.03, random_state=42)
    
    # Ensemble Classifier (Soft Voting)
    ensemble = VotingClassifier(estimators=[('xgb', xgb), ('lgb', lgb)], voting='soft')
    
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        ensemble.fit(X_train, y_train)

    return ensemble, features