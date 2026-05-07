import requests
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime
from loguru import logger

# 🔑 REPLACE# 📱 Option A: Live Python Alert System (Free + Phone Optimized)

We'll bypass TradingView webhooks completely. Python will fetch live market data, apply your **validated thresholds**, and send **real-time alerts directly to your phone** via Telegram.

Follow these exact steps. Takes ~5 minutes total.

---

## 🤖 STEP 1: Create Free Telegram Bot (2 mins on Phone)
1. Open Telegram app → Search `@BotFather` → Tap `Start`
2. Send: `/newbot`
3. Reply with a name: `OB Predictor Bot`
4. Reply with a username: `ob_predictor_xxx_bot` (must end in `bot`)
5. BotFather replies with a **TOKEN** (looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`)
   - 🔒 **Copy this token. Never share it.**
6. Search your new bot → Tap `Start`
7. Send `/myid` to `@userinfobot` → Copy your **CHAT ID** (looks like: `987654321`)

✅ You now have: `BOT_TOKEN` + `CHAT_ID`

---

## 📦 STEP 2: Deploy Live Signal Script
In your Codespace terminal, run this **entire block**:
```bash
cat > live_alert_system.py << 'PYEOF'
import requests, pandas as pd, numpy as np, time, os
from datetime import datetime, timezone
from loguru import logger

# ================= CONFIG =================
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
TELEGRAM_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "PASTE_YOUR_CHAT_ID_HERE"

# Validated Thresholds (from tuner)
BODY_MIN = 0.6
VOL_MIN = 1.2
ALIGN_MIN = 0.6
STOP_MULT = 1.5
TARGET_MULT = 2.5
CHECK_INTERVAL_SEC = 30  # Poll frequency

logger.info(f"🚀 OB Live Alert System Starting | {SYMBOL} {INTERVAL}")
logger.info(f"📡 Thresholds: body>{BODY_MIN} | vol>{VOL_MIN} | |align|>{ALIGN_MIN}")

# ================= CORE FUNCTIONS =================
def fetch_ohlcv(symbol, interval, limit=50):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data, columns=["open_time","o","h","l","c","v","close_time","quote_v","trades","taker_buy","taker_quote","ignore"])
    df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    return df[["o","h","l","c","v"]]

def calc_indicators(df):
    df = df.copy()
    df["atr"] = (df["h"] - df["l"]).rolling(14).mean()
    
    # QMP (Zero-Lag MACD)
    def zlema(s, l): e1=s.ewm(span=l).mean(); return 2*e1 - e1.ewm(span=l).mean()
    fast, slow = zlema(df["c"], 12), zlema(df["c"], 26)
    df["qmp_macd"] = fast - slow
    sig1 = df["qmp_macd"].ewm(span=9).mean()
    sig2 = sig1.ewm(span=9).mean()
    df["qmp_line"] = 2*sig1 - sig2
    df["qmp_hist"] = df["qmp_macd"] - df["qmp_line"]
    
    # QQE
    delta = df["c"].diff()
    gain = delta.clip(lower=0).ewm(span=8).mean()
    loss = (-delta.clip(upper=0)).ewm(span=8).mean()
    rs = gain / (loss + 1e-10)
    df["qqe_rsi"] = 100 - 100/(1+rs)
    df["qqe_rsi_ma"] = df["qqe_rsi"].ewm(span=1).mean()
    wilders = 8*2-1
    atr_rsi = (df["qqe_rsi_ma"] - df["qqe_rsi_ma"].shift(1)).abs()
    ma_atr = atr_rsi.ewm(alpha=1/wilders).mean()
    df["qqe_dar"] = ma_atr.ewm(alpha=1/wilders).mean() * 3.0
    df["qqe_mom"] = df["qqe_rsi_ma"] - df["qqe_rsi_ma"].shift(1)
    
    # OB Detection (Latest closed candle)
    last = df.iloc[-1]
    swing_low = df["l"].rolling(11, center=True).min().iloc[-2] == last["l"]
    swing_high = df["h"].rolling(11, center=True).max().iloc[-2] == last["h"]
    
    body = abs(last["c"] - last["o"]) / (last["h"] - last["l"] + 1e-9)
    vol = last["v"] / df["v"].rolling(20).mean().iloc[-2]
    
    ob_formed = False
    ob_dir = "none"
    if swing_low and last["c"] > last["o"] and body > BODY_MIN and vol > VOL_MIN:
        ob_formed, ob_dir = True, "bull"
    elif swing_high and last["c"] < last["o"] and body > BODY_MIN and vol > VOL_MIN:
        ob_formed, ob_dir = True, "bear"
        
    align = np.sign(df["qmp_hist"].iloc[-2]) * np.sign(df["qqe_mom"].iloc[-2])
    return ob_formed, ob_dir, align, last, df["atr"].iloc[-2]

