# bot.py - COME VEDI TU A MANO - TROVA TUTTE LE PINBAR
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
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURCAD=X","GBPCAD=X","GBPAUD=X"]
_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def pinbar_MANUALE(df):
    # COME GUARDI TU A MANO NELLA FOTO
    if len(df)<3: return None
    c = df.iloc[-1]
    O,H,L,C = float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total = H-L
    if total <= 0: return None
    corpo = abs(O-C)
    if corpo == 0: corpo = total * 0.05
    inf = min(O,C) - L
    sup = H - max(O,C)

    # REGOLA MANUALE - COME OCCHIO UMANO
    # Basta che uno stoppino sia chiaramente più lungo dell'altro

    # HAMMER / PIN RIALZO - come vedi tu, stoppino sotto lungo
    if inf > sup * 1.8 and inf > total * 0.35 and corpo < total * 0.50:
        return {"dir":"SU","target":L+(inf*0.70),"forza":inf/total*100,"tipo":"HAMMER","inf":inf,"sup":sup,"corpo":corpo,"total":total}

    # SHOOTING STAR / PIN RIBASSO - come in foto EUR/GBP tuo, stoppino sopra lungo
    if sup > inf * 1.8 and sup > total * 0.35 and corpo < total * 0.50:
        return {"dir":"GIÙ","target":H-(sup*0.70),"forza":sup/total*100,"tipo":"STAR","inf":inf,"sup":sup,"corpo":corpo,"total":total}

    return None

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan_manuale():
    for symbol in PAIRS:
        clean = symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 300: continue # 5 min solo
        try:
            df1 = fix_df(yf.Ticker(symbol, session=_YF).history(period="1d", interval="1m"))
            if len(df1) < 20: continue
            df5 = df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
            if len(df5) < 5: continue

            pin = pinbar_MANUALE(df5)
            if not pin: continue

            cooldown[clean] = time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"

            # Calcolo come vedi tu
            msg = (
                f"👁️ <b>PINBAR MANUALE</b> 👁️\n"
                f"Asset: <b>{clean}</b>\n"
                f"Dir: <b>{sig}</b> {pin['tipo']}\n"
                f"Scad: <b>5 MIN</b>\n"
                f"Entry 70%: <code>{pin['target']:.5f}</code>\n"
                f"Stoppino: {pin['forza']:.0f}% | Corpo: {(pin['corpo']/pin['total']*100):.0f}%\n"
                f"Ora: {ora_it()}"
            )
            send(msg)
            print(f"[{ora_it()}] MANUALE {clean} {pin['tipo']} forza {pin['forza']:.0f}%")
        except Exception as e:
            print(e)
            continue

def loop():
    send(f"🚀 <b>BOT MANUALE AVVIATO</b>\nTrova TUTTE come vedi tu a mano\nSenza filtri RSI - solo occhio\nOra {ora_it()}")
    while True:
        try:
            time.sleep(45) # Ogni 45 sec
            scan_manuale()
        except:
            time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app = Flask(__name__)
@app.route('/')
def home(): return f"Manuale {ora_it()} trovate {len(cooldown)}"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
