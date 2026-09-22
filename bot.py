import os, time, requests, yfinance as yf, threading
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "V68 LARGHISSIMO ESTREMO ATTIVO"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
threading.Thread(target=run_flask, daemon=True).start()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X"]
WIN = 0
LOSS = 0
pending = {}
last_check = 0

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

send("🚀 *V68 LARGHISSIMO ESTREMO ATTIVO*\nSolo Price vs EMA20 - MAX segnali!")

while True:
    try:
        now = datetime.now()
        to_remove = []
        for pair, (signal, entry_price, entry_time) in list(pending.items()):
            if now - entry_time >= timedelta(minutes=5):
                try:
                    df = yf.download(pair, period="1d", interval="1m", progress=False)
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    curr = float(df["Close"].iloc[-1])
                    win = (signal=="BUY" and curr>entry_price) or (signal=="SELL" and curr<entry_price)
                    if win: WIN+=1; res="✅ WIN AUTO"
                    else: LOSS+=1; res="❌ LOSS AUTO"
                    tot=WIN+LOSS; wr=(WIN/tot*100) if tot>0 else 0
                    send(f"{res} *{pair.replace('=X','')} {signal}*\n{entry_price:.5f} -> {curr:.5f}\n📊 WIN {WIN} LOSS {LOSS} WR {wr:.1f}%")
                    to_remove.append(pair)
                except: pass
        for p in to_remove:
            if p in pending: del pending[p]

        if time.time() - last_check > 60:
            last_check = time.time()
            print(f"Scansione larghissima {now}")
            for pair in PAIRS:
                try:
                    df = yf.download(pair, period="1d", interval="5m", progress=False)
                    if len(df)<20: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df["ema20"]=df["Close"].ewm(span=20).mean()
                    last=df.iloc[-1]

                    # REGOLA PIU' LARGA POSSIBILE - SOLO 1 RIGA
                    if last["Close"] > last["ema20"]:
                        sig="BUY"
                    else:
                        sig="SELL"

                    pending[pair]=(sig,float(last["Close"]),now)
                    send(f"🔔 *V68 LARGO MAX {sig} {pair.replace('=X','')}*\nPrice {last['Close']:.5f} EMA20 {last['ema20']:.5f}\n⏳ AUTO 5min")
                except Exception as e:
                    print(f"Err {pair}: {e}")
    except: pass
    time.sleep(3)