def send_telegram(msg):
    url = f"https://api.telegram.org/b# 📡 Option A: Live Python Signal Monitor + Telegram Alerts
This bypasses TradingView entirely. Python fetches live 15m data, runs your **validated OB+QMP/QQE rules**, and sends instant alerts to your phone. 100% free, runs in Codespaces, zero paywalls.

---

## 📱 STEP 1: Create Telegram Bot (30 seconds)
1. Open Telegram → Search `@BotFather` → Tap `Start`
2. Send: `/newbot`
3. Follow prompts:
   - Name: `OB Signal Monitor`
   - Username: `ob_monitor_123_bot` (must end in `bot`)
4. Copy the **BOT TOKEN** (looks like: `123456:ABC-DEF1234...`)
5. Search your new bot in Telegram → Tap `Start`
6. Open this link in your browser: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
7. Find `"id": 123456789` → That's your **CHAT_ID**

✅ Keep both values handy.

---

## 🐍 STEP 2: Deploy Live Monitor (Copy-Paste Entire Block)
```bash
cat > live_monitor.py << 'PYEOF'
import requests, pandas as pd, numpy as np, time, os, json
from datetime import datetime
from loguru import logger

# === CONFIGURATION ===
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
CHECK_INTERVAL = 60  # seconds
TELEGRAM_TOKEN = "REPLACE_WITH_YOUR_BOT_TOKEN"
TELEGRAM_CHAT = "REPLACE_WITH_YOUR_CHAT_ID"

# Validated thresholds
BODY_MIN = 0.6
VOL_MIN = 1.2
ALIGN_MIN = 0.6

def fetch_data():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=50"
    resp = requests.get(url, timeout=10).json()
    df = pd.DataFrame(resp, columns=['ts','o','h','l','c','v','ct','qv','tr','tb','tq','ig'])
    df[['o','h','l','c','v']] = df[['o','h','l','c','v']].astype(float)
    df['datetime'] = pd.to_datetime(df['ts'], unit='ms')
    return df

def calc_indicators(df):
    df['atr'] = (df['h'] - df['l']).rolling(14).mean()
    def zlema(s, p):
        e1 = s.ewm(span=p, adjust=False).mean()
        e2 = e1.ewm(span=p, adjust=False).mean()
        return 2*e1 - e2
    df['qmp'] = zlema(df['c'], 12) - zlema(df['c'], 26)
    s1 = df['qmp'].ewm(span=9, adjust=False).mean()
    s2 = s1.ewm(span=9, adjust=False).mean()
    df['qmp_line'] = 2*s1 - s2
    df['qmp_hist'] = df['qmp'] - df['qmp_line']
    # QQE
    delta = df['c'].diff()
    g = delta.clip(lower=0); l = -delta.clip(upper=0)
    ag = g.ewm(alpha=1/8, min_periods=8).mean()
    al = l.ewm(alpha=1/8, min_periods=8).mean()
    rsi = 100 - 100/(1 + ag/(al+1e-10))
    rma = rsi.ewm(span=1, adjust=False).mean()
    atr_rsi = abs(rma - rma.shift(1))
    ma1 = atr_rsi.ewm(alpha=1/15, min_periods=15).mean()
    dar = ma1.ewm(alpha=1/15, min_periods=15).mean() * 3.0
    df['qqe_mom'] = rma - rma.shift(1)
    return df.dropna()

def check_signal(df, last_ts):
    if len(df) < 15: return None, last_ts
    cand = df.iloc[-2]  # Last CLOSED candle
    if cand['ts'] == last_ts: return None, last_ts  # Already checked
    last_ts = cand['ts']
    
    lookback = 5
    swing_low = df['l'].rolling(2*lookback+1, center=True).min().iloc[-2] == cand['l']
    swing_high = df['h'].rolling(2*lookback+1, center=True).max().iloc[-2] == cand['h']
    
    body = abs(cand['c'] - cand['o']) / (cand['h'] - cand['l'] + 1e-9)
    vol_ma = df['v'].rolling(20).mean().iloc[-2]
    vol = cand['v'] / (vol_ma + 1e-9)
    align = np.sign(cand['qmp_hist']) * np.sign(cand['qqe_mom'])
    
    if swing_low and cand['c'] > cand['o'] and body > BODY_MIN and vol > VOL_MIN and align > ALIGN_MIN:
        return {'dir': 'LONG', 'price': cand['c'], 'atr': cand['atr'], 'conf': 0.72}, last_ts
    if swing_high and cand['c'] < cand['o'] and body > BODY_MIN and vol > VOL_MIN and align < -ALIGN_MIN:
        return {'dir': 'SHORT', 'price': cand['c'], 'atr': cand['atr'], 'conf': 0.72}, last_ts
    return None, last_ts

def send_alert(sig):
    ts = datetime.now().strftime("%H:%M %Z")
    sl = round(sig['price'] - sig['atr']*1.5 if sig['dir']=='LONG' else sig['price'] + sig['atr']*1.5, 2)
    tp = round(sig['price'] + sig['atr']*2.5 if sig['dir']=='LONG' else sig['price'] - sig['atr']*2.5, 2)
    msg = f"🚨 <b>OB SIGNAL</b>\n📊 {SYMBOL} ({INTERVAL})\n⏰ {ts}\n📈 {sig['dir']}\n💰 {sig['price']}\n🛑 {sl} | 🎯 {tp}\n📉 Conf: {sig['conf']}"
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}, timeout=5)
        logger.info("✅ Telegram alert sent")
    except Exception as e:
        logger.error(f"❌ Telegram failed: {e}")
    
    # Log to CSV
    log_path = "data/live_signals.csv"
    row = [{"time":ts, "symbol":SYMBOL, "dir":sig['dir'], "entry":sig['price'], "sl":sl, "tp":tp, "conf":sig['conf']}]
    pd.DataFrame(row).to_csv(log_path, mode="a", header=not os.path.exists(log_path), index=False)

def main():
    logger.info(f"🚀 Live OB Monitor: {SYMBOL} {INTERVAL} | Check every {CHECK_INTERVAL}s")
    logger.info("⏳ Warming up indicators (2-3 mins)...")
    time.sleep(180)  # Let indicators stabilize
    last_ts = 0
    while True:
        try:
            df = fetch_data()
            df = calc_indicators(df)
            sig, last_ts = check_signal(df, last_ts)
            if sig:
                send_alert(sig)
            else:
                logger.debug("⏳ Monitoring...")
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"🔄 Loop error: {e}. Retrying in 30s...")
            time.sleep(30)

if __name__ == "__main__":
    # Replace placeholders
    import re
    script = open("live_monitor.py").read()
    script = script.replace("REPLACE_WITH_YOUR_BOT_TOKEN", TELEGRAM_TOKEN)
    script = script.replace("REPLACE_WITH_YOUR_CHAT_ID", TELEGRAM_CHAT)
    with open("live_monitor_configured.py", "w") as f: f.write(script)
    logger.info("💾 Config saved. Running...")
    exec(open("live_monitor_configured.py").read())
