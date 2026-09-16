import yfinance as yf
import pandas as pd
import time
import threading
import requests
import os
from flask import Flask

# CONFIG SICURA
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print(f"--- AVVIO BOT --- TOKEN presente: {bool(TOKEN)} CHAT_ID: {CHAT_ID}")

COPPIE = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "EURCAD=X", "USDCHF=X", "AUDUSD=X", "EURGBP=X"]

app = Flask(__name__)

@app.route('/')
def home():
    return "V2.6 ANTI-SPAM ATTIVO - Bot online!"

last_sent = {}

def send_telegram(msg):
    try:
        if not TOKEN or not CHAT_ID:
            print("ERRORE: TOKEN o CHAT_ID mancanti!")
            return
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print(f"Telegram inviato: {msg} -> {r.status_code}")
    except Exception as e:
        print(f"Errore invio telegram: {e}")

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
        now = time.time()
        if pair in last_sent and (now - last_sent[pair]) < 2700:
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
    print("Bot loop avviato - controllo candele...")
    send_telegram("✅ DjovidoBot V2.6 ONLINE - Anti-spam 45min attivo!")
    while True:
        for coppia in COPPIE:
            msg = check_candles(coppia)
            if msg:
                send_telegram(msg)
        time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
