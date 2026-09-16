import yfinance as yf, os, time, threading, requests
from flask import Flask
TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
print(f"--- V2.7 FIX SERIES AVVIATO TOKEN ok={bool(TOKEN)} ---")
COPPIE=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","EURCAD=X","USDCHF=X","AUDUSD=X","EURGBP=X"]
app=Flask(__name__)
@app.route('/')
def home(): return "V2.7 FIX ONLINE"
last_sent={}
def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg},timeout=10)
        print(f"Inviato: {msg}")
    except Exception as e: print(f"Err send:{e}")
def check(pair):
    try:
        df=yf.download(pair,period="2d",interval="5m",progress=False,auto_adjust=True)
        if len(df)<55: return None
        close_series = df['Close']
        ema_series = close_series.ewm(span=50).mean()
        # Prendo gli ultimi 2 valori come numeri veri, non Series
        close = float(close_series.iloc[-1])
        prev = float(close_series.iloc[-2])
        ema = float(ema_series.iloc[-1])
        if time.time()-last_sent.get(pair,0)<2700: return None
        sig=None
        if prev < ema and close > ema: sig=f"🟢 BUY {pair.replace('=X','')} @ {close:.5f}"
        elif prev > ema and close < ema: sig=f"🔴 SELL {pair.replace('=X','')} @ {close:.5f}"
        if sig: last_sent[pair]=time.time(); return sig
    except Exception as e:
        print(f"Err {pair}:{e}")
        return None
def loop():
    print("Loop partito")
    send("✅ DjovidoBot V2.7 FIX ONLINE - Errore Series risolto!")
    while True:
        for cp in COPPIE:
            m=check(cp)
            if m: send(m)
        time.sleep(60)
threading.Thread(target=loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
