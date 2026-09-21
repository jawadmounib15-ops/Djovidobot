import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]

app = Flask(__name__)
@app.route('/')
def home():
    return "DEBUG MODE"

pending=[]

def send(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"SEND ERROR {e}")

def loop():
    send(f"🔍 DEBUG avviato\nTOKEN: {TOKEN[:10]}...\nCHAT: {CHAT_ID}")
    c=0
    while True:
        c+=1
        try:
            df = yf.download("EURUSD=X", period="5d", interval="15m", progress=False)
            if len(df)==0:
                send(f"❌ ERRORE yfinance vuoto! c={c}")
            else:
                price=float(df['Close'].iloc[-1])
                send(f"✅ SCAN {c} OK prezzo EURUSD {price:.5f} - righe {len(df)}")
                # FORZA SEGNALE DI TEST
                if c==2:
                    send(f"🎯 TEST FORZATO BUY EURUSD {price:.5f} - Se vedi questo, il bot funziona!")
        except Exception as e:
            send(f"❌ ECCEZIONE SCAN: {str(e)[:200]}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
