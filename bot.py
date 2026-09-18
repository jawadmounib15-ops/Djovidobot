import os, requests, yfinance as yf
from flask import Flask
import threading, time

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = {
"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
"USDCHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD", "NZDUSD=X": "NZD/USD",
"GC=F": "GOLD", "SI=F": "SILVER"
}

app = Flask(__name__)

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=15)
        print(f"Sent: {msg}")
    except Exception as e:
        print(e)

def loop():
    time.sleep(5)
    send("BOT V15.3 AVVIATO - Fix TELEGRAM_TOKEN OK")
    while True:
        time.sleep(120)

threading.Thread(target=loop, daemon=True).start()

@app.route("/")
def home():
    return "BOT V15.3 LIVE - TELEGRAM_TOKEN FIX"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
