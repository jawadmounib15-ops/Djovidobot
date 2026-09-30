# analyzer.py - FILE UNICO con app dentro + PINBAR PERFETTA
import os, time, threading, requests
from flask import Flask
import yfinance as yf
import pandas as pd

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","EURNZD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X","GBPNZD=X","AUDJPY=X","AUDCAD=X","AUDCHF=X","AUDNZD=X","CADJPY=X","CADCHF=X","CHFJPY=X","NZDJPY=X","NZDCAD=X","NZDCHF=X"]

app = Flask(__name__)

@app.route('/')
def home():
    return "V64 PINBAR PERFETTA LIVE - analyzer:app OK"

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def ema(s,p): return s.ewm(span=p).mean()

def is_perfect_pinbar(o,h,l,c,rsi_val,dist_ema20,prev_high,prev_low):
    body=abs(c-o); rng=h-l
    if rng==0 or body==0: return None
    up=h-max(o,c); low=min(o,c)-l
    close_pos=(c-l)/rng; body_pct=body/rng
    if not (0.05<=body_pct<=0.30): return None
    dom=max(up,low)
    if dom<body*2.8 or dom<rng*0.55: return None
    if min(up,low)>rng*0.30: return None
    if rsi_val and not (30<=rsi_val<=72): return None
    if dist_ema20 and dist_ema20>0.012: return None
    if up>low:
        if close_pos>0.40: return None
        if h<prev_high*0.9995: return None
        return "SELL", round(up/body,1)
    else:
        if close_pos<0.60: return None
        if l>prev_low*1.0005: return None
        return "BUY", round(low/body,1)

def scan():
    for symbol in PAIRS:
        try:
            df=yf.download(symbol, period="5d", interval="5m", progress=False)
            df=fix_df(df)
            if len(df)<210: continue
            df['RSI']=rsi(df['Close']); df['EMA20']=ema(df['Close'],20)
            last=df.iloc[-1]; prev_h=df['High'].iloc[-11:-1].max(); prev_l=df['Low'].iloc[-11:-1].min()
            rsi_v=float(last['RSI']); dist=abs(float(last['Close'])-float(last['EMA20']))/float(last['Close'])
            pin=is_perfect_pinbar(last['Open'],last['High'],last['Low'],last['Close'],rsi_v,dist,prev_h,prev_l)
            if pin:
                sig,ratio=pin
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":f"{'🔴' if sig=='SELL' else '🟢'} {symbol.replace('=X','')} {sig} PINBAR PERFETTA {ratio}x | RSI {rsi_v:.0f}"}, timeout=10)
        except: continue

def loop():
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":"🚀 V64 ATTIVO analyzer:app - Pinbar Perfetta"}, timeout=10)
    except: pass
    while True:
        scan(); time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
