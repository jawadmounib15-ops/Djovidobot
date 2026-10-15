# bot.py - ULTRA LARGO - trova per forza
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURCAD=X","GBPCAD=X","GBPUSD=X","USDCHF=X","NZDUSD=X"]

_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def ema(s,p): return s.ewm(span=p).mean()

def pinbar_ultra(df):
    if len(df)<50: return None
    pin_c = df.iloc[-2]
    conf_c = df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C)
    if corpo==0: corpo = total*0.05
    inf = min(O,C)-L
    sup = H-max(O,C)

    # ULTRA LARGO: 1.2x invece di 1.5x, 35% invece di 40%, corpo 65%
    is_hammer = (inf >= corpo*1.2 and inf >= total*0.35 and sup <= total*0.50 and corpo <= total*0.65)
    is_star = (sup >= corpo*1.2 and sup >= total*0.35 and inf <= total*0.50 and corpo <= total*0.65)
    if not (is_hammer or is_star): return None

    # SR ULTRA LARGO 0.25% - prima 0.15%
    last_20_high = df['High'].iloc[-22:-2].max()
    last_20_low = df['Low'].iloc[-22:-2].min()

    tocca_sr = False
    if is_hammer:
        tocca_sr = L <= last_20_low*1.0025 # 0.25%
        # se non tocca SR, accetta se forza >70%
        if not tocca_sr and inf/total >= 0.60:
            tocca_sr = True
    else:
        tocca_sr = H >= last_20_high*0.9975
        if not tocca_sr and sup/total >= 0.60:
            tocca_sr = True

    if not tocca_sr: return None

    # CONFERMA ULTRA LARGA - basta che non sia opposta forte
    # Prima voleva verde/rosso netto, ora basta non sia rosso forte
    if is_hammer:
        if float(conf_c['Close']) < float(conf_c['Open'])*0.9995: # tollera piccola rossa
            return None
    else:
        if float(conf_c['Close']) > float(conf_c['Open'])*1.0005:
            return None

    # NO FILTRO ORARIO - togliamo 07-23, prende H24 per testare
    # NO FILTRO EMA - togliamo per trovare più

    dir = "SU" if is_hammer else "GIÙ"
    tipo = "HAMMER" if is_hammer else "STAR"
    entry_50 = (H + L) / 2
    forza = (inf if is_hammer else sup)/total*100
    return {"dir":dir,"tipo":tipo,"entry50":entry_50,"forza":forza}

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    for symbol in PAIRS:
        clean = symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 180: continue # 3min
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(symbol, session=_YF).history(period="1d", interval="1m"))
            if len(df)<50:
                print(f"{clean} len {len(df)}", flush=True)
                continue
            df['ema20']=ema(df['Close'],20)
            pin = pinbar_ultra(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            msg = ( f"💎 <b>PIN ULTRA LARGO</b> 💎\n"
                    f"Asset: <b>{clean}</b> {pin['tipo']}\n"
                    f"Dir: <b>{sig} {pin['dir']}</b>\n"
                    f"Scad <b>5 MIN</b>\n"
                    f"Entry: <code>{pin['entry50']:.5f}</code>\n"
                    f"Forza {pin['forza']:.0f}% | TEST LARGO\n"
                    f"{ora_it()}" )
            send(msg)
            print(f"SEGNALE {clean} {pin['tipo']} {sig} {pin['forza']:.0f}%", flush=True)
        except Exception as e:
            print(f"ERR {clean} {e}", flush=True)

def loop():
    send(f"🚀 <b>ULTRA LARGO AVVIATO</b>\n1m -> 5m\nFiltri MINIMI - trova tutto\nOra {ora_it()}")
    print(f"ULTRA LARGO AVVIATO {ora_it()}", flush=True)
    while True:
        try: scan(); time.sleep(30)
        except Exception as e: print(f"LOOP {e}", flush=True); time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"ULTRA LARGO {ora_it()}"
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
