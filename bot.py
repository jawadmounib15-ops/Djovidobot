# bot.py - MEDIO-LARGO con DEBUG
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
debug_log = []
LOG_FILE = "/tmp/medio.log"

def log(m):
    print(m, flush=True)
    debug_log.append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(debug_log)>100: debug_log.pop(0)

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def ora_num(): return datetime.now(ITALY).hour
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def ema(s,p): return s.ewm(span=p).mean()

def pinbar_medio_largo(df, clean):
    if len(df)<70:
        return None, f"{clean} len {len(df)}"
    pin_c, conf_c = df.iloc[-2], df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None, "total 0"
    corpo = abs(O-C) or total*0.05
    inf, sup = min(O,C)-L, H-max(O,C)
    forza = (inf if min(O,C)-L > H-max(O,C) else sup)/total*100

    # MEDIO-LARGO: 1.4x 40% sup 40% corpo 55% forza 55%
    is_hammer = (inf >= corpo*1.4 and inf >= total*0.40 and sup <= total*0.40 and corpo <= total*0.55)
    is_star = (sup >= corpo*1.4 and sup >= total*0.40 and inf <= total*0.40 and corpo <= total*0.55)
    if not (is_hammer or is_star):
        return None, f"{clean} no pinbar forza {forza:.0f}%"

    if forza < 55:
        return None, f"{clean} forza bassa {forza:.0f}%"

    last_20_high = df['High'].iloc[-22:-2].max()
    last_20_low = df['Low'].iloc[-22:-2].min()

    # SR 0.20% - medio
    tocca_sr = (L <= last_20_low*1.0020) if is_hammer else (H >= last_20_high*0.9980)
    if not tocca_sr:
        return None, f"{clean} no SR L {L:.5f} vs {last_20_low:.5f}"

    # EMA largo 0.3%
    ema50 = float(df['ema50'].iloc[-2])
    if is_hammer and C < ema50*0.997: return None, f"{clean} sotto EMA50"
    if is_star and C > ema50*1.003: return None, f"{clean} sopra EMA50"

    # CONFERMA tollera doji 0.05%
    if is_hammer and float(conf_c['Close']) < float(conf_c['Open'])*0.9995: return None, f"{clean} conferma rossa"
    if is_star and float(conf_c['Close']) > float(conf_c['Open'])*1.0005: return None, f"{clean} conferma verde"

    # ORARIO
    h = ora_num()
    if h < 7 or h > 23: return None, f"{clean} fuori orario {h}"

    return {"dir":"SU" if is_hammer else "GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry50":(H+L)/2,"forza":forza}, "OK"

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=10)
    except Exception as e: log(f"send err {e}")

def scan():
    log(">>> INIZIO SCAN")
    trovati=0
    for s in PAIRS:
        clean=s.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 300: continue
        if trovati>=3: break
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(s, session=_YF).history(period="1d", interval="1m"))
            if len(df)<70:
                log(f"{clean} corto {len(df)}")
                continue
            df['ema20']=ema(df['Close'],20)
            df['ema50']=ema(df['Close'],50)
            pin, motivo = pinbar_medio_largo(df, clean)
            if not pin:
                # logga solo se quasi pinbar
                if "pinbar" not in motivo and "len" not in motivo:
                    log(motivo)
                continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            send(f"💎 <b>PIN MEDIO-LARGO</b> 💎\nAsset: <b>{clean}</b> {pin['tipo']}\nDir: <b>{sig} {pin['dir']}</b>\nScad <b>5 MIN</b>\nEntry: <code>{pin['entry50']:.5f}</code>\nForza {pin['forza']:.0f}% | SR+EMA+CONF\n{ora_it()}")
            log(f"*** SEGNALE {clean} {sig} {pin['forza']:.0f}% ***")
            trovati+=1
        except Exception as e:
            log(f"ERR {clean} {e}")
    log(f">>> FINE SCAN trovati {trovati}")

def loop():
    send(f"🚀 <b>MEDIO-LARGO AVVIATO con DEBUG</b>\n1m -> 5m\nPin 1.4x 40% Forza 55% SR 0.20% EMA CONF 07-23\nOra {ora_it()}\nVai su /debug per vedere perché scarta")
    log("AVVIATO MEDIO-LARGO")
    while True:
        try: scan(); time.sleep(35)
        except Exception as e: log(f"LOOP {e}"); time.sleep(10)

threading.Thread(target=loop, daemon=True).start()

app=Flask(__name__)
@app.route('/')
def home(): return f"MEDIO-LARGO {ora_it()} - /debug per log"

@app.route('/debug')
def debug():
    html = f"<b>MEDIO-LARGO LOG {ora_it()}</b><br>Cooldown: {list(cooldown.keys())}<br><br>"
    for l in debug_log[::-1]:
        html+=f"{l}<br>"
    html+=f"<br><a href='/debug'>reload</a>"
    return html

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
