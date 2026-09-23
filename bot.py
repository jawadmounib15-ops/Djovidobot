import os, time, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home():
    return "V105 CORRETTO ONLINE"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCHF=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","NZDUSD=X","EURCHF=X","CADJPY=X"]

WIN=0; LOSS=0; PEND={}; IDX=0

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    ag=g.ewm(alpha=1/p).mean(); al=l.ewm(alpha=1/p).mean()
    return 100-(100/(1+ag/al))

def bot():
    global WIN,LOSS,IDX
    send("💀 *V105 CORRETTO ONLINE*")
    while True:
        try:
            now=datetime.now()
            for k in list(PEND.keys()):
                s,p,t = PEND[k]
                if now-t >= timedelta(minutes=5):
                    try:
                        df=yf.download(k,period="1d",interval="1m",progress=False)
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                        c=float(df["Close"].iloc[-1])
                        pocket = "SELL" if s=="BUY" else "BUY"
                        w = (pocket=="BUY" and c>p) or (pocket=="SELL" and c<p)
                        if w: WIN+=1; R="✅ WIN"
                        else: LOSS+=1; R="❌ LOSS"
                        tot=WIN+LOSS; wr=WIN/tot*100 if tot>0 else 0
                        send(f"{R} *{k.replace('=X','')} Pocket {pocket}* WR {wr:.0f}% ({WIN}W/{LOSS}L)")
                        del PEND[k]
                    except: pass

            batch = PAIRS[IDX:IDX+3]
            if not batch:
                IDX=0
                batch=PAIRS[0:3]
            IDX+=3

            for pair in batch:
                if pair in PEND: continue
                try:
                    df=yf.download(pair,period="5d",interval="5m",progress=False)
                    if len(df)<210: continue
                    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                    df["RSI"]=rsi(df["Close"])
                    df["MA"]=df["Close"].rolling(20).mean()
                    df["STD"]=df["Close"].rolling(20).std()
                    df["UP"]=df["MA"]+2*df["STD"]
                    df["LOW"]=df["MA"]-2*df["STD"]
                    df["EMA200"]=df["Close"].ewm(span=200).mean()
                    c=float(df["Close"].iloc[-1]); r=float(df["RSI"].iloc[-1])
                    up=float(df["UP"].iloc[-1]); low=float(df["LOW"].iloc[-1])
                    ema=float(df["EMA200"].iloc[-1])
                    toll=(up-low)*0.25
                    sig=None
                    if r>=63 and c>=up-toll and c>ema: sig="BUY"
                    elif r<=37 and c<=low+toll and c<ema: sig="SELL"
                    if sig:
                        PEND[pair]=(sig,c,now)
                        pocket = "SELL" if sig=="BUY" else "BUY"
                        send(f"💀 *{pair.replace('=X','')} {sig} -> POCKET {pocket} RSI:{r:.0f}*")
                except: pass
                time.sleep(2)
        except: pass
        time.sleep(60)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
