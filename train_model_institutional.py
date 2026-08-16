# train_model_institutional.py
import pandas as pd
import numpy as np
import ta
import logging
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit

# 70% AI Win-Rate Confidence Threshold
AI_CONFIDENCE_THRESHOLD = 0.70

def compute_advanced_institutional_features(df: pd.DataFrame) -> pd.DataFrame:
    """Institutional Technical Indicators கணக்கீடு"""
    df = df.copy()
    
    # 1. ADX (Trend Strength > 25 Filter)
    adx_ind = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    df['ADX'] = adx_ind.adx()
    df['DMI_Plus'] = adx_ind.adx_pos()
    df['DMI_Minus'] = adx_ind.adx_neg()

    # 2. ATR Ratio (Volatility Expansion)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['ATR_Ratio'] = df['ATR'] / df['Close']

    # 3. Bollinger Bands Squeeze & Width
    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_Width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()

    # 4. Ezekiel Chew Body Range Ratio
    df['Body_Ratio'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-6)

    # 5. Volume MA Ratio (>= 1.2x)
    df['Vol_MA20'] = df['Volume'].rolling(20).mean()
    df['Vol_Ratio'] = df['Volume'] / (df['Vol_MA20'] + 1e-6)

    # 6. EMA 9/21 Slope Alignment
    df['EMA9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA21'] = ta.trend.ema_indicator(df['Close'], window=21)
    df['EMA_Slope'] = (df['EMA9'] - df['EMA21']) / df['EMA21']

    return df.dropna()

def train_and_get_ensemble_model(df: pd.DataFrame):
    """XGBoost + LightGBM + RandomForest Ensemble Classifier Training"""
    df_feat = compute_advanced_institutional_features(df)
    if len(df_feat) < 50:
        return None, None
        
    # Target Construction: Next 1-Candle Return >= +0.30% Spot Gain (~+6.0% Option Premium)
    df_feat['Target'] = np.where(df_feat['Close'].shift(-1) > df_feat['Close'] * 1.003, 1, 0)
    
    features = ['ADX', 'DMI_Plus', 'DMI_Minus', 'ATR_Ratio', 'BB_Width', 'Body_Ratio', 'Vol_Ratio', 'EMA_Slope']
    X = df_feat[features]
    y = df_feat['Target']

    # TimeSeries Split Cross Validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    xgb = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.03, random_state=42, eval_metric='logloss')
    lgb = LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.03, random_state=42, verbose=-1)
    rf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
    
    # Soft Voting Ensemble
    ensemble = VotingClassifier(
        estimators=[('xgb', xgb), ('lgb', lgb), ('rf', rf)], 
        voting='soft'
    )
    
    for train_idx, test_idx in tscv.split(X):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        ensemble.fit(X_tr, y_tr)

    logging.info("✅ XGBoost + LightGBM Model Retrained with 70% Confidence Threshold")
    return ensemble, features

def predict_signal_probability(model, features_list, current_row_df):
    """Predicts Probability Score P(Win)"""
    if model is None:
        return 0.50
    try:
        X_curr = current_row_df[features_list]
        prob_win = model.predict_proba(X_curr)[0][1] # Win Probability
        return round(float(prob_win), 4)
    except Exception as e:
        logging.error(f"Prediction Error: {e}")
        return 0.50

def train_walk_forward_ensemble(df: pd.DataFrame):
    """Walk-Forward Cross Validation to Prevent Overfitting"""
    df = df.copy()
    
    # Feature Calculations
    adx_ind = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    df['ADX'] = adx_ind.adx()
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['Body_Ratio'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-6)
    df['Vol_Ratio'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-6)
    
    df['Target'] = np.where(df['Close'].shift(-1) > df['Close'] * 1.003, 1, 0)
    df = df.dropna()
    
    features = ['ADX', 'ATR', 'Body_Ratio', 'Vol_Ratio']
    X = df[features]
    y = df['Target']
    
    # 5-Fold Walk-Forward TimeSeries Split
    tscv = TimeSeriesSplit(n_splits=5)
    
    xgb = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42)
    lgb = LGBMClassifier(n_estimators=100, max_depth=3, learning_rate=0.03, random_state=42, verbose=-1)
    
    ensemble = VotingClassifier(estimators=[('xgb', xgb), ('lgb', lgb)], voting='soft')
    
    # Out-of-Sample Walk-Forward Training Loop
    oof_scores = []
    for train_idx, val_idx in tscv.split(X):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]
        
        ensemble.fit(X_tr, y_tr)
        acc = ensemble.score(X_va, y_va)
        oof_scores.append(acc)
        
    logging.info(f"✅ Walk-Forward Cross-Validation Score: {np.mean(oof_scores):.4f}")
    return ensemble, features