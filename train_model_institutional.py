# train_model_institutional.py - Top 10 Microstructure Feature Engineering & Calibrated Ensemble

import pandas as pd
import numpy as np
import ta
import logging
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit

# -------------------------------------------------------------
# 1. TOP 10 MICROSTRUCTURE & TECHNICAL FEATURE GENERATORS
# -------------------------------------------------------------
def compute_top10_microstructure_features(df_5m: pd.DataFrame) -> pd.DataFrame:
    """Computes Top 10 Microstructure and Technical Features for BTCUSDT"""
    df = df_5m.copy()
    
    # 1. Log Returns
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # 2. Kyle's Lambda (Price Impact per Unit Volume)
    df['Kyle_Lambda'] = abs(df['Close'] - df['Open']) / (df['Volume'] + 1e-6)
    
    # 3. Amihud Illiquidity Ratio
    df['Amihud_Illiquidity'] = abs(df['Log_Return']) / ((df['Volume'] * df['Close']) * 1e-6 + 1e-6)
    
    # 4. Corwin-Schultz Bounded Spread Proxy
    df['Spread_Proxy'] = (df['High'] - df['Low']) / (df['Close'] + 1e-6)
    
    # 5. 1-Hour Realized Volatility (sigma_60)
    df['Realized_Vol_1h'] = df['Log_Return'].rolling(12).std() * np.sqrt(12 * 24 * 365)
    
    # 6. Taker Depth Imbalance Proxy
    df['Taker_Depth_Imbalance'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'] + 1e-6)
    
    # 7. Trade Intensity (TI)
    df['Trade_Intensity'] = df['Volume'] / (df['Volume'].rolling(12).mean() + 1e-6)
    
    # 8. EMA Difference Percentage (Delta_EMA)
    ema9 = ta.trend.ema_indicator(df['Close'], window=9)
    ema50 = ta.trend.ema_indicator(df['Close'], window=50)
    df['Delta_EMA_Pct'] = ((ema9 - ema50) / (ema50 + 1e-6)) * 100.0

    # 9. ADX & Volume Ratio
    adx_ind = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    df['ADX_14'] = adx_ind.adx()
    df['Vol_Ratio_20'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-6)

    # 10. Candle Body Ratio
    df['Body_Ratio'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-6)

    return df.dropna()

# -------------------------------------------------------------
# 2. CALIBRATED XGBOOST + LIGHTGBM ENSEMBLE TRAINING
# -------------------------------------------------------------
def train_calibrated_institutional_ensemble(df_5m: pd.DataFrame):
    """Trains Isotonic Calibrated XGBoost + LightGBM Ensemble via Walk-Forward Cross Validation"""
    df_feat = compute_top10_microstructure_features(df_5m)
    
    if len(df_feat) < 100:
        logging.warning("Insufficient data length for Calibrated ML Ensemble training.")
        return None, None

    # Target Construction: Forward 1-Candle Return > All-In Friction (Fees + Slippage ~0.11%)
    friction_threshold = 0.0011 # 0.11% Round-trip Cost
    df_feat['Target'] = np.where(df_feat['Log_Return'].shift(-1) > friction_threshold, 1, 0)
    df_feat = df_feat.dropna()

    features = [
        'Kyle_Lambda', 'Amihud_Illiquidity', 'Spread_Proxy', 'Realized_Vol_1h',
        'Taker_Depth_Imbalance', 'Trade_Intensity', 'Delta_EMA_Pct', 'ADX_14',
        'Vol_Ratio_20', 'Body_Ratio'
    ]

    X = df_feat[features]
    y = df_feat['Target']

    # 5-Fold Walk-Forward TimeSeries Cross Validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    xgb = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42, eval_metric='logloss')
    lgb = LGBMClassifier(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42, verbose=-1)
    rf = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)

    # Base Soft Voting Ensemble
    base_ensemble = VotingClassifier(
        estimators=[('xgb', xgb), ('lgb', lgb), ('rf', rf)],
        voting='soft'
    )

    # Isotonic Probability Calibration
    calibrated_ensemble = CalibratedClassifierCV(estimator=base_ensemble, method='isotonic', cv=tscv)
    
    try:
        calibrated_ensemble.fit(X, y)
        logging.info("✅ Isotonic Calibrated XGBoost + LightGBM Ensemble Trained Successfully.")
        return calibrated_ensemble, features
    except Exception as e:
        logging.error(f"ML Ensemble Training Exception: {e}")
        return None, features

# -------------------------------------------------------------
# 3. PREDICT CALIBRATED WIN PROBABILITY P(Win)
# -------------------------------------------------------------
def predict_calibrated_win_probability(model, features_list: list, current_bar_df: pd.DataFrame) -> float:
    """Predicts Isotonic Calibrated Empirical Win Probability P(Win)"""
    if model is None or current_bar_df is None or len(current_bar_df) == 0:
        return 0.50 # Neutral Fallback

    try:
        df_feat = compute_top10_microstructure_features(current_bar_df)
        if df_feat.empty:
            return 0.50
            
        X_curr = df_feat[features_list].iloc[[-1]]
        prob_win = model.predict_proba(X_curr)[0][1] # Probability of Class 1 (Win)
        return round(float(prob_win), 4)
    except Exception as e:
        logging.warning(f"Probability Prediction Warning: {e}")
        return 0.50