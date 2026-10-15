# bot.py - MEDIO-LARGO ANTI-FALSI - 1m -> 5m
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","CADCHF=X","CHFJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","GBPCAD=X"]

_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def ora_num(): return datetime.now(ITALY).hour
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def ema(s,p): return s.ewm(span=p).mean()

def pinbar_anti_falsi(df):
    if len(df)<80: return None
    pin_c, conf_c = df.iloc[-2], df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C) or total*0.05
    inf, sup = min(O,C)-L, H-max(O,C)
    forza = (inf if inf>sup else sup)/total*100

    # PINBAR: leggermente stretto per anti-falsi
    is_hammer = (inf >= corpo*1.6 and inf >= total*0.45 and sup <= total*0.45 and corpo <= total*0.50)
    is_star = (sup >= corpo*1.6 and sup >= total*0.45 and inf <= total*0.45 and corpo <= total*0.50)
    if not (is_hammer or is_star): return None
    if forza < 62: return None # prima 55% -> ora 62%

    # SR VERO: 30 candele invece di 20
    last_30_high = df['High'].iloc[-32:-2].max()
    last_30_low = df['Low'].iloc[-32:-2].min()
    tocca_sr = (L <= last_30_low*1.0015) if is_hammer else (H >= last_30_high*0.9985)
    if not tocca_sr: return None

    # FILTRO TREND ANTI-FALSI: hammer solo se era in discesa
    ema20 = float(df['ema20'].iloc[-2])
    ema50 = float(df['ema50'].iloc[-2])
    ema20_prev = float(df['ema20'].iloc[-6]) # 5 candele fa

    if is_hammer:
        # deve essere in downtrend: ema20 sotto ema50 o ema20 in discesa
        if ema20 > ema50*1.001 and ema20 >= ema20_prev: return None
    else:
        if ema20 < ema50*0.999 and ema20 <= ema20_prev: return None

    # CONFERMA FORTE: non basta verde, deve chiudere sopra 50% pinbar
    entry_50 = (H+L)/2
    if is_hammer:
        if float(conf_c['Close']) <= entry_50: return None # deve superare metà
    else:
        if float(conf_c['Close']) >= entry_50: return None

    # ORARIO
    if ora_num() < 8 or ora_num() > 22: return None

    return {"dir":"SU" if is_hammer else "GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry50":entry_50,"forza":forza}

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    trovati=0
    for s in PAIRS:
        if trovati>=2: break
        clean=s.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 480: continue # 8 min
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(s, session=_YF).history(period="1d", interval="1m"))
            if len(df)<80: continue
            df['ema20']=ema(df['Close'],20)
            df['ema50']=ema(df['Close'],50)
            pin = pinbar_anti_falsi(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            send(f"💎 <b>PIN 80% ANTI-FALSI</b> 💎\nAsset: <b>{clean}</b> {pin['tipo']}\nDir: <b>{sig} {pin['dir']}</b>\nScad <b>5 MIN</b>\nEntry: <code>{pin['entry50']:.5f}</code>\nForza {pin['forza']:.0f}% | SR30+Trend+Conf50%\n{ora_it()}")
            print(f"SEGNALE BUONO {clean} {pin['forza']:.0f}%", flush=True)
            trovati+=1
        except Exception as e: print(f"ERR {e}", flush=True)

def loop():
    send(f"🚀 <b>MEDIO-LARGO ANTI-FALSI AVVIATO</b>\n1m -> 5m\nPin 1.5x 42% Forza 62% SR 30cnd + Filtro Trend + Conf 50%\nOra {ora_it()}")
    while True:
        try: scan(); time.sleep(40)
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"ANTI-FALSI {ora_it()}"
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
