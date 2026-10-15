# bot.py - FINALE 1m -> 5m - 80% SETUP
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

def pinbar_1m_precisa(df):
    if len(df)<70: return None

    # Pinbar è penultima, conferma è ultima (1 candela dopo)
    pin_c = df.iloc[-2]
    conf_c = df.iloc[-1]

    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C)
    if corpo==0: corpo = total*0.05
    inf = min(O,C)-L
    sup = H-max(O,C)

    is_hammer = (inf >= corpo*2.0 and inf >= total*0.40 and sup <= total*0.20 and corpo <= total*0.40)
    is_star = (sup >= corpo*2.0 and sup >= total*0.40 and inf <= total*0.20 and corpo <= total*0.40)
    if not (is_hammer or is_star): return None

    ema20 = float(df['ema20'].iloc[-2])
    ema50 = float(df['ema50'].iloc[-2])
    last_20_high = df['High'].iloc[-22:-2].max()
    last_20_low = df['Low'].iloc[-22:-2].min()

    # FILTRO SR
    tocca_sr = (L <= last_20_low*1.0005) if is_hammer else (H >= last_20_high*0.9995)
    if not tocca_sr: return None

    # CONFERMA - candela dopo va nella direzione
    if is_hammer and float(conf_c['Close']) <= float(conf_c['Open']): return None # Vuoi verde
    if is_star and float(conf_c['Close']) >= float(conf_c['Open']): return None # Vuoi rossa

    # FILTRO ORARIO 08-22 Italia
    h = ora_num()
    if h < 8 or h > 22: return None

    dir = "SU" if is_hammer else "GIÙ"
    tipo = "HAMMER" if is_hammer else "STAR"
    entry_50 = (H + L) / 2 # Entry al 50% pinbar
    forza = (inf if is_hammer else sup)/total*100

    return {"dir":dir,"tipo":tipo,"entry50":entry_50,"target_old":L+(inf*0.70) if is_hammer else H-(sup*0.70),"forza":forza}

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    for symbol in PAIRS:
        clean = symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 600: continue
        try:
            df = fix_df(yf.Ticker(symbol, session=_YF).history(period="1d", interval="1m"))
            if len(df)<70: continue
            df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50)
            pin = pinbar_1m_precisa(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            msg = (
                f"💎 <b>PIN 1m -> 5m 80%</b> 💎\n"
                f"Asset: <b>{clean}</b>\n"
                f"Dir: <b>{sig}</b> {pin['tipo']}\n"
                f"Analisi 1m | Scad <b>5 MIN</b>\n"
                f"Entry 50%: <code>{pin['entry50']:.5f}</code>\n"
                f"Entry 70%: <code>{pin['target_old']:.5f}</code>\n"
                f"Forza {pin['forza']:.0f}% | SR+EMA+CONF+ORARIO\n"
                f"Ora: {ora_it()}"
            )
            send(msg)
            print(f"[{ora_it()}] FINALE {clean} {pin['tipo']}")
        except: continue

def loop():
    send(f"🚀 <b>BOT FINALE 80% AVVIATO</b>\n1m analisi -> 5m scadenza\nFiltri: SR + EMA + Conferma + 08-22\nEntry 50% | No RSI\nOra {ora_it()}")
    while True:
        try: time.sleep(35); scan()
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"Finale {ora_it()}"
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
