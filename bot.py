import yfinance as yf, os, time, threading, requests
from flask import Flask
TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
print(f"--- V2.6 AVVIATO TOKEN ok={bool(TOKEN)} ---")
COPPIE=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","EURCAD=X","USDCHF=X","AUDUSD=X","EURGBP=X"]
app=Flask(__name__)
@app.route('/')
def home(): return "V2.6 ONLINE"
last_sent={}
def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg})
        print(f"Inviato: {msg}")
    except Exception as e: print(e)
def check(pair):
    try:
        df=yf.download(pair,period="2d",interval="5m",progress=False,auto_adjust=True)
        if len(df)<55: return None
        df['EMA50']=df['Close'].ewm(span=50).mean()
        c=df.iloc[-1]; p=df.iloc[-2]
        close=float(c['Close']); ema=float(c['EMA50']); prev=float(p['Close'])
        if time.time()-last_sent.get(pair,0)<2700: return None
        sig=None
        if prev<ema and close>ema: sig=f"🟢 BUY {pair.replace('=X','')} @ {close:.5f}"
        elif prev>ema and close<ema: sig=f"🔴 SELL {pair.replace('=X','')} @ {close:.5f}"
        if sig: last_sent[pair]=time.time(); return sig
    except Exception as e: print(f"Err {pair}:{e}")
def loop():
    print("Loop partito"); send("✅ DjovidoBot V2.6 ONLINE!")
    while True:
        for cp in COPPIE:
            m=check(cp)
            if m: send(m)
        time.sleep(60)
threading.Thread(target=loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
