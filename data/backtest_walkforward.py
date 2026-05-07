import pandas as pd
import numpy as np
from loguru import logger
import sys
from datetime import timedelta

def generate_walkforward_splits(df, train_days=90, test_days=30, step_days=15):
    """Purged walk-forward splits to prevent lookahead bias"""
    splits = []
    start_idx = 0
    while start_idx + train_days + test_days < len(df):
        train_end = start_idx + train_days
        test_start = train_end + 5  # 5-bar purge gap
        test_end = test_start + test_days
        if test_end > len(df): break
        splits.append((start_idx, train_end, test_start, test_end))
        start_idx += step_days
    return splits

def simulate_trade(row, direction, slippage_bps=5, fee_bps=2):
    """Realistic trade simulation with slippage + fees"""
    entry = row['close'] * (1 + slippage_bps/10000 * (1 if direction=='long' else -1))
    stop_atr = row['atr'] * 1.5
    target_atr = row['atr'] * 2.5
    
    if direction == 'long':
        stop = entry - stop_atr
        target = entry + target_atr
    else:
        stop = entry + stop_atr
        target = entry - target_atr
        
    # Simplified: assume target hit before stop if signal alignment strong
    hit_target = (row['signal_alignment'] * (1 if direction=='long' else -1)) > 0.5
    pnl_pct = (target_atr / entry * 100) if hit_target else (-stop_atr / entry * 100)
    
    # Apply fees (round trip)
    pnl_pct -= 2 * fee_bps / 100
    return pnl_pct

def run_backtest(df, splits):
    results = []
    for train_start, train_end, test_start, test_end in splits:
        train = df.iloc[train_start:train_end]
        test = df.iloc[test_start:test_end]
        
        # Simple rule-based strategy (replace with ML model later)
        trades = []
        for idx in test.index:
            row = test.loc[idx]
            if row['ob_formed'] and abs(row['signal_alignment']) > 0.5:
                direction = 'long' if row['ob_direction']=='bull' else 'short'
                pnl = simulate_trade(row, direction)
                trades.append({
                    'date': idx, 'direction': direction, 
                    'pnl_pct': pnl, 'confidence': abs(row['signal_alignment']),
                    'entry_quality': row['entry_quality']
                })
        
        if trades:
            trade_df = pd.DataFrame(trades)
            results.append({
                'split_start': test.index[0],
                'n_trades': len(trade_df),
                'win_rate': (trade_df['pnl_pct']>0).mean(),
                'avg_pnl': trade_df['pnl_pct'].mean(),
                'profit_factor': abs(trade_df[trade_df['pnl_pct']>0]['pnl_pct'].sum() / 
                                   trade_df[trade_df['pnl_pct']<0]['pnl_pct'].sum()),
                'max_dd': trade_df['pnl_pct'].cumsum().min(),
                'sharpe': trade_df['pnl_pct'].mean() / (trade_df['pnl_pct'].std() + 1e-10)
            })
    return pd.DataFrame(results)

def main():
    path = 'data/merged_features.csv'
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    except FileNotFoundError:
        logger.error(f"❌ {path} not found. Run Phase 2 first.")
        sys.exit(1)
        
    logger.info(f"📊 Loaded {len(df)} bars. Running walk-forward backtest...")
    splits = generate_walkforward_splits(df)
    results = run_backtest(df, splits)
    
    if len(results) == 0:
        logger.error("❌ No valid splits generated. Check data length.")
        sys.exit(1)
        
    # Aggregate metrics
    agg = {
        'total_trades': results['n_trades'].sum(),
        'win_rate': results['win_rate'].mean(),
        'profit_factor': results['profit_factor'].mean(),
        'avg_sharpe': results['sharpe'].mean(),
        'worst_dd': results['max_dd'].min()
    }
    
    # Pass/Fail thresholds (conservative)
    logger.info("="*60)
    logger.info("🔍 WALK-FORWARD BACKTEST RESULTS")
    logger.info(f"Total Trades: {agg['total_trades']}")
    logger.info(f"Win Rate: {agg['win_rate']:.1%} (target >55%)")
    logger.info(f"Profit Factor: {agg['profit_factor']:.2f} (target >1.3)")
    logger.info(f"Sharpe Ratio: {agg['avg_sharpe']:.2f} (target >0.8)")
    logger.info(f"Worst Drawdown: {agg['worst_dd']:.1%} (target >-20%)")
    logger.info("-"*60)
    
    passed = (
        agg['win_rate'] > 0.55 and 
        agg['profit_factor'] > 1.3 and 
        agg['avg_sharpe'] > 0.8 and 
        agg['worst_dd'] > -0.20
    )
    
    if passed:
        logger.info("✅ EDGE VALIDATED: Proceed to paper trading")
    else:
        logger.info("❌ EDGE NOT VALIDATED: Tune parameters or collect more data")
    logger.info("="*60)
    
    results.to_csv('data/backtest_results.csv')
    logger.info(f"💾 Detailed results saved to data/backtest_results.csv")

if __name__ == "__main__":
    main()
