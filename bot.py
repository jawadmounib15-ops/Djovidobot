import yfinance as yf
import pandas as pd
import time
import threading
import requests
import os
from flask import Flask

# CONFIG SICURA - niente token scritti!
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

COPPIE = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "EURCAD=X", "USDCHF=X", "AUDUSD=X", "EURGBP=X"]

app = Flask(__name__)

@app.route('/')
def home():
    return "V2.6 ANTI-SPAM ATTIVO"

last_sent = {} # <--- ANTI SPAM 45 min

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def check_candles(pair):
    try:
        df = yf.download(pair, period="2d", interval="5m", progress=False, auto_adjust=True)
        if len(df) < 55:
            return None

        df['EMA50'] = df['Close'].ewm(span=50).mean()
        c = df.iloc[-1]
        prev = df.iloc[-2]

        close = float(c['Close'])
        ema = float(c['EMA50'])
        prev_close = float(prev['Close'])

        # Filtro anti-spam
        now = time.time()
        if pair in last_sent and (now - last_sent[pair]) < 2700: # 45 minuti
            return None

        signal = None
        if prev_close < ema and close > ema:
            signal = f"🟢 BUY {pair.replace('=X','')} @ {close:.5f}"
        elif prev_close > ema and close < ema:
            signal = f"🔴 SELL {pair.replace('=X','')} @ {close:.5f}"

        if signal:
            last_sent[pair] = now
            return signal

    except Exception as e:
        print(f"Errore {pair}: {e}")
    return None

def bot_loop():
    while True:
        for coppia in COPPIE:
            msg = check_candles(coppia)
            if msg:
                send_telegram(msg)
        time.sleep(60)

# Avvia bot in background
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
