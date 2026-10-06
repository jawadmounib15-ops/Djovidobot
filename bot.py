import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
ROMA = pytz.timezone("Europe/Rome")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X",
         "EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X",
         "GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
@app.route('/')
def home(): return f"V63 75% EQUILIBRATO - {len(PAIRS)} PAIRS"

pending=[]; cooldown={}

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
    now=datetime.now(ROMA)
    if now.weekday()==5 or now.weekday()==6 or (now.weekday()==4 and now.hour>=23): return
    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 5400: continue
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
            prev=df.iloc[-2]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            e20=float(last['e20']); e200=float(last['e200'])
            e20_prev=float(prev['e20'])

            # EQUILIBRATO 75% - non stretto stretto
            if last['atr'] < last['atr_ma50']*0.68 or last['atr'] > last['atr_ma50']*1.80: continue
            if abs(price-e20)/price >= 0.0015: continue # era 0.0008 troppo stretto, ora 0.0015
            if abs(price-e200)/price < 0.0012: continue # era 0.0020 troppo stretto

            e20_slope = e20 - e20_prev
            is_green = float(last['Close']) > float(last['Open'])
            is_red = not is_green
            rsi_prev = float(df['rsi'].iloc[-2])
            rsi_rising = rsi_v > rsi_prev
            rsi_falling = rsi_v < rsi_prev

            signal=None
            # 75% WIN - BUY con conferma RSI in risalita + candela verde
            if price>e200*1.001 and e20>e200 and e20_slope>0 and 27<=rsi_v<=37 and 12<=stoch_k<=26 and is_green and rsi_rising:
                signal="BUY"
            # 75% WIN - SELL con conferma RSI in discesa + candela rossa
            if price<e200*0.999 and e20<e200 and e20_slope<0 and 63<=rsi_v<=73 and 74<=stoch_k<=88 and is_red and rsi_falling:
                signal="SELL"

            if signal:
                if any(p['symbol']==clean for p in pending): continue
                send(f"🎯 V63 75% {signal} {clean} RSI {rsi_v:.0f}({rsi_prev:.0f}) STO {stoch_k:.0f} Entry {price:.5f}")
                pending.append({"symbol":clean,"signal":signal,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count_this_scan+=1
        except: continue

def check_results():
    now=time.time()
    for p in pending[:]:
        if now-p['time'] < 300: continue
        try:
            df=yf.download(p['symbol']+"=X", period="1d", interval="1m", progress=False)
            df=fix_df(df)
            if len(df)==0: continue
            curr=float(df['Close'].iloc[-1])
            win=(p['signal']=="BUY" and curr>p['entry']) or (p['signal']=="SELL" and curr<p['entry'])
            pct=((curr-p['entry'])/p['entry']*100) if p['signal']=="BUY" else ((p['entry']-curr)/p['entry']*100)
            send(f"{'WIN ✅' if win else 'LOSS ❌'} V63 75% {p['signal']} {p['symbol']} {pct:+.2f}% {p['entry']:.5f}->{curr:.5f}")
            pending.remove(p)
        except: pending.remove(p)

def loop():
    send(f"🚀 V63 EQUILIBRATO 75% AVVIATO - RSI 27-37/63-73 STO 12-26/74-88 + slope + RSI rising + candela - fix 23:00")
    while True:
        try: scan(); check_results()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
