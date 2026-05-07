import pandas as pd
import numpy as np
from loguru import logger
import sys

def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Clean column names (TradingView exports sometimes have trailing spaces)
    df.columns = [c.strip().lower() for c in df.columns]
    # Combine Date & Time as strings, THEN convert to datetime
    df.index = pd.to_datetime(df['date'] + ' ' + df['time'])
    df = df[['open', 'high', 'low', 'close', 'volume']]
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    return df.dropna()

def detect_ob(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    df = df.copy()
    df['ob_formed'] = False
    df['ob_direction'] = 'none'
    df['entry_quality'] = 0.0
    
    swing_high = df['high'].rolling(2*lookback+1, center=True).max() == df['high']
    swing_low = df['low'].rolling(2*lookback+1, center=True).min() == df['low']
    
    for i in range(lookback*2, len(df)-1):
        idx = df.index[i]
        if swing_low.iloc[i] and df.loc[idx, 'close'] > df.loc[idx, 'open']:
            body_ratio = (df.loc[idx, 'close'] - df.loc[idx, 'open']) / (df.loc[idx, 'high'] - df.loc[idx, 'low'] + 1e-9)
            vol_ratio = df.loc[idx, 'volume'] / df['volume'].rolling(20).mean().iloc[i]
            if body_ratio > 0.7 and vol_ratio > 1.3:
                df.loc[idx, 'ob_formed'] = True
                df.loc[idx, 'ob_direction'] = 'bull'
                df.loc[idx, 'entry_quality'] = min(body_ratio * vol_ratio / 1.5, 1.0)
        elif swing_high.iloc[i] and df.loc[idx, 'close'] < df.loc[idx, 'open']:
            body_ratio = (df.loc[idx, 'open'] - df.loc[idx, 'close']) / (df.loc[idx, 'high'] - df.loc[idx, 'low'] + 1e-9)
            vol_ratio = df.loc[idx, 'volume'] / df['volume'].rolling(20).mean().iloc[i]
            if body_ratio > 0.7 and vol_ratio > 1.3:
                df.loc[idx, 'ob_formed'] = True
                df.loc[idx, 'ob_direction'] = 'bear'
                df.loc[idx, 'entry_quality'] = min(body_ratio * vol_ratio / 1.5, 1.0)
    return df

def main():
    input_path = 'data/raw_15m_data.csv'
    output_path = 'data/labeled_ob.csv'
    try:
        df = load_data(input_path)
    except FileNotFoundError:
        logger.error(f"❌ {input_path} not found. Generate test data or upload TradingView CSV.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Data load error: {e}")
        sys.exit(1)
        
    logger.info(f"📊 Loaded {len(df)} bars. Running OB detection...")
    labeled = detect_ob(df)
    labeled.to_csv(output_path)
    
    stats = labeled[labeled['ob_formed']==True]
    logger.info(f"✅ Done. Found {len(stats)} OBs ({len(stats[stats['ob_direction']=='bull'])} bull, {len(stats[stats['ob_direction']=='bear'])} bear)")
    logger.info(f"💾 Saved to {output_path}")

if __name__ == "__main__":
    main()
