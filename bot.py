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
@app.route('/')
def home(): return f"V61.6 SOLO PINBAR FIX - TOKEN:{bool(TOKEN)} CHAT:{bool(CHAT_ID)} - Pending:{len(pending)} - Cooldown:{len(cooldown)} - {len(PAIRS)} PAIRS"

pending=[]; cooldown={}
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

def send(msg):
    print(f"SEND: {msg}")
    if not TOKEN or not CHAT_ID: return
    try:
        r=requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=15)
        print(f"TG RESP: {r.status_code}")
    except Exception as e: print(f"SEND ERR: {e}")

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def stochastic(df,k=14,d=3):
    lo=df['Low'].rolling(k).min(); hi=df['High'].rolling(k).max()
    k_perc=100*((df['Close']-lo)/(hi-lo))
    return k_perc, k_perc.rolling(d).mean()

def scan():
    global pending
    pending=[p for p in pending if time.time()-p['time']<1800]
    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 1800: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            tk=yf.Ticker(symbol, session=_YF_SESSION)
            df=tk.history(period="5d", interval="15m")
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            price=c; rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200'])
            is_green=c>o; is_red=not is_green
            body=abs(c-o); total_range=h-l
            upper=h-max(o,c); lower=min(o,c)-l

            if last['atr'] < last['atr_ma50']*0.55: continue
            if last['atr'] > last['atr_ma50']*1.80: continue
            tocco_e20=abs(price-e20)/price < 0.0030
            dist_e200=abs(price-e200)/price
            if dist_e200 < 0.0005: continue
            slope_e20 = float(df['e20'].iloc[-1] - df['e20'].iloc[-4])

            signal=None; lavoro=""; scadenza=""

            # L1 TREND - UGUALE
            if not signal:
                if price>e200 and e20>e50 and slope_e20>=0 and 28<=rsi_v<=47 and stoch_k<35 and is_green:
                    if tocco_e20 or 25<=rsi_v<=38:
                        signal="BUY"; lavoro="L1 TREND"; scadenza="30 MIN"
                if price<e200 and e20<e50 and slope_e20<=0 and 53<=rsi_v<=72 and stoch_k>65 and is_red:
                    if tocco_e20 or 65<=rsi_v<=76:
                        signal="SELL"; lavoro="L1 TREND"; scadenza="15 MIN"

            # L2 PINBAR - MODIFICA SOLO QUI - PELO ALLA VOLTA
            if not signal and total_range>0 and body>0:
                pin_bull = lower > body*2.4 and body < total_range*0.38 and upper < body*0.7 and is_green
                pin_bear = upper > body*2.4 and body < total_range*0.38 and lower < body*0.7 and is_red
                if pin_bull and price>e200 and e20>e50 and 30<=rsi_v<=55:
                    signal="BUY"; lavoro="L2 PINBAR"; scadenza="30 MIN"
                if pin_bear and price<e200 and e20<e50 and 45<=rsi_v<=70:
                    signal="SELL"; lavoro="L2 PINBAR"; scadenza="15 MIN"

            if signal:
                if clean in ["EURGBP","EURJPY","GBPCHF","EURAUD"]: scadenza="30 MIN"
                send(f"🎯 {lavoro} {signal} {clean} RSI {rsi_v:.0f} STO {stoch_k:.0f} ⏰ {scadenza}\nEntry {price:.5f}")
                pending.append({"symbol":clean,"signal":signal,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count_this_scan+=1
        except Exception as e:
            print(f"ERR {clean}: {e}")
            continue

def loop():
    time.sleep(3)
    if not TOKEN or not CHAT_ID: print("MANCA TOKEN/CHAT_ID!")
    else: send(f"🚀 V61.6 SOLO PINBAR FIX AVVIATO - {len(PAIRS)} coppie\nUnica modifica: coda 2.2->2.4 body 40%->38% opposta 0.9->0.7")
    while True:
        try: scan(); check_results()
        except Exception as e: print(f"LOOP ERR {e}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
