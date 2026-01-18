from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import numpy as np
import random

app = FastAPI(title="TradeVision AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- TIMEFRAME DETECTION --------
def detect_timeframe(image):
    gray = image.convert("L")
    arr = np.array(gray)

    height = arr.shape[0]
    edges = np.abs(np.diff(arr, axis=0)).mean()

    if edges > 40:
        return "M5–M15"
    elif edges > 25:
        return "M30–H1"
    else:
        return "H4–D1"

# -------- TREND --------
def detect_trend(image):
    gray = image.convert("L")
    arr = np.array(gray)
    return "BUY" if arr.mean() > 127 else "SELL"

# -------- CANDLE BIAS --------
def candle_bias(image):
    gray = image.convert("L")
    arr = np.array(gray)

    top = arr[:arr.shape[0]//2].mean()
    bottom = arr[arr.shape[0]//2:].mean()

    return "BUY" if bottom > top else "SELL"

# -------- STRUCTURE --------
def detect_structure(trend, candle):
    return "BOS" if trend == candle else "CHoCH"

# -------- SL/TP SCALING --------
def risk_by_timeframe(tf):
    if tf == "M5–M15":
        return 0.0006
    elif tf == "M30–H1":
        return 0.0012
    else:
        return 0.0030

# -------- TRADE --------
def generate_trade(signal, tf):
    entry = round(random.uniform(1.1000, 1.3000), 4)
    risk = risk_by_timeframe(tf)
    reward = risk * 2

    if signal == "BUY":
        sl = round(entry - risk, 4)
        tp = round(entry + reward, 4)
    else:
        sl = round(entry + risk, 4)
        tp = round(entry - reward, 4)

    return entry, sl, tp

# -------- STABLE CONFIDENCE --------
def confidence_engine(trend, candle, structure, tf):
    score = 55

    if trend == candle:
        score += 8

    if structure == "BOS":
        score += 10
    else:
        score -= 5

    if tf in ["M30–H1", "H4–D1"]:
        score += 5  # higher TF = more reliable

    return min(max(score, 55), 82)

@app.post("/analyze-chart/")
async def analyze_chart(file: UploadFile = File(...)):
    image = Image.open(io.BytesIO(await file.read()))

    tf = detect_timeframe(image)
    trend = detect_trend(image)
    candle = candle_bias(image)
    structure = detect_structure(trend, candle)

    signal = trend if structure == "BOS" else candle
    entry, sl, tp = generate_trade(signal, tf)
    confidence = confidence_engine(trend, candle, structure, tf)

    due_time = {
        "M5–M15": "5–30 minutes",
        "M30–H1": "1–6 hours",
        "H4–D1": "1–5 days"
    }[tf]

    return {
        "signal": signal,
        "timeframe": tf,
        "market_structure": structure,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "risk_reward": "1:2",
        "due_time": due_time,
        "confidence": f"{confidence}%"
    }
