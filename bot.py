import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","AUDCHF=X","AUDCAD=X","CADCHF=X"]

app = Flask(__name__)
pending = []
cooldown = {}
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

@app.route('/')
def home():
    return f"BOT 2MIN 2.8x LIVE - Pending:{len(pending)} - {len(PAIRS)} PAIRS"

def send(msg):
    if not TOKEN or not CHAT_ID:
        return
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except:
        pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def scan_2min():
    global pending
    pending = [p for p in pending if time.time() - p['time'] < 400]
    count = 0
    for symbol in PAIRS:
        if count >= 2:
            break
        clean = symbol.replace("=X","")
        if clean in cooldown and time.time() - cooldown[clean] < 360:
            continue
        if any(p['symbol'] == clean for p in pending):
            continue
        try:
            df = yf.Ticker(symbol, session=_YF_SESSION).history(period="2d", interval="2m")
            df = fix_df(df)
            if len(df) < 200:
                continue
            df['e20'] = df['Close'].ewm(span=20).mean()
            df['e50'] = df['Close'].ewm(span=50).mean()
            df['e200'] = df['Close'].ewm(span=200).mean()
            df['rsi'] = rsi(df['Close'])
            last = df.iloc[-1]
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            price=c; rsi_v=float(last['rsi'])
            e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200'])
            is_green=c>o; is_red=not is_green
            body=abs(c-o); total_range=h-l
            upper=h-max(o,c); lower=min(o,c)-l
            if total_range < 0.000005:
                total_range = body * 2.5 if body>0 else 0.00005
            if body == 0:
                continue
            signal=None
            # STRETTA PELO - 2.8x / 30% / 0.45x
            pin_bull = lower > body*2.8 and body < total_range*0.30 and upper < body*0.45 and is_green
            pin_bear = upper > body*2.8 and body < total_range*0.30 and lower < body*0.45 and is_red
            if pin_bull and price>e200 and e20>e50 and 30<=rsi_v<=60:
                signal="BUY"
            if pin_bear and price<e200 and e20<e50 and 40<=rsi_v<=70:
                signal="SELL"
            if signal:
                send(f"🎯 2.8x {signal} {clean} ⏰6MIN RSI{int(rsi_v)} {price:.5f}")
                pending.append({"symbol":clean,"signal":signal,"time":time.time()})
                cooldown[clean]=time.time()
                count+=1
        except Exception as e:
            print(f"ERR {clean}: {e}")
            continue

def loop():
    time.sleep(5)
    if TOKEN and CHAT_ID:
        send(f"🚀 BOT 2MIN 2.8x AVVIATO - {len(PAIRS)} coppie")
    while True:
        try:
            scan_2min()
        except Exception as e:
            print(f"LOOP ERR {e}")
        time.sleep(45)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
