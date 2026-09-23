import os, time, requests, yfinance as yf, threading, pandas as pd 
from flask import Flask 
app = Flask(__name__) 
@app.route('/') 
def home(): return "V105 30-70 ADX25 ONLINE" 
TOKEN = os.environ.get("TELEGRAM_TOKEN") 
CHAT = os.environ.get("TELEGRAM_CHAT_ID") 
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCHF=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","EURCHF=X","CADJPY=X"] 
IDX=0 
def send(m): 
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10) 
    except: pass 
def rsi(s,p=14): 
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0) 
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean())) 
def adx_force(df, p=14):
    try:
        h=df["High"]; l=df["Low"]; c=df["Close"]
        tr1=h-l; tr2=(h-c.shift()).abs(); tr3=(l-c.shift()).abs()
        tr=pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)
        atr=tr.ewm(alpha=1/p).mean()
        up=h.diff(); down= -l.diff()
        plus_dm=up.where((up>down)&(up>0),0).ewm(alpha=1/p).mean()
        minus_dm=down.where((down>up)&(down>0),0).ewm(alpha=1/p).mean()
        plus_di=100*plus_dm/atr; minus_di=100*minus_dm/atr
        dx=100*(plus_di-minus_di).abs()/(plus_di+minus_di)
        return float(dx.ewm(alpha=1/p).mean().iloc[-1])
    except: return 0
def bot(): 
    global IDX 
    send("💀 *V105 30-70 ADX25 ONLINE*") 
    while True: 
        try: 
            batch = PAIRS[IDX:IDX+3] 
            if not batch: IDX=0; batch=PAIRS[0:3] 
            IDX+=3 
            for pair in batch: 
                try: 
                    df=yf.download(pair,period="5d",interval="5m",progress=False) 
                    if len(df)<210: continue 
                    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0) 
                    df["RSI"]=rsi(df["Close"]) 
                    df["MA"]=df["Close"].rolling(20).mean() 
                    df["STD"]=df["Close"].rolling(20).std() 
                    df["UP"]=df["MA"]+2*df["STD"] 
                    df["LOW"]=df["MA"]-2*df["STD"] 
                    c=float(df["Close"].iloc[-1]); r=float(df["RSI"].iloc[-1]) 
                    up=float(df["UP"].iloc[-1]); low=float(df["LOW"].iloc[-1])
                    adx_val=adx_force(df)
                    if adx_val < 25: continue
                    sig=None 
                    toll=(up-low)*0.05
                    if r <= 30 and c <= low+toll: sig="BUY" 
                    elif r >= 70 and c >= up-toll: sig="SELL" 
                    if sig: 
                        send(f"💀 *{pair.replace('=X','')} {sig}*\nRSI:{r:.0f} ADX:{adx_val:.0f}") 
                except: pass 
                time.sleep(2) 
        except: pass 
        time.sleep(60) 
threading.Thread(target=bot,daemon=True).start() 
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
