import os, requests, yfinance as yf
from flask import Flask
import threading, time
from datetime import datetime

TOKEN = os.getenv("TOKEN", "8460061494:AAEe7k1uZBO6Y4rnBy9YQ4D7x8N0qD9gGq9g")
CHAT_ID = os.getenv("CHAT_ID", "6145829174")

PAIRS = {
"EURUSD=X": "EUR/USD",
"GBPUSD=X": "GBP/USD",
"USDJPY=X": "USD/JPY",
"USDCHF=X": "USD/CHF",
"AUDUSD=X": "AUD/USD",
"NZDUSD=X": "NZD/USD",
"EURGBP=X": "EUR/GBP",
"EURJPY=X": "EUR/JPY",
"GBPJPY=X": "GBP/JPY",
"AUDJPY=X": "AUD/JPY",
"USDCAD=X": "USD/CAD",
"EURCAD=X": "EUR/CAD",
"CADJPY=X": "CAD/JPY",
"CHFJPY=X": "CHF/JPY",
"EURAUD=X": "EUR/AUD",
"GBPCHF=X": "GBP/CHF",
"GBPCAD=X": "GBP/CAD",
"AUDCAD=X": "AUD/CAD",
"AUDCHF=X": "AUD/CHF",
"NZDJPY=X": "NZD/JPY",
"GC=F": "GOLD",
"SI=F": "SILVER"
}

app = Flask(__name__)

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def check():
    for sym, name in PAIRS.items():
        try:
            df = yf.download(sym, period="2d", interval="1m", progress=False)
            if len(df) < 20: continue
            close = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            if close > prev:
                send(f"BUY SIGNAL - {name} - {close}")
            elif close < prev:
                send(f"SELL SIGNAL - {name} - {close}")
        except: continue

def loop():
    send("BOT V15.2 AVVIATO - Solo segnali buoni")
    while True:
        check()
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

@app.route("/")
def home():
    return "BOT V15.2 LIVE"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
