import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
@app.route('/')
def home():
    return f"V61.4 SBLOCCATO - TOKEN:{bool(TOKEN)} CHAT:{bool(CHAT_ID)} - Pending:{len(pending)} - Cooldown:{len(cooldown)} - {len(PAIRS)} PAIRS"

pending=[]; cooldown={}
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

def send(msg):
    print(f"SEND: {msg}")
    try:
        r=requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=15)
        print(f"TG RESP: {r.status_code}")
    except Exception as e:
        print(f"SEND ERR: {e}")

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
    pending=[p for p in pending if time.time()-p['time']<3600]
    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=2: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 3600: continue # prima 5400 -> 3600
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
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200'])
            is_green=float(last['Close'])>float(last['Open'])
            is_red=not is_green

            if last['atr'] < last['atr_ma50']*0.65: continue
            if last['atr'] > last['atr_ma50']*1.95: continue
            tocco_e20=abs(price-e20)/price < 0.0030 # prima 0.0022 -> 0.0030 SBLOCCA
            dist_e200=abs(price-e200)/price
            if dist_e200 < 0.0008: continue # prima 0.0015 -> 0.0008 SBLOCCA

            slope_e20 = float(df['e20'].iloc[-1] - df['e20'].iloc[-4])
            slope_e50 = float(df['e50'].iloc[-1] - df['e50'].iloc[-4])

            signal=None
            # FIX SBLOCCO: RSI più largo e STOCH più largo
            if price>e200 and e20>e50 and slope_e20>0 and tocco_e20 and 30<=rsi_v<=44 and stoch_k<28 and is_green:
                signal="BUY"
            if price<e200 and e20<e50 and slope_e20<0 and tocco_e20 and 56<=rsi_v<=70 and stoch_k>72 and is_red:
                signal="SELL"

            if signal:
                send(f"🎯 V61.4 {signal} {clean} RSI {rsi_v:.0f} STO {stoch_k:.0f} Entry {price:.5f}")
                pending.append({"symbol":clean,"signal":signal,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count_this_scan+=1
        except Exception as e:
            print(f"ERR {clean}: {e}")
            continue

def check_results():
    now=time.time()
    for p in pending[:]:
        if now-p['time'] < 180: continue
        try:
            df=yf.Ticker(p['symbol']+"=X", session=_YF_SESSION).history(period="1d", interval="1m")
            df=fix_df(df)
            if len(df)==0: continue
            curr=float(df['Close'].iloc[-1])
            win=(p['signal']=="BUY" and curr>p['entry']) or (p['signal']=="SELL" and curr<p['entry'])
            send(f"{'WIN ✅' if win else 'LOSS ❌'} V61.4 {p['signal']} {p['symbol']} {((curr-p['entry'])/p['entry']*100):+.2f}%")
            pending.remove(p)
        except: pass

def loop():
    time.sleep(3)
    if not TOKEN or not CHAT_ID:
        print("MANCA TOKEN/CHAT_ID!")
    else:
        send(f"🚀 V61.4 SBLOCCATO AVVIATO - {len(PAIRS)} coppie - Se leggi questo, Telegram OK! Ora cerco segnali...")
    while True:
        try:
            scan()
            check_results()
        except Exception as e:
            print(f"LOOP ERR {e}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
