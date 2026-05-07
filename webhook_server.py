from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import os

app = FastAPI(title="OB Predictor Webhook", version="1.0")

# Validated thresholds (auto-updated by tuner)
BODY_RATIO_MIN = 0.6
VOL_RATIO_MIN = 1.2
ALIGNMENT_MIN = 0.6
STOP_ATR_MULT = 1.5
TARGET_ATR_MULT = 2.5

class TVPayload(BaseModel):
    symbol: str
    timeframe: str
    close: float
    open: float
    high: float
    low: float
    volume: float
    atr: float
    qmp_histogram: float
    qqe_momentum: float
    ob_formed: bool = False
    ob_direction: str = "none"

@app.get("/health")
def health():
    return {"status": "ok", "service": "ob-predictor", "timestamp": str(datetime.utcnow())}

@app.post("/webhook")
async def receive_signal(payload: TVPayload, authorization: str = Header(None)):
    if authorization != "Bearer test_token_123":
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Calculate entry quality & signal alignment
    body_ratio = abs(payload.close - payload.open) / (payload.high - payload.low + 1e-9)
    vol_ratio = payload.volume / max(1.0, 1.0)  # Placeholder; real TV volume normalization handled in Pine
    alignment = np.sign(payload.qmp_histogram) * np.sign(payload.qqe_momentum)
    entry_quality = body_ratio * vol_ratio / 1.5
    
    # Decision Logic (Validated Thresholds)
    signal = "HOLD"
    confidence = 0.0
    direction = "none"
    
    if payload.ob_formed and entry_quality > (BODY_RATIO_MIN * VOL_RATIO_MIN / 1.5) and abs(alignment) > ALIGNMENT_MIN:
        if payload.ob_direction == "bull" and payload.qmp_histogram > 0:
            direction, signal, confidence = "long", "ENTER_LONG", 0.72
        elif payload.ob_direction == "bear" and payload.qmp_histogram < 0:
            direction, signal, confidence = "short", "ENTER_SHORT", 0.72
    
    # Log to CSV
    log_path = "data/live_signals.csv"
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": payload.symbol,
        "price": payload.close,
        "signal": signal,
        "direction": direction,
        "confidence": confidence,
        "atr": payload.atr,
        "stop_loss": round(payload.close - payload.atr * STOP_ATR_MULT if direction=="long" else payload.close + payload.atr * STOP_ATR_MULT, 4),
        "take_profit": round(payload.close + payload.atr * TARGET_ATR_MULT if direction=="long" else payload.close - payload.atr * TARGET_ATR_MULT, 4)
    }
    
    df = pd.DataFrame([log_data])
    if not os.path.exists(log_path):
        df.to_csv(log_path, index=False)
    else:
        df.to_csv(log_path, mode='a', header=False, index=False)
        
    logger.info(f"📥 {payload.symbol} | {signal} | Conf:{confidence:.2f} | SL:{log_data['stop_loss']} | TP:{log_data['take_profit']}")
    
    return {"status": "processed", "signal": signal, "direction": direction, "confidence": confidence, "sl": log_data["stop_loss"], "tp": log_data["take_profit"]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
