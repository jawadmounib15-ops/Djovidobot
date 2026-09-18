import os, requests, yfinance as yf
import pandas as pd
from flask import Flask
import threading, time
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = {
"EURUSD=X": "EUR/USD",
"GBPUSD=X": "GBP/USD", 
"USDJPY=X": "USD/JPY",
"EURJPY=X": "EUR/JPY",
"GBPJPY=X": "GBP/JPY",
"GC=F": "GOLD",
"SI=F": "SILVER"
}

app = Flask(__name__)
last_status = 0

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=15)
    except Exception as e:
        print(e)

def rsi_calc(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_signal():
    global last_status
    now_hour = datetime.now().hour
    if now_hour >= 23 or now_hour < 5:
        return

    found = 0
    for sym, name in PAIRS.items():
        try:
            df = yf.download(sym, period="5d", interval="15m", progress=False)
            if len(df) < 60: continue
            close = df['Close']
            rsi = rsi_calc(close).iloc[-1]
            ema20 = close.ewm(span=20).mean().iloc[-1]
            ema50 = close.ewm(span=50).mean().iloc[-1]
            price = float(close.iloc[-1])
            ratio = abs(ema20 - ema50) / price * 1000
            
            if rsi < 38 and ema20 > ema50 and ratio > 0.20:
                send(f"🔥 <b>{name} BUY</b>\nRatio {round(ratio,2)} RSI {round(rsi,1)}\nV15.6")
                found += 1
            elif rsi > 62 and ema20 < ema50 and ratio > 0.20:
                send(f"🔥 <b>{name} SELL</b>\nRatio {round(ratio,2)} RSI {round(rsi,1)}\nV15.6")
                found += 1
        except: continue
    
    # se dopo 30 min zero segnali, ti avvisa che è vivo
    if found == 0 and time.time() - last_status > 1800:
        send(f"⏳ Bot vivo, mercato lento\nControllo... nessun segnale V.I.P. per ora\nV15.6 attiva - Pausa 23h-05h")
        last_status = time.time()

def loop():
    time.sleep(5)
    send("✅ <b>BOT V15.6 AVVIATO</b>\n- RSI 38/62 STRETTA\n- Ratio >0.20 (per stasera)\n- Pausa 23h-05h")
    global last_status
    last_status = time.time()
    while True:
        check_signal()
        time.sleep(180)

threading.Thread(target=loop, daemon=True).start()

@app.route("/")
def home():
    return "BOT V15.6 LIVE - Ratio 0.20"

if __name__ == "__main__":
    app.run(host="0.0.0.0",  port=10000)
