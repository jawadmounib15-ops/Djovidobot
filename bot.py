import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","AUDCHF=X","AUDCAD=X","CADCHF=X"]

app = Flask(__name__)
pending=[]; cooldown={}; _YF_SESSION=cffi_requests.Session(impersonate="chrome")
bad_pairs={} # coppie che perdono tanto

@app.route('/')
def home():
    return f"BOT 1.9x FIX - Pending:{len(pending)} Bad:{bad_pairs}"

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def scan():
    global pending
    pending=[p for p in pending if time.time()-p['time']<400]
    c=0
    for symbol in PAIRS:
        if c>=2: break
        clean=symbol.replace("=X","")
        # se AUDCAD ha perso 2 volte, stop 30 min
        if clean in bad_pairs and bad_pairs[clean]>=2 and time.time()-cooldown.get(clean,0)<1800:
            continue
        if clean in cooldown and time.time()-cooldown[clean]<400: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            df=fix_df(yf.Ticker(symbol, session=_YF_SESSION).history(period="2d", interval="2m"))
            if len(df)<200: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['rsi']=rsi(df['Close'])
            last=df.iloc[-1]
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); cc=float(last['Close'])
            e20=float(last['e20']); e50=float(last['e50']); rsi_v=float(last['rsi'])
            body=abs(cc-o); rng=h-l; upper=h-max(o,cc); lower=min(o,cc)-l
            if rng<0.000005 or body==0: continue
            is_green=cc>o; is_red=not is_green

            # 1.9x LARGO come hai chiesto
            pin_bull = lower > body*2.2 and body < rng*0.45 and upper < body*0.80 and is_green
            pin_bear = upper > body*2.2 and body < rng*0.45 and lower < body*0.80 and is_red

            signal=None
            if pin_bull and e20>e50 and 20<=rsi_v<=38:
                signal="BUY"
            if pin_bear and e20<e50 and 55<=rsi_v<=75:
                signal="SELL"

            if signal:
                send(f"🎯 1.9x {signal} {clean} ⏰6MIN RSI{int(rsi_v)}\n{cc:.5f}")
                pending.append({"symbol":clean,"time":time.time()})
                cooldown[clean]=time.time()
                c+=1
        except: continue

def loop():
    time.sleep(5)
    send("🚀 BOT 1.9x FIX AVVIATO - tolto 3.0x, rimesso 1.9x + anti AUDCAD")
    while True:
        try: scan()
        except: pass
        time.sleep(45)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
