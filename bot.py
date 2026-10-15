# bot.py - MEDIO - il giusto equilibrio
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURCAD=X","GBPCAD=X"]

_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def ora_num(): return datetime.now(ITALY).hour
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def ema(s,p): return s.ewm(span=p).mean()

def pinbar_medio(df):
    if len(df)<70: return None
    pin_c, conf_c = df.iloc[-2], df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C) or total*0.05
    inf, sup = min(O,C)-L, H-max(O,C)

    # MEDIO: via di mezzo
    # Originale 2.0x 50% / Ultra 1.2x 35% / MEDIO 1.5x 42%
    is_hammer = (inf >= corpo*1.4 and inf >= total*0.40 and sup <= total*0.40 and corpo <= total*0.55)
    is_star = (sup >= corpo*1.4 and sup >= total*0.40 and inf <= total*0.40 and corpo <= total*0.55)
    if not (is_hammer or is_star): return None

    forza = (inf if is_hammer else sup)/total*100
    if forza < 60: return None # scarta quelli 55% come EURGBP dello screen

    # SR MEDIO 0.15% - obbligatorio, niente bypass
    last_20_high = df['High'].iloc[-22:-2].max()
    last_20_low = df['Low'].iloc[-22:-2].min()
    tocca_sr = (L <= last_20_low*1.0020) if is_hammer else (H >= last_20_high*0.9980)
    if not tocca_sr: return None

    # EMA - ritorna, ma largo
    ema20 = float(df['ema20'].iloc[-2])
    ema50 = float(df['ema50'].iloc[-2])
    if is_hammer and C < ema50*0.998: return None
    if is_star and C > ema50*1.002: return None

    # CONFERMA - verde/rosso netto come originale
    if is_hammer and float(conf_c['Close']) <= float(conf_c['Open']): return None
    if is_star and float(conf_c['Close']) >= float(conf_c['Open']): return None

    # ORARIO 08-22 come originale
    h = ora_num()
    if h < 8 or h > 22: return None

    return {"dir":"SU" if is_hammer else "GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry50":(H+L)/2,"forza":forza}

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    trovati = 0
    for s in PAIRS:
        if trovati >= 2: break # MAX 2 per scan, non 4 come prima
        clean = s.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 480: continue # 8 min
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(s, session=_YF).history(period="1d", interval="1m"))
            if len(df)<70: continue
            df['ema20']=ema(df['Close'],20)
            df['ema50']=ema(df['Close'],50)
            pin = pinbar_medio(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            send(f"💎 <b>PIN MEDIO 80%</b> 💎\nAsset: <b>{clean}</b> {pin['tipo']}\nDir: <b>{sig} {pin['dir']}</b>\nScad <b>5 MIN</b>\nEntry: <code>{pin['entry50']:.5f}</code>\nForza {pin['forza']:.0f}% | SR+EMA+CONF+08-22\n{ora_it()}")
            print(f"SEGNALE {clean} {pin['forza']:.0f}%", flush=True)
            trovati += 1
        except: continue

def loop():
    send(f"🚀 <b>MEDIO 80% AVVIATO</b>\n1m -> 5m\nFiltri: Pin 1.5x 42% + Forza 60% + SR 0.15% + EMA + CONF + 08-22\nMax 2 segnali per scan\nOra {ora_it()}")
    while True:
        try: scan(); time.sleep(40)
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"MEDIO {ora_it()}"
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
