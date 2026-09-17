import threading, time, requests, os
from flask import Flask
import yfinance as yf
import pandas as pd

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg}, timeout=10)
        print(f"INVIATO: {msg}", flush=True)
    except Exception as e:
        print(f"ERRORE TELEGRAM: {e}", flush=True)

def check_pair(symbol):
    try:
        data = yf.download(symbol+"=X", period="1d", interval="5m", progress=False)
        if len(data) < 50: return None
        # RSI semplice
        delta = data['Close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        rs = gain/loss
        rsi = 100 - (100/(1+rs))
        last_rsi = float(rsi.iloc[-1])
        price = float(data['Close'].iloc[-1])
        print(f"CHECK {symbol} RSI={last_rsi:.1f} PRICE={price}", flush=True)
        if last_rsi > 60:
            return f"🟢 BUY SICURO {symbol} RSI {last_rsi:.1f} PRICE {price:.5f}"
        if last_rsi < 40:
            return f"🔴 SELL SICURO {symbol} RSI {last_rsi:.1f} PRICE {price:.5f}"
        return None
    except Exception as e:
        print(f"ERRORE {symbol}: {e}", flush=True)
        return None

def run_bot():
    print("MOTORE AVVIATO...", flush=True)
    send_telegram("V9.3.1 ONLINE - MOTORE FIX")
    pairs = ["EURUSD","GBPUSD","USDJPY","EURGBP","EURJPY","GBPJPY","AUDUSD","USDCHF"]
    while True:
        try:
            print("--- NUOVA SCANSIONE ---", flush=True)
            for p in pairs:
                signal = check_pair(p)
                if signal:
                    send_telegram(signal)
                    print("ATTESA 15 MIN DOPO SEGNALE", flush=True)
                    time.sleep(900) # 15 min
                    break
            time.sleep(60)
        except Exception as e:
            print(f"ERRORE LOOP: {e}", flush=True)
            time.sleep(30)

@app.route("/")
def home():
    return "V9.3.1 ONLINE - MOTORE FIX"

# AVVIO THREAD
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
