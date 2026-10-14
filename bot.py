# bot.py - ALLARGATO - MANDA SUBITO
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

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","GBPJPY=X","EURCAD=X","AUDJPY=X"]
_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def rsi(s, p=7):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def pinbar_ALLARGATA(df):
    if len(df)<25: return None
    c=df.iloc[-2]
    O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total=H-L
    if total<=0: return None
    corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
    # ALLARGATO: corpo fino 35% (prima 20%)
    if corpo>total*0.35: return None
    # ALLARGATO: miccia 55% (prima 70%) - così manda
    if inf>=total*0.55 and sup<=total*0.25:
        return {"dir":"SU","target":L+(inf*0.70),"forza":inf/total*100}
    if sup>=total*0.55 and inf<=total*0.25:
        return {"dir":"GIÙ","target":H-(sup*0.70),"forza":sup/total*100}
    return None

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    for symbol in PAIRS:
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean]<900: continue # 15 min solo
        try:
            df=fix_df(yf.Ticker(symbol, session=_YF).history(period="5d", interval="5m"))
            if len(df)<25: continue
            df['rsi7']=rsi(df['Close'],7); last_rsi=float(df['rsi7'].iloc[-2])
            pin=pinbar_ALLARGATA(df)
            if not pin: continue
            # ALLARGATO: RSI 40/60 non 30/70
            if pin["dir"]=="SU" and last_rsi>40: continue
            if pin["dir"]=="GIÙ" and last_rsi<60: continue
            cooldown[clean]=time.time()
            sig="CALL" if pin["dir"]=="SU" else "PUT"
            msg=f"✅ <b>PIN 5m ALLARGATA</b> ✅\nAsset: <b>{clean}</b>\nDir: <b>{sig}</b>\nScad: 5 MIN\nEntry 70%: <code>{pin['target']:.5f}</code>\nForza: {pin['forza']:.0f}% | RSI: {last_rsi:.0f}\nOra: {ora_it()}"
            send(msg)
            print(f"INVIATO {clean}")
        except: continue

def loop():
    send(f"🚀 <b>BOT ALLARGATO AVVIATO</b>\n55% miccia | 35% corpo | RSI 40/60\nOra {ora_it()}")
    while True:
        try:
            now=datetime.now(ITALY)
            sleep_sec=(5-(now.minute%5))*60-now.second+3
            if sleep_sec<10: sleep_sec+=300
            time.sleep(sleep_sec)
            scan()
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"Allargato {ora_it()}"
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
