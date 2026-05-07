import pandas as pd
import numpy as np
from loguru import logger
import sys

def calc_zerolag_ema(series, length):
    ema1 = series.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    return 2 * ema1 - ema2

def calc_rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))

def add_qmp_qqe_features(df):
    df = df.copy()
    # QMP (Zero-Lag MACD)
    df['qmp_fast'] = calc_zerolag_ema(df['close'], 12)
    df['qmp_slow'] = calc_zerolag_ema(df['close'], 26)
    df['qmp_macd'] = df['qmp_fast'] - df['qmp_slow']
    sig1 = df['qmp_macd'].ewm(span=9, adjust=False).mean()
    sig2 = sig1.ewm(span=9, adjust=False).mean()
    df['qmp_line'] = 2 * sig1 - sig2
    df['qmp_hist'] = df['qmp_macd'] - df['qmp_line']

    # QQE (RSI Momentum + Volatility Filter)
    df['qqe_rsi'] = calc_rsi(df['close'], 8)
    df['qqe_rsi_ma'] = df['qqe_rsi'].ewm(span=1, adjust=False).mean()
    wilders = 8 * 2 - 1
    atr_rsi = abs(df['qqe_rsi_ma'] - df['qqe_rsi_ma'].shift(1))
    ma_atr = atr_rsi.ewm(alpha=1/wilders, min_periods=wilders).mean()
    df['qqe_dar'] = ma_atr.ewm(alpha=1/wilders, min_periods=wilders).mean() * 3.0
    df['qqe_momentum'] = df['qqe_rsi_ma'] - df['qqe_rsi_ma'].shift(1)

    # Signal Alignment (-1: Strong Bear | 0: Neutral | +1: Strong Bull)
    df['signal_alignment'] = np.sign(df['qmp_hist']) * np.sign(df['qqe_momentum'])
    return df.dropna()

def main():
    path = 'data/labeled_ob.csv'
    out_path = 'data/merged_features.csv'
    
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    except FileNotFoundError:
        logger.error(f"❌ {path} not found. Run Phase 1 first.")
        sys.exit(1)
        
    logger.info(f"📊 Loaded {len(df)} labeled bars. Calculating QMP/QQE...")
    df = add_qmp_qqe_features(df)
    
    # Validation Summary
    ob_bars = df[df['ob_formed']==True]
    bull_align = len(ob_bars[(ob_bars['ob_direction']=='bull') & (ob_bars['signal_alignment']>0)])
    bear_align = len(ob_bars[(ob_bars['ob_direction']=='bear') & (ob_bars['signal_alignment']<0)])
    total_ob = len(ob_bars)
    
    logger.info("="*50)
    logger.info("🔍 QMP/QQE VALIDATION SUMMARY")
    logger.info(f"Total OBs Detected: {total_ob}")
    logger.info(f"Bull OBs + Bull Alignment: {bull_align} ({bull_align/max(total_ob,1)*100:.1f}%)")
    logger.info(f"Bear OBs + Bear Alignment: {bear_align} ({bear_align/max(total_ob,1)*100:.1f}%)")
    logger.info(f"Signal Conflict (OB vs Alignment): {total_ob - bull_align - bear_align}")
    logger.info(f"✅ Expected alignment rate > 60% for viable edge")
    logger.info("="*50)
    
    df.to_csv(out_path)
    logger.info(f"💾 Merged dataset saved to {out_path}")

if __name__ == "__main__":
    main()
