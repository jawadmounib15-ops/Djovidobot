import os
import time
import requests
import yfinance as yf
import threading
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "V77 CONTRARIO 100% LOSS - 8 SEGNALI OGNI 5M"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_flask, daemon=True).start()

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]
WIN = 0
LOSS = 0
PEND = {}
CHECK = 0

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT, "text": m, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

send("💀 *V77 CONTRARIO 100% LOSS ATTIVO*\n📉 8 segnali ogni 5 min\n🔄 Fa l'opposto delle regole")

while True:
    try:
        now = datetime.now()

        # RISULTATI DOPO 5 MIN
        for k in list(PEND.keys()):
            s, p, t = PEND[k]
            if now - t >= timedelta(minutes=5):
                try:
                    df = yf.download(k, period="1d", interval="1m", progress=False)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    c = float(df["Close"].iloc[-1])
                    win = (s == "BUY" and c > p) or (s == "SELL" and c < p)
                    if win:
                        WIN += 1
                        R = "✅ WIN"
                    else:
                        LOSS += 1
                        R = "❌ LOSS"
                    tot = WIN + LOSS
                    wr = WIN / tot * 100 if tot > 0 else 0
                    send(f"{R} *{k.replace('=X','')} {s}*\nEntrata {p:.5f} -> Ora {c:.5f}\n📊 WIN {WIN} LOSS {LOSS} WR {wr:.0f}%")
                    del PEND[k]
                except:
                    pass

        # SEGNALI OGNI 5 MIN - CONTRARIO DELLE REGOLE
        if time.time() - CHECK >= 300:
            CHECK = time.time()
            for pair in PAIRS:
                try:
                    df = yf.download(pair, period="10d", interval="5m", progress=False)
                    if len(df) < 500:
                        continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)

                    e500 = df["Close"].ewm(span=500).mean().iloc[-1]
                    cl = float(df["Close"].iloc[-1])

                    # CONTRARIO PURO - OPPOSTO DELLE REGOLE NORMALI
                    if cl > e500:
                        sig = "SELL" # normale = BUY, noi SELL = LOSS
                    else:
                        sig = "BUY" # normale = SELL, noi BUY = LOSS

                    PEND[pair] = (sig, cl, now)
                    send(f"💀 *5M {sig} {pair.replace('=X','')}*\nEMA500 {e500:.5f}\nPrice {cl:.5f}\n🔄 CONTRARIO")
                except Exception as e:
                    print(e)
                    pass
    except:
        pass
    time.sleep(3)
