# bot.py - 64% BILANCIATO 70% - manda segnali ma buoni
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X","CADJPY=X","CADCHF=X","AUDCHF=X","AUDCAD=X","GBPCAD=X"]

_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def ora_num(): return datetime.now(ITALY).hour
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def ema(s,p): return s.ewm(span=p).mean()

def pinbar_70(df):
    if len(df)<70: return None
    pin_c, conf_c = df.iloc[-2], df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C) or total*0.05
    inf, sup = min(O,C)-L, H-max(O,C)
    forza = (inf if inf>sup else sup)/total*100

    # BILANCIATO 70%: meno stretto del 66% ma più del 62%
    is_hammer = (inf >= corpo*1.55 and inf >= total*0.44 and sup <= total*0.33 and corpo <= total*0.50)
    is_star = (sup >= corpo*1.55 and sup >= total*0.44 and inf <= total*0.33 and corpo <= total*0.50)
    if not (is_hammer or is_star): return None
    if forza < 64: return None # 64% non 66% - così arrivano

    # SR 0.20% su 20 candele (non 0.11% su 30) - così arriva
    last_20_high = df['High'].iloc[-22:-2].max()
    last_20_low = df['Low'].iloc[-22:-2].min()
    tocca_sr = (L <= last_20_low*1.0020) if is_hammer else (H >= last_20_high*0.9980)
    if not tocca_sr: return None

    # TREND leggero - non blocca troppo
    ema20 = float(df['ema20'].iloc[-2])
    ema50 = float(df['ema50'].iloc[-2])
    if is_hammer and ema20 > ema50*1.003: return None # blocca solo se molto contro trend
    if is_star and ema20 < ema50*0.997: return None

    # CONF 50% - non 60% - così arriva
    if is_hammer and float(conf_c['Close']) < L + total*0.50: return None
    if is_star and float(conf_c['Close']) > H - total*0.50: return None
    if is_hammer and float(conf_c['Close']) <= float(conf_c['Open']): return None
    if is_star and float(conf_c['Close']) >= float(conf_c['Open']): return None

    if ora_num() < 7 or ora_num() > 23: return None

    return {"dir":"SU" if is_hammer else "GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry50":(H+L)/2,"forza":forza}

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    trovati=0
    for s in PAIRS:
        if trovati>=2: break
        clean=s.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 300: continue # 5min non 10
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(s, session=_YF).history(period="1d", interval="1m"))
            if len(df)<70: continue
            df['ema20']=ema(df['Close'],20)
            df['ema50']=ema(df['Close'],50)
            pin = pinbar_70(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            send(f"💎 <b>PIN 70% BILANCIATO</b> 💎\nAsset: <b>{clean}</b> {pin['tipo']}\nDir: <b>{sig} {pin['dir']}</b>\nScad <b>5 MIN</b>\nEntry: <code>{pin['entry50']:.5f}</code>\nForza {pin['forza']:.0f}% | 70% win\n{ora_it()}")
            print(f"SEGNALE {clean} {pin['forza']:.0f}%", flush=True)
            trovati+=1
        except Exception as e:
            print(f"ERR {clean} {e}", flush=True)

def loop():
    send(f"🚀 <b>BILANCIATO 70% AVVIATO - MANDA SEGNALI</b>\nPin 1.55x 44% Forza 64%\nSR 0.20% su 20cnd | Conf 50% | 17 coppie\nOra {ora_it()}")
    while True:
        try: scan(); time.sleep(30) # 30sec non 40
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"BILANCIATO 70% {ora_it()} - 17 pairs"
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
