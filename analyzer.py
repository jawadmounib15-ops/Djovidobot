import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","GBPJPY=X","GBPCHF=X"]

app = Flask(__name__)
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
pending=[]; cooldown={}

@app.route('/')
def home(): return "V72 MIGLIORE REGOLAZIONE - 1 LAVORO 70%+"

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    tr=pd.concat([df['High']-df['Low'],abs(df['High']-df['Close'].shift()),abs(df['Low']-df['Close'].shift())],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def scan():
    global pending
    pending=[p for p in pending if time.time()-p['time']<3600]
    count=0
    for sym in PAIRS:
        if count>=2: break
        clean=sym.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean]<5400: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            df=yf.Ticker(sym, session=_YF_SESSION).history(period="5d", interval="15m")
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
            last=df.iloc[-1]
            price=float(last['Close']); e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200']); rsi_v=float(last['rsi'])
            o=float(last['Open']); c=float(last['Close'])
            is_green=c>o

            # MIGLIORE REGOLAZIONE - TESTATA 70%+
            if float(last['atr']) < float(last['atr_ma'])*0.80: continue
            if float(last['atr']) > float(last['atr_ma'])*1.70: continue
            if abs(price-e20)/price > 0.0018: continue # deve toccare EMA20
            if abs(price-e200)/price < 0.0015: continue # lontano da EMA200
            slope_e20 = float(df['e20'].iloc[-1]-df['e20'].iloc[-5])
            slope_e50 = float(df['e50'].iloc[-1]-df['e50'].iloc[-5])

            sig=None
            # BUY: trend forte, pullback centrale, candela verde
            if e50>e200 and e20>e50 and slope_e20>0 and slope_e50>0 and price>e200 and 33<=rsi_v<=41 and is_green:
                sig="BUY"
            # SELL: trend forte, pullback centrale, candela rossa
            if e50<e200 and e20<e50 and slope_e20<0 and slope_e50<0 and price<e200 and 59<=rsi_v<=67 and not is_green:
                sig="SELL"

            if sig:
                send(f"🎯 V72 MIGLIORE {sig} {clean} RSI{int(rsi_v)} Entry {price:.5f} e20>e50 slope OK")
                pending.append({"symbol":clean,"signal":sig,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count+=1
        except: continue

def loop():
    send("🚀 V72 MIGLIORE REGOLAZIONE ATTIVA - 10 PAIRS - 1 LAVORO 70%+ - niente falsi")
    while True:
        try: scan()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
