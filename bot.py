# bot.py SERIO - SOLO REALI - PINBAR VISIBILE - 5m -> 5m - 70%
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

SCADENZA = 5
RITRACCIAMENTO = 0.70
TIMEFRAME = "5m"

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

# SOLO 10 COPPIE REALI PRINCIPALI - LE PIU' PULITE
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]

_YF = cffi_requests.Session(impersonate="chrome", timeout=15)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=10)
    except Exception as e: print(e)

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def rsi(s, p=7):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l
    return 100-(100/(1+rs))

def pinbar_seria_visibile(df):
    if len(df) < 30: return None
    c = df.iloc[-2]
    O,H,L,C = float(c['Open']), float(c['High']), float(c['Low']), float(c['Close'])
    total = H - L
    if total <= 0: return None

    # FILTRO SERIO 1: candela deve essere grande
    avg = (df['High'].iloc[-20:-2] - df['Low'].iloc[-20:-2]).mean()
    if total < avg * 1.1: # solo candele più grandi della media
        return None

    corpo = abs(O-C)
    inf = min(O,C) - L
    sup = H - max(O,C)

    # FILTRO SERIO 2: corpo piccolissimo - pinbar che si VEDE
    if corpo > total * 0.20: # max 20% corpo
        return None

    # BULLISH SERIA
    if inf >= total * 0.70 and sup <= total * 0.10:
        target = L + (inf * RITRACCIAMENTO)
        return {"dir":"SU","target":target,"forza":inf/total*100,"total":total,"O":O,"H":H,"L":L,"C":C}

    # BEARISH SERIA
    if sup >= total * 0.70 and inf <= total * 0.10:
        target = H - (sup * RITRACCIAMENTO)
        return {"dir":"GIÙ","target":target,"forza":sup/total*100,"total":total,"O":O,"H":H,"L":L,"C":C}

    return None

def get_price(symbol):
    try:
        df = fix_df(yf.Ticker(symbol, session=_YF).history(period="1d", interval="1m"))
        return float(df.iloc[-1]['Close']) if len(df) else None
    except: return None

def scan():
    now = datetime.now(ITALY)
    # SOLO MERCATO REALE - no OTC
    if now.hour < 8 or now.hour >= 22:
        print(f"[{ora_it()}] Mercato reale chiuso - dormo")
        return
    if now.weekday() >= 5: # sabato domenica
        print(f"[{ora_it()}] Weekend - no reali")
        return

    for symbol in PAIRS:
        clean = symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 1200: # 20 min cooldown serio
            continue
        try:
            df = fix_df(yf.Ticker(symbol, session=_YF).history(period="5d", interval=TIMEFRAME))
            if len(df) < 30: continue
            df['rsi7'] = rsi(df['Close'], 7)
            last_rsi = float(df['rsi7'].iloc[-2])
            pin = pinbar_seria_visibile(df)
            if not pin: continue

            # RSI SERIO come da tue foto
            if pin["dir"] == "SU" and last_rsi > 30: continue
            if pin["dir"] == "GIÙ" and last_rsi < 70: continue

            target = pin["target"]
            print(f"[{ora_it()}] {clean} PIN SERIA {pin['forza']:.0f}% RSI {last_rsi:.0f} -> attendo 70% {target:.5f}")

            # Attendi tocco 70% - 60 sec
            toccato = False
            for _ in range(30):
                time.sleep(2)
                live = get_price(symbol)
                if not live: continue
                if pin["dir"] == "SU" and live <= target * 1.0004:
                    toccato = True; break
                if pin["dir"] == "GIÙ" and live >= target * 0.9996:
                    toccato = True; break

            if not toccato:
                print(f"[{ora_it()}] {clean} non tocca 70% - skip")
                continue

            cooldown[clean] = time.time()
            signal = "CALL" if pin["dir"] == "SU" else "PUT"
            msg = (
                f"✅ <b>PINBAR SERIA REALE</b> ✅\n"
                f"Asset: <b>{clean}</b> (REALE)\n"
                f"Direzione: <b>{'SU CALL' if signal=='CALL' else 'GIÙ PUT'}</b>\n"
                f"Scadenza: <b>{SCADENZA} MIN</b> | Analisi 5m\n"
                f"Entry 70%: <code>{target:.5f}</code>\n"
                f"Pin: {pin['forza']:.0f}% | RSI7: {last_rsi:.0f}\n"
                f"Candela: O {pin['O']:.5f} H {pin['H']:.5f} L {pin['L']:.5f} C {pin['C']:.5f}\n"
                f"Ora IT: {ora_it()}\n"
                f"Verifica su TradingView M5 - la vedi!"
            )
            send(msg)

        except Exception as e:
            print(f"Err {clean}: {e}")
            continue

def loop():
    send(f"🚀 <b>BOT SERIO REALI AVVIATO</b>\nSolo 10 coppie reali | 08-22 IT | Pinbar >70% visibile\nTF 5m -> Scad 5m 70%\nOra: {ora_it()}")
    while True:
        try:
            now = datetime.now(ITALY)
            sleep_sec = (5 - (now.minute % 5)) * 60 - now.second + 3
            if sleep_sec < 10: sleep_sec += 300
            time.sleep(sleep_sec)
            scan()
        except Exception as e:
            print(f"Loop err: {e}")
            time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return f"Bot Serio Reali 5m {ora_it()}"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
