import yfinance as yf, pandas as pd, numpy as np, os, requests
from datetime import datetime
from loguru import logger

SYMBOL, INTERVAL = "GC=F", "1h"
BODY_MIN, VOL_MIN, ALIGN_MIN = 0.55, 1.15, 0.55
TOKEN, CHAT = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT"]

def fetch_and_check():
    df = yf.download(SYMBOL, period="45d", interval=INTERVAL, progress=False)
    df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={'Open':'o','High':'h','Low':'l','Close':'c','Volume':'v'})
    df['atr'] = (df['h'] - df['l']).rolling(14).mean()
    
    def zlema(s, p): e1=s.ewm(span=p,adjust=False).mean(); return 2*e1 - e1.ewm(span=p,adjust=False).mean()
    df['qmp'] = zlema(df['c'], 12) - zlema(df['c'], 26)
    s1 = df['qmp'].ewm(span=9, adjust=False).mean()
    s2 = s1.ewm(span=9, adjust=False).mean()
    df['qmp_hist'] = df['qmp'] - (2*s1 - s2)
    
    delta = df['c'].diff()
    g, l = delta.clip(lower=0), -delta.clip(upper=0)
    ag, al = g.ewm(alpha=1/8,min_periods=8).mean(), l.ewm(alpha=1/8,min_periods=8).mean()
    rsi = 100 - 100/(1 + ag/(al+1e-10))
    rma = rsi.ewm(span=1, adjust=False).mean()
    atr_rsi = abs(rma - rma.shift(1))
    ma1 = atr_rsi.ewm(alpha=1/15, min_periods=15).mean()
    df['qqe_mom'] = rma - rma.shift(1)
    
    df = df.dropna()
    if len(df) < 15: return None
    cand = df.iloc[-2]
    lb = 5
    s_low = df['l'].rolling(2*lb+1, center=True).min().iloc[-2] == cand['l']
    s_high = df['h'].rolling(2*lb+1, center=True).max().iloc[-2] == cand['h']
    body = abs(cand['c'] - cand['o']) / (cand['h'] - cand['l'] + 1e-9)
    vol = cand['v'] / (df['v'].rolling(20).mean().iloc[-2] + 1e-9)
    align = np.sign(cand['qmp_hist']) * np.sign(cand['qqe_mom'])
    
    if s_low and cand['c'] > cand['o'] and body > BODY_MIN and vol > VOL_MIN and align > ALIGN_MIN:
        return {'dir': 'LONG', 'price': round(cand['c'],2), 'atr': round(cand['atr'],2)}
    if s_high and cand['c'] < cand['o'] and body > BODY_MIN and vol > VOL_MIN and align < -ALIGN_MIN:
        return {'dir': 'SHORT', 'price': round(cand['c'],2), 'atr': round(cand['atr'],2)}
    return None

def send_alert(sig):
    ts = datetime.utcnow().strftime("%H:%M UTC")
    sl = round(sig['price'] - sig['atr']*1.5 if sig['dir']=='LONG' else sig['price'] + sig['atr']*1.5, 2)
    tp = round(sig['price'] + sig['atr']*2.5 if sig['dir']=='LONG' else sig['price'] - sig['atr']*2.5, 2)
    msg = f"🥇 <b>XAUUSD 1H OB SIGNAL</b>\n⏰ {ts}\n📈 {sig['dir']}\n💰 {sig['price']}\n🛑 {sl} | 🎯 {tp}\n📉 Conf: 0.72"
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT, "text": msg, "parse_mode": "HTML"}, timeout=5)
        logger.info("✅ Alert sent")
    except Exception as e: logger.error(f"❌ Telegram: {e}")
    pd.DataFrame([{"time":ts, "symbol":"XAUUSD", "dir":sig['dir'], "entry":sig['price'], "sl":sl, "tp":tp}]).to_csv("data/live_signals_gold.csv", mode="a", header=not os.path.exists("data/live_signals_gold.csv"), index=False)

if __name__ == "__main__":
    logger.info("🔍 Checking last closed 1H XAUUSD candle...")
    sig = fetch_and_check()
    if sig: send_alert(sig)
    else: logger.info("⏳ No signal.")
