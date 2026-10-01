import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
# TOLTE esotiche USDSEK/MXN/NOK che spammavano
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
@app.route('/')
def home(): return f"V61.1 STRETT0 - {len(PAIRS)} PAIRS - cooldown 90min"

pending=[]
cooldown={} # nuovo

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
        if count_this_scan>=5: break # MAX 5 segnali per giro, non 6
        clean=symbol.replace("=X","")
        # COOLDOWN 10 minuti per coppia
        if clean in cooldown and time.time()-cooldown[clean] < 600: continue
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

            # STRETT0: ATR 0.6 - 2.0x invece di 0.45-3.2
            if last['atr'] < last['atr_ma50']*0.66: continue
            if last['atr'] > last['atr_ma50']*2.0: continue

            tocco_e20=abs(price-float(last['e20']))/price < 0.004 # più stretto 0.3% non 0.4%
            dist_e200=abs(price-float(last['e200']))/price
            if dist_e200 < 0.001: continue # no flat

            signal=None
            # STRETT0: RSI più centrale e stoch più estremo
            if price>float(last['e200']) and tocco_e20 and 30<=rsi_v<=36 and stoch_k<15:
                signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 64<=rsi_v<=70 and stoch_k>85:
                signal="SELL"

            if signal:
                if any(p['symbol']==clean for p in pending): continue
                send(f"🎯 L4 PELO {signal} {clean} RSI {rsi_v:.0f} STO {stoch_k:.0f} Entry {price:.5f}")
                pending.append({"symbol":clean,"signal":signal,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count_this_scan+=1
        except: continue

def check_results():
    now=time.time()
    for p in pending[:]:
        if now-p['time'] < 60: continue # controlla dopo 2min 
        try:
            df=yf.download(p['symbol']+"=X", period="1d", interval="1m", progress=False)
            df=fix_df(df)
            if len(df)==0: continue
            curr=float(df['Close'].iloc[-1])
            win=(p['signal']=="BUY" and curr>p['entry']) or (p['signal']=="SELL" and curr<p['entry'])
            # manda solo WIN/LOSS importanti, non spam
            send(f"{'WIN ✅' if win else 'LOSS ❌'} L4 {p['signal']} {p['symbol']} {((curr-p['entry'])/p['entry']*100):+.2f}%")
            pending.remove(p)
        except: pass

def loop():
    send(f"🚀 V61.1 STRETT0 - {len(PAIRS)} coppie - max 2 segnali/giro - cooldown 90min")
    while True:
        try: scan(); check_results()
        except: pass
        time.sleep(60) # scan ogni 1min

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
