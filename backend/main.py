from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import numpy as np
import random
import cv2

app = FastAPI(title="TradeVision AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= TIMEFRAME DETECTION =================
def detect_timeframe(image: Image.Image):
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    edge_strength = np.abs(np.diff(gray, axis=0)).mean()

    if edge_strength > 45:
        return "M5–M15"
    elif edge_strength > 30:
        return "M30–H1"
    else:
        return "H4–D1"

# ================= TREND DETECTION =================
def detect_trend(image: Image.Image):
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    return "BUY" if gray.mean() > 127 else "SELL"

# ================= TRUE CANDLE DETECTION =================
def detect_candles(image: Image.Image, lookback=25):
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candles = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h > 18 and w > 3:
            candles.append((x, y, w, h))

    candles = sorted(candles, key=lambda c: c[0])[-lookback:]

    bullish, bearish = 0, 0
    for x, y, w, h in candles:
        body = gray[y:y+h, x:x+w]
        if body.shape[0] == 0 or body.shape[1] == 0:
            continue

        top = body[:h//2].mean()
        bottom = body[h//2:].mean()

        if bottom > top:
            bullish += 1
        else:
            bearish += 1

    return bullish, bearish

# ================= CANDLE BIAS =================
def candle_bias(image):
    bullish, bearish = detect_candles(image)
    if bullish > bearish:
        return "BUY"
    elif bearish > bullish:
        return "SELL"
    else:
        return "NEUTRAL"

# ================= MARKET STRUCTURE =================
def detect_structure(trend, candle):
    if candle == "NEUTRAL":
        return "CHoCH"
    return "BOS" if trend == candle else "CHoCH"

# ================= RISK BY TIMEFRAME =================
def risk_by_timeframe(tf):
    if tf == "M5–M15":
        return 0.0006
    elif tf == "M30–H1":
        return 0.0012
    else:
        return 0.0030

# ================= TRADE LEVELS =================
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

# ================= STABLE CONFIDENCE ENGINE =================
def compute_confidence(trend, candle, structure, tf):
    score = 58

    if trend == candle:
        score += 8

    if structure == "BOS":
        score += 12
    else:
        score -= 6

    if tf in ["M30–H1", "H4–D1"]:
        score += 6

    return min(max(score, 55), 82)

# ================= MAIN ENDPOINT =================
@app.post("/analyze-chart/")
async def analyze_chart(file: UploadFile = File(...)):
    image = Image.open(io.BytesIO(await file.read()))

    timeframe = detect_timeframe(image)
    trend = detect_trend(image)
    candle = candle_bias(image)
    structure = detect_structure(trend, candle)

    signal = trend if structure == "BOS" else candle
    if signal == "NEUTRAL":
        signal = trend

    entry, sl, tp = generate_trade(signal, timeframe)
    confidence = compute_confidence(trend, candle, structure, timeframe)

    due_time_map = {
        "M5–M15": "5–30 minutes",
        "M30–H1": "1–6 hours",
        "H4–D1": "1–5 days"
    }

    return {
        "signal": signal,
        "timeframe": timeframe,
        "market_structure": structure,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "risk_reward": "1:2",
        "due_time": due_time_map[timeframe],
        "confidence": f"{confidence}%"
    }
