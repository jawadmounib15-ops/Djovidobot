import yfinance as yf, os, time, threading, requests, pandas as pd
from flask import Flask
TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
print(f"--- V2.8 DEFINITIVO AVVIATO TOKEN ok={bool(TOKEN)} ---")
COPPIE=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","EURCAD=X","USDCHF=X","AUDUSD=X","EURGBP=X"]
app=Flask(__name__)
@app.route('/')
def home(): return "V2.8 ONLINE"
last_sent={}
def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg},timeout=10)
    except: pass
def get_price(df):
    # Questo sistema funziona SEMPRE, anche se yfinance cambia formato
    try:
        c = df['Close']
        if isinstance(c, pd.DataFrame):
            c = c.iloc[:,0]
        return float(c.iloc[-1]), float(c.iloc[-2]), float(c.ewm(span=50).mean().iloc[-1])
    except:
        return None,None,None
def check(pair):
    try:
        df=yf.download(pair,period="2d",interval="5m",progress=False,auto_adjust=True)
        if len(df)<55: return None
        close, prev, ema = get_price(df)
        if close is None: return None
        if time.time()-last_sent.get(pair,0)<2700: return None
        sig=None
        if prev < ema and close > ema: sig=f"🟢 BUY {pair.replace('=X','')} @ {close:.5f}"
        elif prev > ema and close < ema: sig=f"🔴 SELL {pair.replace('=X','')} @ {close:.5f}"
        if sig: last_sent[pair]=time.time(); return sig
    except Exception as e:
        print(f"Err {pair}:{e}")
        return None
def loop():
    print("Loop partito V2.8")
    send("✅ DjovidoBot V2.8 DEFINITIVO ONLINE - Rosso sistemato!")
    while True:
        for cp in COPPIE:
            m=check(cp)
            if m: send(m)
        time.sleep(60)
threading.Thread(target=loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
