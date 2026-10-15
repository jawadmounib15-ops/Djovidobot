# bot.py - STRETTO +2 PELO - 66% + coppie richieste
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

# COPPIE COME RICHIESTO DA TE
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

def pinbar_stretto(df):
    if len(df)<80: return None
    pin_c, conf_c = df.iloc[-2], df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C) or total*0.05
    inf, sup = min(O,C)-L, H-max(O,C)
    forza = (inf if inf>sup else sup)/total*100

    # +2 PELO: prima 1.55x 44% sup 33% corpo 50% forza 64%
    # ora: 1.65x 46% sup 31% corpo 46% forza 66%
    is_hammer = (inf >= corpo*1.65 and inf >= total*0.46 and sup <= total*0.31 and corpo <= total*0.46)
    is_star = (sup >= corpo*1.65 and sup >= total*0.46 and inf <= total*0.31 and corpo <= total*0.46)
    if not (is_hammer or is_star): return None
    if forza < 66: return None

    # SR 0.13% -> 0.11%
    last_30_high = df['High'].iloc[-32:-2].max()
    last_30_low = df['Low'].iloc[-32:-2].min()
    tocca_sr = (L <= last_30_low*1.0011) if is_hammer else (H >= last_30_high*0.9989)
    if not tocca_sr: return None

    ema20 = float(df['ema20'].iloc[-2])
    ema50 = float(df['ema50'].iloc[-2])
    ema20_prev = float(df['ema20'].iloc[-6])
    if is_hammer:
        if ema20 > ema50*1.001 and ema20 >= ema20_prev: return None
    else:
        if ema20 < ema50*0.999 and ema20 <= ema20_prev: return None

    # CONF 55% -> 60%
    if is_hammer and float(conf_c['Close']) < L + total*0.60: return None
    if is_star and float(conf_c['Close']) > H - total*0.60: return None
    if is_hammer and float(conf_c['Close']) <= float(conf_c['Open']): return None
    if is_star and float(conf_c['Close']) >= float(conf_c['Open']): return None

    if ora_num() < 8 or ora_num() > 22: return None

    return {"dir":"SU" if is_hammer else "GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry50":(H+L)/2,"forza":forza}

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    trovati=0
    for s in PAIRS:
        if trovati>=2: break
        clean=s.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 600: continue
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(s, session=_YF).history(period="1d", interval="1m"))
            if len(df)<80: continue
            df['ema20']=ema(df['Close'],20)
            df['ema50']=ema(df['Close'],50)
            pin = pinbar_stretto(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            send(f"💎 <b>PIN +2 PELO 66%</b> 💎\nAsset: <b>{clean}</b> {pin['tipo']}\nDir: <b>{sig}</b> Forza {pin['forza']:.0f}%\nEntry: <code>{pin['entry50']:.5f}</code>\nSR 0.11% + Trend + Conf 60%\n{ora_it()}")
            print(f"SEGNALE {clean} {pin['forza']:.0f}%", flush=True)
            trovati+=1
        except: continue

def loop():
    send(f"🚀 <b>STRETTO +2 PELO 66% AVVIATO</b>\nPin 1.65x 46% Forza 66%\nSR 0.11% Conf 60%\nCoppie: {len(PAIRS)}\nOra {ora_it()}")
    while True:
        try: scan(); time.sleep(40)
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"+2 PELO 66% {ora_it()} - {len(PAIRS)} pairs"
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
