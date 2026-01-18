from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import random
import io
import numpy as np

app = FastAPI(title="TradeVision AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def detect_trend(image: Image.Image):
    gray = image.convert("L")
    arr = np.array(gray)
    avg_brightness = arr.mean()

    if avg_brightness > 127:
        return "BUY"
    else:
        return "SELL"

def generate_trade(signal):
    entry_price = round(random.uniform(1.1000, 1.3000), 4)
    risk = 0.0010
    reward = risk * 2

    if signal == "BUY":
        sl = round(entry_price - risk, 4)
        tp = round(entry_price + reward, 4)
    else:
        sl = round(entry_price + risk, 4)
        tp = round(entry_price - reward, 4)

    return entry_price, sl, tp

@app.post("/analyze-chart/")
async def analyze_chart(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))

    signal = detect_trend(image)
    entry, sl, tp = generate_trade(signal)

    return {
        "signal": signal,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "risk_reward": "1:2",
        "due_time": "Intraday",
        "confidence": f"{random.randint(65, 80)}%"
    }
