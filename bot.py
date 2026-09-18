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
"USDCHF=X": "USD/CHF",
"AUDUSD=X": "AUD/USD",
"EURJPY=X": "EUR/JPY",
"GBPJPY=X": "GBP/JPY",
"GC=F": "GOLD"
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
    now_hour = datetime.now().hour
    if now_hour >= 23 or now_hour < 5:
        print(f"Pausa {now_hour}:00 - 23h-05h")
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
            up_trend = ema20 > ema50
            down_trend = ema20 < ema50
            ratio = round(abs(ema20 - ema50) / price * 1000, 2)

            # V15.5 STRETTA - poco meno di V15.4
            if rsi < 38 and up_trend and ratio > 0.35:
                send(f"🔥 <b>{name} BUY</b>\nRatio {ratio} RSI {round(rsi,1)}\nEMA UP ✅\nV15.5 STRETTA")
            elif rsi > 62 and down_trend and ratio > 0.35:
                send(f"🔥 <b>{name} SELL</b>\nRatio {ratio} RSI {round(rsi,1)}\nEMA DOWN ✅\nV15.5 STRETTA")
        except: continue

def loop():
    time.sleep(5)
    send("✅ <b>BOT V15.5 STRETTA AVVIATO</b>\n- RSI 38/62\n- Ratio >0.35\n- Pausa 23h-05h\nObiettivo 90% WIN")
    while True:
        check_signal()
        time.sleep(240)

threading.Thread(target=loop, daemon=True).start()

@app.route("/")
def home():
    return "BOT V15.5 STRETTA LIVE"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
