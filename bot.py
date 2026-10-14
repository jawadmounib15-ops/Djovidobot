# bot.py - DOPPIO LAVORO - L1 TUO + L2 REGOLE VERE
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","GBPJPY=X","AUDJPY=X","EURCAD=X"]
_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")

cooldown1 = {} # Per lavoro 1
cooldown2 = {} # Per lavoro 2

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def rsi(s, p=7):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=10)
    except: pass

# ============ LAVORO 1 - TUO ORIGINALE ============
def pinbar_ALLARGATA(df):
    if len(df)<25: return None
    c=df.iloc[-2]
    O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total=H-L
    if total<=0: return None
    corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
    if corpo>total*0.35: return None
    if inf>=total*0.55 and sup<=total*0.25:
        return {"dir":"SU","target":L+(inf*0.70),"forza":inf/total*100}
    if sup>=total*0.55 and inf<=total*0.25:
        return {"dir":"GIÙ","target":H-(sup*0.70),"forza":sup/total*100}
    return None

def scan_L1():
    for symbol in PAIRS:
        clean=symbol.replace("=X","")
        if clean in cooldown1 and time.time()-cooldown1[clean]<900: continue
        try:
            df=fix_df(yf.Ticker(symbol, session=_YF).history(period="5d", interval="5m"))
            if len(df)<25: continue
            df['rsi7']=rsi(df['Close'],7); last_rsi=float(df['rsi7'].iloc[-2])
            pin=pinbar_ALLARGATA(df)
            if not pin: continue
            if pin["dir"]=="SU" and last_rsi>40: continue
            if pin["dir"]=="GIÙ" and last_rsi<60: continue
            cooldown1[clean]=time.time()
            sig="CALL" if pin["dir"]=="SU" else "PUT"
            msg=f"✅ <b>L1 ALLARGATA</b> ✅\nAsset: <b>{clean}</b>\nDir: <b>{sig}</b>\nScad: 5 MIN\nEntry: <code>{pin['target']:.5f}</code>\nForza: {pin['forza']:.0f}% | RSI: {last_rsi:.0f}\nOra: {ora_it()}"
            send(msg)
            print(f"L1 {clean}")
        except: continue

# ============ LAVORO 2 - REGOLE VERE FOTO ============
def pinbar_REGOLE_VERE(df):
    if len(df)<5: return None
    c=df.iloc[-1] # ULTIMA come Quotex
    O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total=H-L
    if total<=0: return None
    corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
    if corpo==0: corpo=total*0.01
    is_hammer = (inf >= corpo*2.0 and inf >= total*0.50 and sup <= total*0.35 and corpo <= total*0.40)
    is_star = (sup >= corpo*2.0 and sup >= total*0.50 and inf <= total*0.35 and corpo <= total*0.40)
    if is_hammer: return {"dir":"SU","target":L+(inf*0.70),"forza":inf/total*100,"tipo":"HAMMER"}
    if is_star: return {"dir":"GIÙ","target":H-(sup*0.70),"forza":sup/total*100,"tipo":"STAR"}
    return None

def scan_L2():
    for symbol in PAIRS:
        clean=symbol.replace("=X","")
        if clean in cooldown2 and time.time()-cooldown2[clean]<600: continue
        try:
            df1=fix_df(yf.Ticker(symbol, session=_YF).history(period="1d", interval="1m"))
            if len(df1)<30: continue
            df5=df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            df5['rsi14']=rsi(df5['Close'],14); last_rsi=float(df5['rsi14'].iloc[-1])
            pin=pinbar_REGOLE_VERE(df5)
            if not pin: continue
            if pin["dir"]=="SU" and last_rsi>70: continue
            if pin["dir"]=="GIÙ" and last_rsi<30: continue
            cooldown2[clean]=time.time()
            sig="CALL" if pin["dir"]=="SU" else "PUT"
            msg=f"🎯 <b>L2 REALE FOTO</b> 🎯\nAsset: <b>{clean}</b>\nDir: <b>{sig}</b> {pin['tipo']}\nScad: 5 MIN\nEntry: <code>{pin['target']:.5f}</code>\nForza: {pin['forza']:.0f}% | RSI: {last_rsi:.0f}\nOra: {ora_it()}"
            send(msg)
            print(f"L2 {clean} {pin['tipo']}")
        except: continue

def loop():
    send(f"🚀 <b>BOT DOPPIO LAVORO</b>\nL1: ALLARGATA | L2: REGOLE VERE FOTO\nOra {ora_it()}")
    while True:
        try:
            now=datetime.now(ITALY)
            sleep_sec=(5-(now.minute%5))*60-now.second+3
            if sleep_sec<10: sleep_sec+=300
            time.sleep(sleep_sec)
            threading.Thread(target=scan_L1, daemon=True).start()
            threading.Thread(target=scan_L2, daemon=True).start()
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"Doppio: L1 {len(cooldown1)} L2 {len(cooldown2)} {ora_it()}"
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
