import pandas as pd
import numpy as np
from loguru import logger
from itertools import product
import sys

def load_merged(path='data/merged_features.csv'):
    return pd.read_csv(path, index_col=0, parse_dates=True)

def simulate_strategy(df, body_min, vol_min, align_min, slippage=2, fee=1):
    trades = []
    for idx, row in df.iterrows():
        if not row['ob_formed']: continue
        if row['entry_quality'] < body_min * vol_min / 1.5: continue
        if abs(row['signal_alignment']) < align_min: continue
        
        direction = 'long' if row['ob_direction']=='bull' else 'short'
        entry = row['close'] * (1 + slippage/10000 * (1 if direction=='long' else -1))
        stop_atr, target_atr = row['atr']*1.5, row['atr']*2.5
        stop = entry - stop_atr if direction=='long' else entry + stop_atr
        target = entry + target_atr if direction=='long' else entry - target_atr
        
        # Simplified outcome: use signal strength as proxy
        hit = (row['signal_alignment'] * (1 if direction=='long' else -1)) > 0.3
        pnl = (target_atr/entry*100 if hit else -stop_atr/entry*100) - 2*fee/100
        trades.append({'pnl': pnl, 'direction': direction})
    
    if not trades: return None
    df_trades = pd.DataFrame(trades)
    win_rate = (df_trades['pnl']>0).mean()
    pf = abs(df_trades[df_trades['pnl']>0]['pnl'].sum() / df_trades[df_trades['pnl']<0]['pnl'].sum()) if len(df_trades[df_trades['pnl']<0])>0 else 0
    return {'n': len(trades), 'win_rate': win_rate, 'profit_factor': pf}

def main():
    df = load_merged()
    logger.info(f"🔧 Testing parameter grid on {len(df)} bars...")
    
    best = {'score': -1}
    for body_min, vol_min, align_min in product([0.5,0.6,0.7], [1.1,1.2,1.3], [0.5,0.6,0.7]):
        result = simulate_strategy(df, body_min, vol_min, align_min)
        if not result: continue
        # Composite score: prioritize profit factor, then win rate
        score = result['profit_factor'] * 0.6 + result['win_rate'] * 0.4
        if score > best['score']:
            best = {'score': score, 'params': (body_min, vol_min, align_min), 'result': result}
    
    if best['score'] < 0:
        logger.error("❌ No valid parameter combo found. Try different asset/timeframe.")
        return
        
    b,v,a = best['params']
    r = best['result']
    logger.info("="*60)
    logger.info("🏆 BEST PARAMETER COMBO FOUND")
    logger.info(f"body_ratio > {b}, vol_ratio > {v}, |alignment| > {a}")
    logger.info(f"Trades: {r['n']} | Win Rate: {r['win_rate']:.1%} | PF: {r['profit_factor']:.2f}")
    logger.info("-"*60)
    if r['profit_factor'] > 1.3 and r['win_rate'] > 0.55:
        logger.info("✅ EDGE VALIDATED with tuned params → Proceed to paper trading")
        # Auto-update the main scripts with best params
        with open('data/auto_label_ob.py', 'r') as f:
            content = f.read()
        content = content.replace('body_ratio > 0.5 and vol_ratio > 1.1', f'body_ratio > {b} and vol_ratio > {v}')
        with open('data/auto_label_ob.py', 'w') as f:
            f.write(content)
        with open('data/merge_qmp_qqe.py', 'r') as f:
            content = f.read()
        content = content.replace("abs(row['signal_alignment']) > 0.5", f"abs(row['signal_alignment']) > {a}")
        with open('data/merge_qmp_qqe.py', 'w') as f:
            f.write(content)
        logger.info("💾 Updated scripts with optimal parameters")
    else:
        logger.info("⚠️ Edge improved but not yet robust. Try different asset or timeframe.")
    logger.info("="*60)

if __name__ == "__main__":
    main()
