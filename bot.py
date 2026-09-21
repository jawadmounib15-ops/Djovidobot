import os, time, requests, yfinance as yf, threading
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home():
    return "V66 ULTRA LARGO AUTO ATTIVO"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# IL TUO BOT SOTTO
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
WIN = 0
LOSS = 0
pending = {}
last_check = 0

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

send("🚀 *V66 ULTRA LARGO AUTO ATTIVO*\nRender ora resta VERDE!")

print("Bot V66 ULTRA AUTO + Flask avviato")

while True:
    try:
        now = datetime.now()
        to_remove = []
        for pair, (signal, entry_price, entry_time) in list(pending.items()):
            if now - entry_time >= timedelta(minutes=15):
                try:
                    df = yf.download(pair, period="1d", interval="1m", progress=False)
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    curr = float(df["Close"].iloc[-1])
                    win = (signal=="BUY" and curr>entry_price) or (signal=="SELL" and curr<entry_price)
                    if win: WIN+=1; res="✅ WIN AUTO"
                    else: LOSS+=1; res="❌ LOSS AUTO"
                    tot=WIN+LOSS; wr=(WIN/tot*100) if tot>0 else 0
                    send(f"{res} *{pair.replace('=X','')} {signal}*\nEntrata {entry_price:.5f} -> Ora {curr:.5f}\n📊 WIN {WIN} LOSS {LOSS} WR {wr:.1f}%")
                    to_remove.append(pair)
                except: pass
        for p in to_remove:
            if p in pending: del pending[p]

        if time.time() - last_check > 60:
            last_check = time.time()
            for pair in PAIRS:
                if pair in pending: continue
                try:
                    df = yf.download(pair, period="1d", interval="5m", progress=False)
                    if len(df)<25: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df["ema20"]=df["Close"].ewm(span=20).mean()
                    delta=df["Close"].diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean()
                    df["rsi"]=100-(100/(1+gain/loss))
                    last=df.iloc[-1]
                    sig=None
                    if last["Close"]>last["ema20"] and last["rsi"]>50: sig="BUY"
                    elif last["Close"]<last["ema20"] and last["rsi"]<50: sig="SELL"
                    if sig:
                        pending[pair]=(sig,float(last["Close"]),now)
                        send(f"🔔 *ULTRA {sig} {pair.replace('=X','')}*\nPrice {last['Close']:.5f} EMA {last['ema20']:.5f} RSI {last['rsi']:.1f}\n⏳ AUTO tra 15min")
                except: pass
    except: pass
    time.sleep(3)
