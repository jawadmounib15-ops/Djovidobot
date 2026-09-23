import os, time, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "V105.1 STRETTO REALI LIVE"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","NZDUSD=X","USDCHF=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","CADJPY=X","NZDJPY=X","CHFJPY=X","EURCHF=X","GBPCHF=X","AUDCHF=X","EURAUD=X","GBPAUD=X","EURCAD=X","AUDCAD=X","NZDCAD=X","AUDNZD=X","CADCHF=X","EURNZD=X"]

WIN=0; LOSS=0; PEND={}; CHECK=0

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def get_candles(pair):
    sym=pair.replace("=X","")
    try:
        r=requests.get(f"https://api-eu.po.market/history?symbol={sym}&period=300&count=300", timeout=4, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200:
            j=r.json(); data=j.get('candles') or j.get('data') or []
            if len(data)>200:
                df=pd.DataFrame(data)
                for k in [['close','Close'],['open','Open'],['high','High'],['low','Low']]:
                    if k[0] in df.columns: df[k[1]]=df[k[0]]
                if "Close" in df.columns: return df
    except: pass
    try:
        df=yf.download(pair,period="10d",interval="5m",progress=False,auto_adjust=True)
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df
    except: return None

def bot():
    global WIN,LOSS,CHECK
    send("💀 *V105.1 STRETTO 1 PELO REALI ONLINE*\nRSI 65/35 + BB 0.10 + EMA 0.05%")
    while True:
        try:
            now=datetime.now()
            for k in list(PEND.keys()):
                s,p,t=PEND[k]
                if now-t>=timedelta(minutes=5):
                    try:
                        df=get_candles(k)
                        if df is None or len(df)==0: continue
                        c=float(df["Close"].iloc[-1])
                        w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
                        if w: WIN+=1; R="✅ WIN"
                        else: LOSS+=1; R="❌ LOSS"
                        tot=WIN+LOSS; wr=WIN/tot*100 if tot>0 else 0
                        send(f"{R} *{k.replace('=X','')} {s}* {p:.5f}->{c:.5f} WR {wr:.0f}% ({WIN}W/{LOSS}L)\n👉 Pocket fai *{'SELL' if s=='BUY' else 'BUY'}*")
                        del PEND[k]
                    except: pass
            if time.time()-CHECK>=30:
                CHECK=time.time()
                for pair in PAIRS:
                    if pair in PEND: continue
                    try:
                        df=get_candles(pair)
                        if df is None or len(df)<210: continue
                        df["RSI"]=rsi(df["Close"])
                        df["MA"]=df["Close"].rolling(20).mean()
                        df["STD"]=df["Close"].rolling(20).std()
                        df["UP"]=df["MA"]+2*df["STD"]
                        df["LOW"]=df["MA"]-2*df["STD"]
                        df["EMA200"]=df["Close"].ewm(span=200).mean()
                        c=float(df["Close"].iloc[-1]); r=float(df["RSI"].iloc[-1])
                        up=float(df["UP"].iloc[-1]); low=float(df["LOW"].iloc[-1]); ema=float(df["EMA200"].iloc[-1])
                        toll=(up-low)*0.10
                        ema_dist_ok=abs(c-ema)/c>0.0005
                        sig=None
                        if r>=65 and c>=up-toll and c<ema and ema_dist_ok: sig="BUY"
                        elif r<=35 and c<=low+toll and c>ema and ema_dist_ok: sig="SELL"
                        if sig:
                            PEND[pair]=(sig,c,now)
                            send(f"💀 *5M {sig} {pair.replace('=X','')} RSI:{r:.0f} STRETTO REALI*\n👉 *POCKET: {'SELL' if sig=='BUY' else 'BUY'}*")
                    except: pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
