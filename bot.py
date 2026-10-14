# bot.py FINALE - DOPPIO LAVORO - 70% - TELEGRAM
# Lavoro 1: 5m analisi -> 5m scadenza
# Lavoro 2: 1m analisi -> 5m scadenza
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

# ===== CONFIG =====
SCADENZA = 5
RITRACCIAMENTO = 0.70
# ==================

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X"]
_YF = cffi_requests.Session(impersonate="chrome", timeout=15)
ITALY = ZoneInfo("Europe/Rome")
cooldown_m5 = {}
cooldown_m1 = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=10)
    except: pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def rsi(s, p=7):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def pinbar_70(df, tf_name="5m"):
    if len(df)<25: return None
    c=df.iloc[-2]; O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total=H-L
    if total<=0: return None
    avg=(df['High'].iloc[-12:-2]-df['Low'].iloc[-12:-2]).mean()
    if total<avg*0.85: return None
    corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
    if corpo>total*0.25: return None
    if inf>=total*0.65 and sup<=total*0.10:
        return {"dir":"SU","target":L+(inf*RITRACCIAMENTO),"forza":inf/total*100}
    if sup>=total*0.65 and inf<=total*0.10:
        return {"dir":"GIÙ","target":H-(sup*RITRACCIAMENTO),"forza":sup/total*100}
    return None

def get_price(sym):
    try:
        df=fix_df(yf.Ticker(sym, session=_YF).history(period="1d", interval="1m"))
        return float(df.iloc[-1]['Close']) if len(df) else None
    except: return None

def scan_tf(timeframe, cooldown_dict, label):
    for symbol in PAIRS:
        clean=symbol.replace("=X","")
        if clean in cooldown_dict and time.time()-cooldown_dict[clean]<600: continue
        try:
            period = "5d" if timeframe=="5m" else "2d"
            df=fix_df(yf.Ticker(symbol, session=_YF).history(period=period, interval=timeframe))
            if len(df)<25: continue
            df['rsi7']=rsi(df['Close'],7); last_rsi=float(df['rsi7'].iloc[-2])
            pin=pinbar_70(df, timeframe)
            if not pin: continue
            if pin["dir"]=="SU" and last_rsi>30: continue
            if pin["dir"]=="GIÙ" and last_rsi<70: continue

            target=pin["target"]
            # attesa 60 sec tocco 70%
            toccato=False
            for _ in range(30):
                time.sleep(2)
                live=get_price(symbol)
                if not live: continue
                if pin["dir"]=="SU" and live<=target*1.0005: toccato=True; break
                if pin["dir"]=="GIÙ" and live>=target*0.9995: toccato=True; break
            if not toccato: continue

            cooldown_dict[clean]=time.time()
            msg=(f"✅ <b>{label} 70%</b> ✅\nAsset: <b>{clean}</b>\nDir: <b>{'SU CALL' if pin['dir']=='SU' else 'GIÙ PUT'}</b>\n"
                 f"Analisi: <b>{timeframe}</b> | Scad: <b>{SCADENZA} MIN</b>\nEntry 70%: <code>{target:.5f}</code>\n"
                 f"Forza: {pin['forza']:.0f}% | RSI: {last_rsi:.0f}\nOra: {ora_it()}")
            send(msg)
            print(f"[{ora_it()}] {label} {clean} inviato")
        except Exception as e:
            print(f"Err {clean} {label}: {e}")
            continue

# ===== LOOP LAVORO 1 - 5m =====
def loop_m5():
    while True:
        try:
            now=datetime.now(ITALY)
            sleep_sec=(5 - (now.minute % 5))*60 - now.second + 5
            if sleep_sec<10: sleep_sec+=300
            time.sleep(sleep_sec)
            print(f"[{ora_it()}] SCAN M5...")
            scan_tf("5m", cooldown_m5, "LAVORO 1 [M5]")
        except Exception as e:
            print(f"Loop M5 err {e}"); time.sleep(10)

# ===== LOOP LAVORO 2 - 1m =====
def loop_m1():
    while True:
        try:
            now=datetime.now(ITALY)
            sleep_sec=60 - now.second + 2
            time.sleep(max(1,sleep_sec))
            scan_tf("1m", cooldown_m1, "LAVORO 2 [M1->5m]")
        except Exception as e:
            print(f"Loop M1 err {e}"); time.sleep(10)

threading.Thread(target=loop_m5, daemon=True).start()
threading.Thread(target=loop_m1, daemon=True).start()

from flask import Flask
app=Flask(__name__)
@app.route('/')
def home(): return f"Doppio Bot M1+M5 70% Scad {SCADENZA}m - {ora_it()}"
@app.route('/ping')
def ping(): return "ok"

if __name__=="__main__":
    send(f"🚀 <b>BOT DOPPIO AVVIATO</b>\nLavoro 1: 5m -> {SCADENZA}m 70%\nLavoro 2: 1m -> {SCADENZA}m 70%\nOra {ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
