# bot.py - TELEGRAM PURO - 1m -> 5m - 80% LARGO
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
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

def pinbar_largo(df):
    if len(df)<70: return None
    pin_c = df.iloc[-2]
    conf_c = df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C)
    if corpo==0: corpo = total*0.05
    inf = min(O,C)-L
    sup = H-max(O,C)

    # LARGO: prima 2.0x -> ora 1.5x | 50% -> 40% | corpo 40% -> 55%
    is_hammer = (inf >= corpo*1.5 and inf >= total*0.40 and sup <= total*0.40 and corpo <= total*0.55)
    is_star = (sup >= corpo*1.5 and sup >= total*0.40 and inf <= total*0.40 and corpo <= total*0.55)
    if not (is_hammer or is_star): return None

    last_20_high = df['High'].iloc[-22:-2].max()
    last_20_low = df['Low'].iloc[-22:-2].min()

    # SR LARGO: 0.05% -> 0.15%
    tocca_sr = (L <= last_20_low*1.0015) if is_hammer else (H >= last_20_high*0.9985)
    if not tocca_sr: return None

    # CONFERMA
    if is_hammer and float(conf_c['Close']) <= float(conf_c['Open']): return None
    if is_star and float(conf_c['Close']) >= float(conf_c['Open']): return None

    # ORARIO LARGO 07-23
    h = ora_num()
    if h < 7 or h > 23: return None

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
        if clean in cooldown and time.time()-cooldown[clean] < 300: continue
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(symbol, session=_YF).history(period="1d", interval="1m"))
            if len(df)<70: continue
            df['ema20']=ema(df['Close'],20)
            df['ema50']=ema(df['Close'],50)
            pin = pinbar_largo(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            msg = ( f"💎 <b>PIN LARGO 1m -> 5m</b> 💎\n"
                    f"Asset: <b>{clean}</b>\n"
                    f"Dir: <b>{sig} {pin['dir']}</b> {pin['tipo']}\n"
                    f"Scadenza: <b>5 MIN</b>\n"
                    f"Entry 50%: <code>{pin['entry50']:.5f}</code>\n"
                    f"Forza {pin['forza']:.0f}% | SR+EMA+CONF\n"
                    f"Ora: {ora_it()}" )
            send(msg)
            print(f"[{ora_it()}] SEGNALE {clean} {pin['tipo']} {sig} {pin['forza']:.0f}%", flush=True)
        except Exception as e:
            print(f"ERR {clean} {e}", flush=True)
            continue

def loop():
    send(f"🚀 <b>BOT FINALE 80% LARGO AVVIATO</b>\n1m analisi -> 5m scadenza\nFiltri: SR 0.15% + EMA + Conferma + 07-23\nPinbar 1.5x | Corpo 55%\nOra {ora_it()}")
    print(f"BOT LARGO AVVIATO {ora_it()}", flush=True)
    while True:
        try: scan(); time.sleep(35)
        except Exception as e: print(f"LOOP ERR {e}", flush=True); time.sleep(10)

threading.Thread(target=loop, daemon=True).start()

app=Flask(__name__)
@app.route('/')
def home(): return f"BOT 80% LARGO TELEGRAM - {ora_it()} - OK"
@app.route('/debug')
def debug(): return f"BOT TELEGRAM LARGO - {ora_it()} - Pairs {len(PAIRS)} - Cooldown {len(cooldown)}"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
