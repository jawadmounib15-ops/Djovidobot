import os, time, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home():
    return "V105 3 FILTRI 0% WR ONLINE"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCHF=X",
         "USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","CADJPY=X",
         "CHFJPY=X","EURCHF=X","GBPCHF=X","AUDCHF=X","EURAUD=X",
         "GBPAUD=X","EURCAD=X","AUDCAD=X","NZDCAD=X","CADCHF=X"]

WIN=0; LOSS=0; PEND={}; CHECK=0

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    ag=g.ewm(alpha=1/p).mean(); al=l.ewm(alpha=1/p).mean()
    return 100-(100/(1+ag/al))

def bot():
    global WIN,LOSS,CHECK
    send("💀 *V105 3 FILTRI FISSO 0% WR ONLINE*\n25 coppie | Scan 60sec\nBUY: RSI>63 + BB UP + Trend DOWN\nSELL: RSI<37 + BB DOWN + Trend UP")
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
                        w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
                        if w: WIN+=1; R="✅ WIN"
                        else: LOSS+=1; R="❌ LOSS"
                        tot=WIN+LOSS; wr=WIN/tot*100 if tot>0 else 0
                        send(f"{R} *{k.replace('=X','')} {s}* {p:.5f}->{c:.5f} WR {wr:.0f}% ({WIN}W/{LOSS}L)\n👉 Pocket fai *{'SELL' if s=='BUY' else 'BUY'}*")
                        del PEND[k]
                    except: pass

            if time.time()-CHECK >= 60:
                CHECK=time.time()
                for pair in PAIRS:
                    if pair in PEND: continue
                    try:
                        df=yf.download(pair,period="10d",interval="5m",progress=False)
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
                        sig=None
                        toll=(up-low)*0.15
                        if r>=65 and c>=up-toll and c<ema: sig="BUY"
                        elif r<=35 and c<=low+toll and c>ema: sig="SELL"
                        if sig:
                            PEND[pair]=(sig,c,now)
                            send(f"💀 *5M {sig} {pair.replace('=X','')} 3 FILTRI RSI:{r:.0f}*\n👉 *POCKET: {'SELL' if sig=='BUY' else 'BUY'}*")
                    except: pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
