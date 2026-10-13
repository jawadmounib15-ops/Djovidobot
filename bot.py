import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)

@app.route('/')
def home():
    return f"V61.2 SOLO SEGNALI - {len(PAIRS)} PAIRS - cooldown 90min - NO CALCOLO RISULTATO"

cooldown={}

def send(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass

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
    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=4: # MAX 2 segnali per giro
            break

        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 5400: # 90 min
            continue

        try:
            df=yf.download(symbol, period="5d", interval="15m", progress=False)
            df=fix_df(df)
            if len(df)<210: continue

            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)

            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])

            if last['atr'] < last['atr_ma50']*0.50: continue
            if last['atr'] > last['atr_ma50']*2.2: continue

            tocco_e20=abs(price-float(last['e20']))/price < 0.005
            dist_e200=abs(price-float(last['e200']))/price
            if dist_e200 < 0.001: continue

            signal=None
            if price>float(last['e200']) and tocco_e20 and 64<=rsi_v<=75 and stoch_k<85:
                signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 20<=rsi_v<=30 and stoch_k>15:
                signal="SELL"

            if signal:
                # MESSAGGIO SENZA CALCOLO RISULTATO
                send(f"🎯 {signal} {clean}\nRSI {rsi_v:.0f} STO {stoch_k:.0f}\nEntry {price:.5f}\n⏰ Scadenza: 15m / 30m")
                cooldown[clean]=time.time()
                count_this_scan+=1

        except: continue

def loop():
    send(f"🚀 V61.2 ATTIVO - {len(PAIRS)} coppie - SOLO SEGNALI - scadenza 15/30m")
    while True:
        try: scan()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
