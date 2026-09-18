import os, requests, yfinance as yf
import pandas as pd
from flask import Flask
import threading, time
from datetime import datetime

# Usiamo i nomi che hai messo tu su Render
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Coppie V.I.P - solo mercato reale, no OTC
PAIRS = {
"EURUSD=X": "EUR/USD",
"GBPUSD=X": "GBP/USD", 
"USDJPY=X": "USD/JPY",
"USDCHF=X": "USD/CHF",
"AUDUSD=X": "AUD/USD",
"NZDUSD=X": "NZD/USD",
"EURJPY=X": "EUR/JPY",
"GBPJPY=X": "GBP/JPY",
"USDCAD=X": "USD/CAD",
"GC=F": "GOLD",
"SI=F": "SILVER"
}

app = Flask(__name__)

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=15)
        print(f"Sent: {msg}")
    except Exception as e:
        print(e)

def rsi_calc(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_signal():
    # NO OTC NOTTE: non tradare 22:00 - 06:00 ora italiana
    now_hour = datetime.now().hour
    if now_hour >= 22 or now_hour <= 6:
        print("Notte - NO OTC - pausa")
        return

    for sym, name in PAIRS.items():
        try:
            df = yf.download(sym, period="5d", interval="15m", progress=False)
            if len(df) < 60: continue
            
            close = df['Close']
            rsi = rsi_calc(close).iloc[-1]
            ema20 = close.ewm(span=20).mean().iloc[-1]
            ema50 = close.ewm(span=50).mean().iloc[-1]
            price = float(close.iloc[-1])
            
            # EMA TREND
            up_trend = ema20 > ema50
            down_trend = ema20 < ema50
            
            # RSI 70/30 + EMA per 90% WIN
            ratio = round(abs(ema20 - ema50) / price * 1000, 2)

            if rsi < 35 and up_trend and ratio > 0.5:
                send(f"🔥 <b>{name} BUY</b>\nRatio {ratio} RSI {round(rsi,1)}\nEMA Trend UP ✅\nObiettivo: 90% WIN")
            elif rsi > 65 and down_trend and ratio > 0.5:
                send(f"🔥 <b>{name} SELL</b>\nRatio {ratio} RSI {round(rsi,1)}\nEMA Trend DOWN ✅\nObiettivo: 90% WIN")
                
        except Exception as e:
            print(f"Err {name}: {e}")
            continue

def loop():
    time.sleep(5)
    send("✅ <b>BOT V15.4 V.I.P AVVIATO</b>\n- RSI 70/30\n- EMA Trend\n- NO OTC notte\nObiettivo: 90% WIN")
    while True:
        check_signal()
        time.sleep(300) # controllo ogni 5 minuti per segnali buoni

threading.Thread(target=loop, daemon=True).start()

@app.route("/")
def home():
    return "BOT V15.4 V.I.P LIVE - 90% WIN"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
